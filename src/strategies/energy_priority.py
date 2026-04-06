"""Energy-priority strategy."""

from typing import Any, Dict, List

from .base import BaseStrategy


class EnergyPriorityStrategy(BaseStrategy):
    """Prefer assignments with lower estimated incremental energy."""

    def __init__(self, energy_model=None):
        super().__init__("energy_priority")
        self.energy_model = energy_model

    def assign_tasks(self, environment) -> Dict[str, Any]:
        idle_uavs = self.get_idle_uavs(environment)
        pending_tasks = self.get_pending_tasks(environment)

        assignments = []

        for task in pending_tasks:
            if not idle_uavs:
                break

            uav_energy_costs = []
            for uav in idle_uavs:
                distance = (
                    (uav.position[0] - task.start_point[0]) ** 2
                    + (uav.position[1] - task.start_point[1]) ** 2
                ) ** 0.5
                distance += (
                    (task.start_point[0] - task.end_point[0]) ** 2
                    + (task.start_point[1] - task.end_point[1]) ** 2
                ) ** 0.5

                battery_factor = 1.0 + max(0.0, (100.0 - uav.battery) / 100.0 * 0.3)
                payload = float(getattr(task, "payload", 1.0))
                payload_factor = 1.0 + payload * 0.1

                estimated_energy = distance * battery_factor * payload_factor
                uav_energy_costs.append((uav, estimated_energy))

            uav_energy_costs.sort(key=lambda item: item[1])
            best_uav, min_energy = uav_energy_costs[0]

            best_uav.assign_task(task)
            task.status = "in_progress"
            task.assigned_uav = best_uav
            idle_uavs.remove(best_uav)

            assignments.append(
                {
                    "uav_id": best_uav.id,
                    "task_id": task.id,
                    "estimated_energy": min_energy,
                }
            )

        return {
            "strategy": self.name,
            "assignments": assignments,
            "assigned_count": len(assignments),
            "total_estimated_energy": sum(item["estimated_energy"] for item in assignments),
        }

    def select_charging_station(self, uav, environment):
        available_agvs = self.get_available_agvs(environment)
        if not available_agvs:
            return None

        scored = []
        for agv in available_agvs:
            distance = (
                (agv.position[0] - uav.position[0]) ** 2
                + (agv.position[1] - uav.position[1]) ** 2
            ) ** 0.5
            distance_score = 1.0 / (1.0 + distance / 100.0)
            charging_power = float(getattr(agv, "charging_power", 200.0))
            power_score = charging_power / 200.0
            total_score = distance_score * 0.6 + power_score * 0.4
            scored.append((agv, total_score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[0][0]

    def optimize_batch(self, uavs: List[object], tasks: List[object]) -> Dict[str, Any]:
        return {
            "strategy": self.name,
            "method": "batch_optimization",
            "note": "Greedy placeholder; can be replaced by global optimization.",
        }
