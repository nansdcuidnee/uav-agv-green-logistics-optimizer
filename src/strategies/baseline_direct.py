"""Baseline direct strategy."""

from typing import Any, Dict

from .base import BaseStrategy


class BaselineDirectStrategy(BaseStrategy):
    """Assign tasks in FIFO order to idle UAVs."""

    def __init__(self):
        super().__init__("baseline_direct")

    def assign_tasks(self, environment) -> Dict[str, Any]:
        idle_uavs = self.get_idle_uavs(environment)
        pending_tasks = self.get_pending_tasks(environment)

        assignments = []
        for i, task in enumerate(pending_tasks):
            if i >= len(idle_uavs):
                break
            uav = idle_uavs[i]
            uav.assign_task(task)
            task.status = "in_progress"
            task.assigned_uav = uav
            assignments.append({"uav_id": uav.id, "task_id": task.id})

        return {
            "strategy": self.name,
            "assignments": assignments,
            "assigned_count": len(assignments),
        }

    def select_charging_station(self, uav, environment) -> object:
        available_agvs = self.get_available_agvs(environment)
        return available_agvs[0] if available_agvs else None
