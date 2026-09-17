"""Adapter for Unitree's installed ``TeleVuerWrapper`` data object."""

from typing import Any, List, Optional

from .input_schema import TeleopInput


def _list_or_none(value: Any) -> Optional[List[float]]:
    if value is None:
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    return list(value)


def _unitree_trigger_to_closed_ratio(value: float) -> float:
    """Convert TeleVuer's 10=open, 0=pressed convention to 0=open, 1=closed."""

    return max(0.0, min(1.0, 1.0 - float(value) / 10.0))


def from_televuer(tele_data: Any) -> TeleopInput:
    """Create a normalized sample from the official XR teleop sample."""

    left_axis = tele_data.left_ctrl_thumbstickValue
    right_axis = tele_data.right_ctrl_thumbstickValue
    left_wrist = getattr(tele_data, "left_wrist_pose", None)
    right_wrist = getattr(tele_data, "right_wrist_pose", None)
    head_pose = getattr(tele_data, "head_pose", None)
    left_pose = _list_or_none(left_wrist)
    right_pose = _list_or_none(right_wrist)
    return TeleopInput(
        motion_ready=bool(tele_data.motion_data_ready),
        left_x=float(left_axis[0]),
        left_y=float(left_axis[1]),
        right_x=float(right_axis[0]),
        right_y=float(right_axis[1]),
        left_trigger=_unitree_trigger_to_closed_ratio(tele_data.left_ctrl_triggerValue),
        right_trigger=_unitree_trigger_to_closed_ratio(tele_data.right_ctrl_triggerValue),
        left_grip=float(getattr(tele_data, "left_ctrl_squeezeValue", 0.0)),
        right_grip=float(getattr(tele_data, "right_ctrl_squeezeValue", 0.0)),
        buttons={
            "A": bool(getattr(tele_data, "right_ctrl_aButton", False)),
            "B": bool(getattr(tele_data, "right_ctrl_bButton", False)),
            "X": bool(getattr(tele_data, "left_ctrl_aButton", False)),
            "Y": bool(getattr(tele_data, "left_ctrl_bButton", False)),
            "left_stick": bool(getattr(tele_data, "left_ctrl_thumbstick", False)),
            "right_stick": bool(getattr(tele_data, "right_ctrl_thumbstick", False)),
            "left_trigger": bool(getattr(tele_data, "left_ctrl_trigger", False)),
            "right_trigger": bool(getattr(tele_data, "right_ctrl_trigger", False)),
        },
        left_pose=left_pose,
        right_pose=right_pose,
        headset_pose=_list_or_none(head_pose),
        arm={
            "left_wrist_pose": left_pose,
            "right_wrist_pose": right_pose,
        },
    )
