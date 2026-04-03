"""Strategy base class for pluggable scheduling policies."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseStrategy(ABC):
    """Base class for all task-assignment and charging-selection strategies."""

    def __init__(self, strategy_name: str):
        self.name = strategy_name

    @abstractmethod
    def assign_tasks(self, environment) -> Dict[str, Any]:
        """Assign pending tasks to idle UAVs."""

    @abstractmethod
    def select_charging_station(self, uav, environment) -> Optional[object]:
        """Select an AGV to charge current UAV."""

    def get_idle_uavs(self, environment) -> List[object]:
        return [uav for uav in environment.uavs if uav.is_idle()]

    def get_pending_tasks(self, environment) -> List[object]:
        return [task for task in environment.tasks if task.status == "pending"]

    def get_available_agvs(self, environment) -> List[object]:
        return [agv for agv in environment.agvs if getattr(agv, "status", None) == "idle"]
