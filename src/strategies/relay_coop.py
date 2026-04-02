"""Relay cooperative strategy."""

from typing import Any, Dict

from .base import BaseStrategy


class RelayCoopStrategy(BaseStrategy):
    """Assign nearest AGV-assisted tasks and prefer paired AGV for charging."""

    def __init__(self, relay_distance: float = 200.0):
        super().__init__("relay_coop")
        self.relay_distance = relay_distance

    def assign_tasks(self, environment) -> Dict[str, Any]:
        idle_uavs = self.get_idle_uavs(environment)
        pending_tasks = self.get_pending_tasks(environment)

        assignments = []
        for task in pending_tasks:
            if not idle_uavs:
                break

            nearest_agv = min(
                environment.agvs,
                key=lambda agv: (
                    (agv.position[0] - task.start_point[0]) ** 2
                    + (agv.position[1] - task.start_point[1]) ** 2
                )
                ** 0.5,
            )

            direction = self._calculate_direction(nearest_agv.position, task.start_point)
            relay_point = (
                nearest_agv.position[0] + direction[0] * self.relay_distance,
                nearest_agv.position[1] + direction[1] * self.relay_distance,
            )

            uav = idle_uavs.pop(0)
            uav.assign_task(task)
            task.status = "in_progress"
            task.assigned_uav = uav
            task.relay_point = relay_point
            task.assigned_agv = nearest_agv

            assignments.append(
                {
                    "uav_id": uav.id,
                    "task_id": task.id,
                    "relay_point": relay_point,
                    "agv_id": nearest_agv.id,
                }
            )

        return {
            "strategy": self.name,
            "assignments": assignments,
            "assigned_count": len(assignments),
        }

    def select_charging_station(self, uav, environment) -> object:
        current_task = uav.task
        if current_task and getattr(current_task, "assigned_agv", None):
            if current_task.assigned_agv.status == "idle":
                return current_task.assigned_agv

        available_agvs = self.get_available_agvs(environment)
        if not available_agvs:
            return None

        return min(
            available_agvs,
            key=lambda agv: (
                (agv.position[0] - uav.position[0]) ** 2
                + (agv.position[1] - uav.position[1]) ** 2
            )
            ** 0.5,
        )

    def _calculate_direction(self, from_pos, to_pos) -> tuple:
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        distance = (dx**2 + dy**2) ** 0.5
        if distance == 0:
            return (0.0, 0.0)
        return (dx / distance, dy / distance)
