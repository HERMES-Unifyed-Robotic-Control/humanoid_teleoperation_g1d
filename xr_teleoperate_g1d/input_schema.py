"""Normalized input types shared by XR, replay and test sources."""

from dataclasses import asdict, dataclass, field
from time import time_ns
from typing import Any, Dict, List, Mapping, Optional


@dataclass
class TeleopInput:
    """One controller sample.

    Axes are normalized to ``[-1, 1]``. Trigger and grip values are normalized
    to ``[0, 1]`` where one means fully pressed. Controller poses use
    ``[x, y, z, qx, qy, qz, qw]``.
    """

    timestamp_ns: int = field(default_factory=time_ns)
    motion_ready: bool = True
    left_x: float = 0.0
    left_y: float = 0.0
    right_x: float = 0.0
    right_y: float = 0.0
    left_trigger: float = 0.0
    right_trigger: float = 0.0
    left_grip: float = 0.0
    right_grip: float = 0.0
    left_pose: Optional[List[float]] = None
    right_pose: Optional[List[float]] = None
    headset_pose: Optional[List[float]] = None
    buttons: Dict[str, bool] = field(default_factory=dict)
    arm: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TeleopInput":
        """Build an input sample from a JSON-compatible mapping."""

        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
