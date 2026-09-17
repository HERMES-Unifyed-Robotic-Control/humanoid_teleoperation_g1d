"""Controller mapping for G1-D base, lift, arms and Dex1 grippers."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .input_schema import TeleopInput


@dataclass(frozen=True)
class ControlLimits:
    deadzone: float = 0.08
    max_vx: float = 0.20
    max_vyaw: float = 0.60
    max_lift: float = 1.0
    max_waist_pitch_rate: float = 0.30
    grip_activation: float = 0.90


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def smooth_deadzone(value: float, deadzone: float) -> float:
    """Apply a deadzone followed by a quintic smooth-step response."""

    value = clamp(value, -1.0, 1.0)
    if abs(value) <= deadzone:
        return 0.0
    t = (abs(value) - deadzone) / (1.0 - deadzone)
    smooth = 6.0 * t**5 - 15.0 * t**4 + 10.0 * t**3
    return smooth if value > 0.0 else -smooth


def map_input(
    sample: TeleopInput,
    *,
    limits: ControlLimits = ControlLimits(),
    yaw_axis: str = "left_x",
    lift_axis: str = "right_y",
    waist_pitch_axis: Optional[str] = "right_x",
    invert_vx: bool = True,
    invert_yaw: bool = True,
    invert_lift: bool = True,
    invert_waist_pitch: bool = True,
) -> Dict[str, Any]:
    """Convert one normalized XR sample into a complete collection frame.

    G1-D is a differential AGV. The current SDK explicitly ignores ``vy``, so
    the four axes follow the G1-D handheld controller: left Y drives forward,
    left X turns, right Y moves the lift and right X pitches the waist.
    """

    vx_axis = -sample.left_y if invert_vx else sample.left_y
    yaw_value = getattr(sample, yaw_axis)
    lift_value = getattr(sample, lift_axis)
    waist_pitch_value = getattr(sample, waist_pitch_axis) if waist_pitch_axis else 0.0
    yaw_axis_value = -yaw_value if invert_yaw else yaw_value
    lift_axis_value = -lift_value if invert_lift else lift_value
    waist_pitch_axis_value = -waist_pitch_value if invert_waist_pitch else waist_pitch_value

    ready = bool(sample.motion_ready)
    vx = limits.max_vx * smooth_deadzone(vx_axis, limits.deadzone) if ready else 0.0
    vyaw = limits.max_vyaw * smooth_deadzone(yaw_axis_value, limits.deadzone) if ready else 0.0
    lift = limits.max_lift * smooth_deadzone(lift_axis_value, limits.deadzone) if ready else 0.0
    waist_pitch = (
        limits.max_waist_pitch_rate * smooth_deadzone(waist_pitch_axis_value, limits.deadzone)
        if ready
        else 0.0
    )

    left_closed = clamp(sample.left_trigger, 0.0, 1.0)
    right_closed = clamp(sample.right_trigger, 0.0, 1.0)

    return {
        "timestamp_ns": int(sample.timestamp_ns),
        "xr": sample.to_dict(),
        "actions": {
            "chassis": {"vx": vx, "vy": 0.0, "vyaw": vyaw},
            "lift": {"vz": lift},
            "waist": {"pitch_velocity": waist_pitch},
            "dex1": {
                "enabled": ready,
                "left_closed_ratio": left_closed,
                "right_closed_ratio": right_closed,
            },
            "arm": {
                "motion_ready": ready,
                "left_active": ready and sample.left_grip >= limits.grip_activation,
                "right_active": ready and sample.right_grip >= limits.grip_activation,
                "target": sample.arm,
            },
        },
        "states": {},
        "safety": {"motion_ready": ready, "stop_commanded": not ready},
    }


def legacy_unitree_mapping(sample: TeleopInput, *, limits: ControlLimits = ControlLimits()) -> Dict[str, Any]:
    """Backward-compatible name for the official G1-D mapping."""

    return map_input(sample, limits=limits)


def xrobotoolkit_mapping(sample: TeleopInput, *, limits: ControlLimits = ControlLimits()) -> Dict[str, Any]:
    """Compatibility layout from the generic XRoboToolkit mobile sample."""

    return map_input(
        sample,
        limits=limits,
        yaw_axis="right_x",
        waist_pitch_axis=None,
        invert_vx=False,
        invert_yaw=False,
        invert_lift=False,
        invert_waist_pitch=False,
    )
