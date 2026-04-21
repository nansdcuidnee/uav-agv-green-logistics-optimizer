"""Energy-priority strategy."""

from typing import Any, Dict, List, Tuple

from .base import BaseStrategy


class EnergyPriorityStrategy(BaseStrategy):
    """Prefer assignments with lower estimated incremental energy.

    核心思路：
    1. 计算每个任务的直接飞行距离
    2. 如果任务距离 > 阈值（300m），考虑使用中继
    3. 综合评估后选择最优分配方案
    """

    # 距离阈值：超过此距离使用中继更省能
    RELAY_THRESHOLD = 300.0

    def __init__(self, energy_model=None, relay_threshold: float = 300.0):
        super().__init__("energy_priority")
        self.energy_model = energy_model
        self.RELAY_THRESHOLD = relay_threshold

    def _calculate_distance(self, pos1, pos2) -> float:
        """计算两点之间的距离"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def _calculate_task_centroid(self, tasks) -> Tuple[float, float]:
        """计算任务点的几何中心"""
        if not tasks:
            return (500.0, 500.0)

        all_points = []
        for task in tasks:
            all_points.append(task.start_point)
            all_points.append(task.end_point)

        avg_x = sum(p[0] for p in all_points) / len(all_points)
        avg_y = sum(p[1] for p in all_points) / len(all_points)
        return (avg_x, avg_y)

    def assign_tasks(self, environment) -> Dict[str, Any]:
        idle_uavs = self.get_idle_uavs(environment)
        pending_tasks = self.get_pending_tasks(environment)

        if not pending_tasks or not idle_uavs:
            return {
                "strategy": self.name,
                "assignments": [],
                "assigned_count": 0,
                "total_estimated_energy": 0,
            }

        assignments = []

        # 计算中继中心（用于长距离任务）
        relay_center = self._calculate_task_centroid(pending_tasks)
        print(f"[ENERGY_PRIORITY] Relay center: {relay_center}, threshold: {self.RELAY_THRESHOLD}m")

        # 移动AGV到中继位置
        if environment.agvs:
            for agv in environment.agvs:
                agv.move_to(relay_center)

        for task in pending_tasks:
            if not idle_uavs:
                break

            # 计算直接飞行距离
            direct_distance = self._calculate_distance(task.start_point, task.end_point)

            # 评估不同方案的能耗
            uav_energy_costs = []

            for uav in idle_uavs:
                # 方案1：直接从UAV当前位置飞往任务点
                uav_to_start = self._calculate_distance(uav.position, task.start_point)
                total_direct = uav_to_start + direct_distance

                # 方案2：使用中继（从中继中心出发）
                relay_to_start = self._calculate_distance(relay_center, task.start_point)
                total_relay = relay_to_start + direct_distance

                # 选择能耗更低的方案
                if total_relay < total_direct and direct_distance > self.RELAY_THRESHOLD:
                    # 使用中继
                    estimated_energy = total_relay
                    use_relay = True
                else:
                    # 直接飞行
                    estimated_energy = total_direct
                    use_relay = False

                # 电池因子
                battery_factor = 1.0 + max(0.0, (100.0 - uav.battery) / 100.0 * 0.3)
                payload = float(getattr(task, "payload", 1.0))
                payload_factor = 1.0 + payload * 0.1

                final_energy = estimated_energy * battery_factor * payload_factor
                uav_energy_costs.append({
                    'uav': uav,
                    'energy': final_energy,
                    'direct_distance': total_direct,
                    'relay_distance': total_relay,
                    'use_relay': use_relay
                })

            # 按能耗排序，选择最优
            uav_energy_costs.sort(key=lambda x: x['energy'])
            best_option = uav_energy_costs[0]
            best_uav = best_option['uav']

            # 更新任务和UAV
            if best_option['use_relay']:
                # UAV从中继点出发
                best_uav.position = relay_center
                task.use_relay = True
                task.relay_point = relay_center
                print(f"[ENERGY_PRIORITY] Task {task.id}: Use relay (dist: {best_option['relay_distance']:.1f}m < {best_option['direct_distance']:.1f}m)")
            else:
                task.use_relay = False
                task.relay_point = None
                print(f"[ENERGY_PRIORITY] Task {task.id}: Direct flight (dist: {best_option['direct_distance']:.1f}m)")

            best_uav.assign_task(task)
            task.status = "in_progress"
            task.assigned_uav = best_uav
            task.assigned_agv = environment.agvs[0] if environment.agvs else None
            idle_uavs.remove(best_uav)

            assignments.append(
                {
                    "uav_id": best_uav.id,
                    "task_id": task.id,
                    "estimated_energy": best_option['energy'],
                    "direct_distance": best_option['direct_distance'],
                    "relay_distance": best_option['relay_distance'],
                    "use_relay": best_option['use_relay'],
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
