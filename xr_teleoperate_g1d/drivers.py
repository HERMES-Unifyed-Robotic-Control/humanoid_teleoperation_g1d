"""G1-D motion backends.

Imports for Unitree's Python SDK are deliberately lazy so mapping, replay and
tests still work on a development machine without DDS installed.
"""

import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, TextIO


@dataclass(frozen=True)
class MotionCommand:
    vx: float
    vyaw: float
    lift_vz: float

    @classmethod
    def from_frame(cls, frame: Dict[str, Any]) -> "MotionCommand":
        actions = frame["actions"]
        return cls(
            vx=float(actions["chassis"]["vx"]),
            vyaw=float(actions["chassis"]["vyaw"]),
            lift_vz=float(actions["lift"]["vz"]),
        )


class DryRunDriver:
    def __init__(self, stream: TextIO = sys.stdout):
        self.stream = stream

    def send(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        command = MotionCommand.from_frame(frame)
        print(
            "vx={:+.3f} m/s vyaw={:+.3f} rad/s lift={:+.3f} "
            "dex1=({:.2f},{:.2f})".format(
                command.vx,
                command.vyaw,
                command.lift_vz,
                frame["actions"]["dex1"]["left_closed_ratio"],
                frame["actions"]["dex1"]["right_closed_ratio"],
            ),
            file=self.stream,
        )
        return {}

    def close(self) -> None:
        return None


class Sdk2BridgeDriver:
    """Stream motion commands to the C++ ``AgvClient`` bridge over stdin."""

    def __init__(self, bridge_binary: str, network_interface: str, watchdog_ms: int = 300):
        self._sequence = 0
        self._process = subprocess.Popen(
            [bridge_binary, network_interface, str(watchdog_ms)],
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def send(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        if self._process.poll() is not None:
            raise RuntimeError("g1d_agv_bridge exited with code %s" % self._process.returncode)
        if self._process.stdin is None:
            raise RuntimeError("g1d_agv_bridge stdin is unavailable")
        command = MotionCommand.from_frame(frame)
        self._process.stdin.write(
            "{} {:.9f} {:.9f} {:.9f}\n".format(
                self._sequence, command.vx, command.vyaw, command.lift_vz
            )
        )
        self._process.stdin.flush()
        self._sequence += 1
        return {}

    def close(self) -> None:
        if self._process.poll() is None:
            if self._process.stdin is not None:
                self._process.stdin.close()
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.terminate()
                self._process.wait(timeout=2.0)


class DirectDdsMotionDriver:
    """DDS backend matching the currently installed XR teleop topics."""

    def __init__(self, network_interface: Optional[str] = None, enable_dex1: bool = True):
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelPublisher
        from unitree_sdk2py.idl.geometry_msgs.msg.dds_ import Point32_, Twist_
        from unitree_sdk2py.idl.default import (
            geometry_msgs_msg_dds__Point32_,
            geometry_msgs_msg_dds__Twist_,
        )

        ChannelFactoryInitialize(0, networkInterface=network_interface)

        self._height = geometry_msgs_msg_dds__Point32_()
        self._move = geometry_msgs_msg_dds__Twist_()
        self._height_publisher = ChannelPublisher("rt/cmd_hispeed", Point32_)
        self._move_publisher = ChannelPublisher("rt/cmd_vel_no_limit", Twist_)
        self._height_publisher.Init()
        self._move_publisher.Init()
        self._dex1 = Dex1DdsDriver() if enable_dex1 else None

    def send(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        command = MotionCommand.from_frame(frame)
        self._move.linear.x = command.vx
        self._move.linear.y = 0.0
        self._move.angular.z = command.vyaw
        self._height.z = command.lift_vz
        self._move_publisher.Write(self._move)
        self._height_publisher.Write(self._height)
        states = {}
        if self._dex1 is not None:
            states.update(self._dex1.send(frame))
        return states

    def close(self) -> None:
        self._move.linear.x = 0.0
        self._move.angular.z = 0.0
        self._height.z = 0.0
        self._move_publisher.Write(self._move)
        self._height_publisher.Write(self._height)


class Dex1DdsDriver:
    """State-aware Dex1 controller based on Unitree's installed implementation."""

    def __init__(self, state_timeout: float = 5.0):
        from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber
        from unitree_sdk2py.idl.default import unitree_go_msg_dds__MotorCmd_
        from unitree_sdk2py.idl.unitree_go.msg.dds_ import MotorCmds_, MotorStates_

        self._motor_cmd_type = unitree_go_msg_dds__MotorCmd_
        self._motor_cmds_type = MotorCmds_
        self._left_publisher = ChannelPublisher("rt/dex1/left/cmd", MotorCmds_)
        self._right_publisher = ChannelPublisher("rt/dex1/right/cmd", MotorCmds_)
        self._left_subscriber = ChannelSubscriber("rt/dex1/left/state", MotorStates_)
        self._right_subscriber = ChannelSubscriber("rt/dex1/right/state", MotorStates_)
        self._left_publisher.Init()
        self._right_publisher.Init()
        self._left_subscriber.Init()
        self._right_subscriber.Init()
        self._left_q: Optional[float] = None
        self._right_q: Optional[float] = None
        self._left_command = self._make_command()
        self._right_command = self._make_command()

        deadline = time.monotonic() + state_timeout
        while time.monotonic() < deadline and (self._left_q is None or self._right_q is None):
            self._read_state()
            time.sleep(0.01)
        if self._left_q is None or self._right_q is None:
            raise RuntimeError(
                "Dex1 state timeout; check dex1_gripper.service and rt/dex1/*/state"
            )

    def _make_command(self) -> Any:
        message = self._motor_cmds_type()
        command = self._motor_cmd_type()
        command.dq = 0.0
        command.tau = 0.0
        command.kp = 5.0
        command.kd = 0.05
        message.cmds = [command]
        return message

    def _read_state(self) -> None:
        left = self._left_subscriber.Read()
        right = self._right_subscriber.Read()
        if left is not None and left.states:
            self._left_q = float(left.states[0].q)
        if right is not None and right.states:
            self._right_q = float(right.states[0].q)

    @staticmethod
    def _limited_target(target: float, current: float) -> float:
        delta = 0.18
        return max(current - delta, min(current + delta, target))

    def send(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        self._read_state()
        if self._left_q is None or self._right_q is None:
            return {}

        action = frame["actions"]["dex1"]
        if action["enabled"]:
            left_target = 5.4 * (1.0 - float(action["left_closed_ratio"]))
            right_target = 5.4 * (1.0 - float(action["right_closed_ratio"]))
            left_action = self._limited_target(left_target, self._left_q)
            right_action = self._limited_target(right_target, self._right_q)
        else:
            left_action = self._left_q
            right_action = self._right_q

        self._left_command.cmds[0].q = left_action
        self._right_command.cmds[0].q = right_action
        self._left_publisher.Write(self._left_command)
        self._right_publisher.Write(self._right_command)
        return {
            "dex1": {
                "left_q": self._left_q,
                "right_q": self._right_q,
                "left_action_q": left_action,
                "right_action_q": right_action,
            }
        }

    def close(self) -> None:
        return None


class CompositeDriver:
    def __init__(self, motion: Any, dex1: Optional[Any] = None):
        self.motion = motion
        self.dex1 = dex1

    def send(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        states = dict(self.motion.send(frame) or {})
        if self.dex1 is not None:
            states.update(self.dex1.send(frame) or {})
        return states

    def close(self) -> None:
        try:
            if self.dex1 is not None:
                self.dex1.close()
        finally:
            self.motion.close()
