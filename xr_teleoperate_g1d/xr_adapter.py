"""Adapter for the XRoboToolkit PC Service Python SDK."""

from typing import Any

from .input_schema import TeleopInput


class XRoboToolkitSource:
    """Read normalized controller data without taking ownership of arm IK."""

    def __init__(self):
        import xrobotoolkit_sdk as xrt

        self._xrt = xrt
        xrt.init()

    def read(self) -> TeleopInput:
        xrt: Any = self._xrt
        left_axis = xrt.get_left_axis()
        right_axis = xrt.get_right_axis()
        return TeleopInput(
            timestamp_ns=int(xrt.get_time_stamp_ns()),
            motion_ready=True,
            left_x=float(left_axis[0]),
            left_y=float(left_axis[1]),
            right_x=float(right_axis[0]),
            right_y=float(right_axis[1]),
            left_trigger=float(xrt.get_left_trigger()),
            right_trigger=float(xrt.get_right_trigger()),
            left_grip=float(xrt.get_left_grip()),
            right_grip=float(xrt.get_right_grip()),
            left_pose=list(xrt.get_left_controller_pose()),
            right_pose=list(xrt.get_right_controller_pose()),
            headset_pose=list(xrt.get_headset_pose()),
            buttons={
                "A": bool(xrt.get_A_button()),
                "B": bool(xrt.get_B_button()),
                "X": bool(xrt.get_X_button()),
                "Y": bool(xrt.get_Y_button()),
                "left_axis_click": bool(xrt.get_left_axis_click()),
                "right_axis_click": bool(xrt.get_right_axis_click()),
            },
        )

    def close(self) -> None:
        self._xrt.close()
