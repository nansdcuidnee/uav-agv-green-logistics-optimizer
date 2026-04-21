"""Baseline direct strategy."""

from typing import Any, Dict

from .base import BaseStrategy


class BaselineDirectStrategy(BaseStrategy):
    """Assign tasks in simple FIFO order to idle UAVs."""

    def __init__(self):
        super().__init__("baseline_direct")

    def _calculate_distance(self, pos1, pos2) -> float:
        """计算两点之间的距离"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def assign_tasks(self, environment) -> Dict[str, Any]:
        idle_uavs = self.get_idle_uavs(environment)
        pending_tasks = self.get_pending_tasks(environment)

        if not pending_tasks or not idle_uavs:
            return {
                "strategy": self.name,
                "assignments": [],
                "assigned_count": 0,
            }

        print(f"[BASELINE_DIRECT] {len(idle_uavs)} idle UAVs, {len(pending_tasks)} pending tasks")

        assignments = []
        for i, task in enumerate(pending_tasks):
            if i >= len(idle_uavs):
                break
            uav = idle_uavs[i]

            # 计算直接飞行距离（不做任何优化）
            direct_distance = self._calculate_distance(task.start_point, task.end_point)
            uav_to_task = self._calculate_distance(uav.position, task.start_point)
            total_distance = uav_to_task + direct_distance

            print(f"[BASELINE_DIRECT] Task {task.id}: UAV{uav.id} from {uav.position} to {task.start_point}, dist={total_distance:.1f}m")

            uav.assign_task(task)
            task.status = "in_progress"
            task.assigned_uav = uav
            task.use_relay = False  # 明确不使用中继
            task.relay_point = None

            assignments.append({
                "uav_id": uav.id,
                "task_id": task.id,
                "distance": total_distance,
                "use_relay": False
            })

        return {
            "strategy": self.name,
            "assignments": assignments,
            "assigned_count": len(assignments),
        }

    def select_charging_station(self, uav, environment):
        available_agvs = self.get_available_agvs(environment)
        return available_agvs[0] if available_agvs else None
