"""ALNS solution data structures for route-level optimization."""

import copy
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
    uav_route_position: int = -1
    agv_route_position: int = -1
    uav_anchor_position: Tuple[float, float] = (0.0, 0.0)
    agv_anchor_position: Tuple[float, float] = (0.0, 0.0)


@dataclass
class RouteStop:
    task_id: int
    mode: DeliveryMode
    uav_id: int
    agv_id: Optional[int] = None
    relay_point: Optional[Tuple[float, float]] = None
    cost: float = 0.0
    position: Tuple[float, float] = (0.0, 0.0)


@dataclass
class Solution:
    assignments: List[DeliveryOption]
    total_cost: float = 0.0
    mode_counts: Dict[str, int] = field(default_factory=dict)
    uav_routes: Dict[int, List[RouteStop]] = field(default_factory=dict)
    agv_routes: Dict[int, List[RouteStop]] = field(default_factory=dict)
    task_index: Dict[int, DeliveryOption] = field(default_factory=dict)

    def __post_init__(self):
        if self.mode_counts is None:
            self.mode_counts = {}
        if self.uav_routes is None:
            self.uav_routes = {}
        if self.agv_routes is None:
            self.agv_routes = {}
        if self.task_index is None:
            self.task_index = {}

    def rebuild_indexes(self):
        """Rebuild uav_routes, agv_routes, task_index from assignments."""
        self.uav_routes = {}
        self.agv_routes = {}
        self.task_index = {}
        self.total_cost = 0.0
        self.mode_counts = {"direct": 0, "relay_fixed": 0}

        for option in self.assignments:
            self._add_option_to_indexes(option)

    def _add_option_to_indexes(self, option: DeliveryOption):
        """Add a single option to indexes."""
        self.total_cost += option.cost
        mode_str = option.mode.value
        self.mode_counts[mode_str] = self.mode_counts.get(mode_str, 0) + 1
        self.task_index[option.task_id] = option

        uav_stop = RouteStop(
            task_id=option.task_id,
            mode=option.mode,
            uav_id=option.uav_id,
            agv_id=option.agv_id,
            relay_point=option.relay_point,
            cost=option.cost,
            position=option.uav_anchor_position
        )
        if option.uav_id not in self.uav_routes:
            self.uav_routes[option.uav_id] = []

        if 0 <= option.uav_route_position < len(self.uav_routes[option.uav_id]):
            self.uav_routes[option.uav_id].insert(option.uav_route_position, uav_stop)
        else:
            self.uav_routes[option.uav_id].append(uav_stop)

        if option.mode == DeliveryMode.RELAY_FIXED and option.agv_id is not None:
            agv_stop = RouteStop(
                task_id=option.task_id,
                mode=option.mode,
                uav_id=option.uav_id,
                agv_id=option.agv_id,
                relay_point=option.relay_point,
                cost=0.0,
                position=option.agv_anchor_position
            )
            if option.agv_id not in self.agv_routes:
                self.agv_routes[option.agv_id] = []

            if 0 <= option.agv_route_position < len(self.agv_routes[option.agv_id]):
                self.agv_routes[option.agv_id].insert(option.agv_route_position, agv_stop)
            else:
                self.agv_routes[option.agv_id].append(agv_stop)

    def add_assignment(self, option: DeliveryOption):
        """Add an assignment and sync all indexes."""
        self.assignments.append(option)
        self._add_option_to_indexes(option)

    def remove_assignment(self, option: DeliveryOption = None, task_id: int = None) -> Optional[DeliveryOption]:
        """Remove an assignment by option or task_id. Returns removed option."""
        if task_id is not None and option is None:
            option = self.task_index.get(task_id)

        if option is None:
            return None

        if option not in self.assignments:
            return None

        self.assignments.remove(option)

        if option.task_id in self.task_index:
            del self.task_index[option.task_id]

        self.total_cost -= option.cost
        mode_str = option.mode.value
        self.mode_counts[mode_str] = max(0, self.mode_counts.get(mode_str, 0) - 1)

        if option.uav_id in self.uav_routes:
            for i, stop in enumerate(self.uav_routes[option.uav_id]):
                if stop.task_id == option.task_id:
                    self.uav_routes[option.uav_id].pop(i)
                    break
            if not self.uav_routes[option.uav_id]:
                del self.uav_routes[option.uav_id]

        if option.mode == DeliveryMode.RELAY_FIXED and option.agv_id is not None:
            if option.agv_id in self.agv_routes:
                for i, stop in enumerate(self.agv_routes[option.agv_id]):
                    if stop.task_id == option.task_id:
                        self.agv_routes[option.agv_id].pop(i)
                        break
                if not self.agv_routes[option.agv_id]:
                    del self.agv_routes[option.agv_id]

        return option

    def get_uav_route_length(self, uav_id: int) -> int:
        """Get the length of a UAV route."""
        return len(self.uav_routes.get(uav_id, []))

    def get_agv_route_length(self, agv_id: int) -> int:
        """Get the length of an AGV route."""
        return len(self.agv_routes.get(agv_id, []))

    def get_insertion_positions(self, uav_id: int) -> List[int]:
        """Get all possible insertion positions for a UAV route."""
        length = self.get_uav_route_length(uav_id)
        return list(range(length + 1))

    def get_agv_insertion_positions(self, agv_id: int) -> List[int]:
        """Get all possible insertion positions for an AGV route."""
        length = self.get_agv_route_length(agv_id)
        return list(range(length + 1))

    def copy(self):
        """Deep copy the solution."""
        new_solution = Solution(
            assignments=copy.deepcopy(self.assignments),
            total_cost=self.total_cost,
            mode_counts=copy.deepcopy(self.mode_counts),
            uav_routes=copy.deepcopy(self.uav_routes),
            agv_routes=copy.deepcopy(self.agv_routes),
            task_index=copy.deepcopy(self.task_index)
        )
        return new_solution


class DestroyOperator(Enum):
    RANDOM_REMOVE = "random_remove"
    WORST_REMOVE = "worst_remove"
    HIGH_ENERGY_REMOVE = "high_energy_remove"


class RepairOperator(Enum):
    GREEDY_INSERT = "greedy_insert"
    REGRET_INSERT = "regret_insert"
    RELAY_AWARE_REGRET_INSERT = "relay_aware_regret_insert"
