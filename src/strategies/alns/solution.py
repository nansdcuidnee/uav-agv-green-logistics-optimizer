"""ALNS solution data structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DeliveryMode(Enum):
    DIRECT = "direct"
    RELAY_FIXED = "relay_fixed"


@dataclass
class DeliveryOption:
    mode: DeliveryMode
    uav_id: int
    task_id: int
    relay_point: Optional[Tuple[float, float]] = None
    agv_id: Optional[int] = None
    cost: float = 0.0
    cost_breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class Solution:
    assignments: List[DeliveryOption]
    total_cost: float = 0.0
    mode_counts: Dict[str, int] = field(default_factory=dict)

    def copy(self):
        return Solution(
            assignments=self.assignments.copy(),
            total_cost=self.total_cost,
            mode_counts=self.mode_counts.copy()
        )


class DestroyOperator(Enum):
    RANDOM_REMOVE = "random_remove"
    WORST_REMOVE = "worst_remove"


class RepairOperator(Enum):
    GREEDY_INSERT = "greedy_insert"
    REGRET_INSERT = "regret_insert"
