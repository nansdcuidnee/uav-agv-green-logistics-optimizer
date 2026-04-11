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

        # 按优先级排序任务，优先级高的任务先分配
        pending_tasks.sort(key=lambda task: task.priority, reverse=True)

        assignments = []

        for task in pending_tasks:
            if not idle_uavs:
                break

            uav_scores = []
            for uav in idle_uavs:
                # 计算直飞能耗
                direct_distance = (
                    (uav.position[0] - task.start_point[0]) ** 2
                    + (uav.position[1] - task.start_point[1]) ** 2
                ) ** 0.5
                direct_distance += (
                    (task.start_point[0] - task.end_point[0]) ** 2
                    + (task.start_point[1] - task.end_point[1]) ** 2
                ) ** 0.5

                # 计算使用中继的能耗
                relay_benefit = 0.0
                relay_distance = direct_distance
                if environment.agvs:
                    nearest_agv = min(
                        environment.agvs,
                        key=lambda agv: (
                            (agv.position[0] - task.start_point[0]) ** 2
                            + (agv.position[1] - task.start_point[1]) ** 2
                        ) ** 0.5
                    )
                    # 计算从中继点出发的距离
                    relay_start_distance = (
                        (uav.position[0] - nearest_agv.position[0]) ** 2
                        + (uav.position[1] - nearest_agv.position[1]) ** 2
                    ) ** 0.5
                    relay_task_distance = (
                        (nearest_agv.position[0] - task.start_point[0]) ** 2
                        + (nearest_agv.position[1] - task.start_point[1]) ** 2
                    ) ** 0.5
                    relay_task_distance += (
                        (task.start_point[0] - task.end_point[0]) ** 2
                        + (task.start_point[1] - task.end_point[1]) ** 2
                    ) ** 0.5
                    relay_distance = relay_start_distance + relay_task_distance
                    # 计算中继收益
                    relay_benefit = max(0.0, direct_distance - relay_distance) / direct_distance

                # 计算电池因素
                battery_factor = 1.0 + max(0.0, (100.0 - uav.battery) / 100.0 * 0.5)
                
                # 计算负载因素
                payload = float(getattr(task, "payload", 1.0))
                payload_factor = 1.0 + payload * 0.2
                
                # 计算任务优先级因素
                priority_factor = 1.0 - (task.priority - 1) * 0.1
                priority_factor = max(0.5, priority_factor)
                
                # 计算总评分
                # 评分越低越好
                direct_score = direct_distance * battery_factor * payload_factor * priority_factor
                relay_score = relay_distance * battery_factor * payload_factor * priority_factor * (1 - relay_benefit * 0.3)
                
                # 选择更优的方式
                use_relay = relay_score < direct_score
                best_score = min(direct_score, relay_score)
                
                # 记录决策信息
                decision_info = {
                    "use_relay": use_relay,
                    "direct_score": direct_score,
                    "relay_score": relay_score,
                    "relay_benefit": relay_benefit,
                    "battery_level": uav.battery,
                    "distance": direct_distance
                }
                
                uav_scores.append((uav, best_score, decision_info))

            # 按评分排序，选择最优的UAV
            uav_scores.sort(key=lambda item: item[1])
            best_uav, best_score, decision_info = uav_scores[0]

            best_uav.assign_task(task)
            task.status = "in_progress"
            task.assigned_uav = best_uav
            task.decision_info = decision_info
            
            # 如果使用中继，设置中继点
            if decision_info["use_relay"] and environment.agvs:
                nearest_agv = min(
                    environment.agvs,
                    key=lambda agv: (
                        (agv.position[0] - task.start_point[0]) ** 2
                        + (agv.position[1] - task.start_point[1]) ** 2
                    ) ** 0.5
                )
                task.relay_point = nearest_agv.position
                task.assigned_agv = nearest_agv

            idle_uavs.remove(best_uav)

            assignments.append(
                {
                    "uav_id": best_uav.id,
                    "task_id": task.id,
                    "estimated_energy": best_score,
                    "use_relay": decision_info["use_relay"],
                    "relay_benefit": decision_info["relay_benefit"]
                }
            )

        return {
            "strategy": self.name,
            "assignments": assignments,
            "assigned_count": len(assignments),
            "total_estimated_energy": sum(item["estimated_energy"] for item in assignments),
        }
    
    def calculate_task_score(self, uav, task, environment):
        """计算任务分配评分
        
        评分规则：
        1. 距离因素：任务距离越远，评分越高（越差）
        2. 电池因素：电池电量越低，评分越高（越差）
        3. 负载因素：负载越重，评分越高（越差）
        4. 优先级因素：优先级越高，评分越低（越好）
        5. 中继因素：使用中继可以降低评分（改善）
        
        Args:
            uav: 无人机对象
            task: 任务对象
            environment: 环境对象
            
        Returns:
            tuple: (最佳评分, 是否使用中继, 决策信息)
        """
        # 计算直飞距离
        direct_distance = (
            (uav.position[0] - task.start_point[0]) ** 2
            + (uav.position[1] - task.start_point[1]) ** 2
        ) ** 0.5
        direct_distance += (
            (task.start_point[0] - task.end_point[0]) ** 2
            + (task.start_point[1] - task.end_point[1]) ** 2
        ) ** 0.5

        # 计算使用中继的距离和收益
        relay_benefit = 0.0
        relay_distance = direct_distance
        if environment.agvs:
            nearest_agv = min(
                environment.agvs,
                key=lambda agv: (
                    (agv.position[0] - task.start_point[0]) ** 2
                    + (agv.position[1] - task.start_point[1]) ** 2
                ) ** 0.5
            )
            relay_start_distance = (
                (uav.position[0] - nearest_agv.position[0]) ** 2
                + (uav.position[1] - nearest_agv.position[1]) ** 2
            ) ** 0.5
            relay_task_distance = (
                (nearest_agv.position[0] - task.start_point[0]) ** 2
                + (nearest_agv.position[1] - task.start_point[1]) ** 2
            ) ** 0.5
            relay_task_distance += (
                (task.start_point[0] - task.end_point[0]) ** 2
                + (task.start_point[1] - task.end_point[1]) ** 2
            ) ** 0.5
            relay_distance = relay_start_distance + relay_task_distance
            relay_benefit = max(0.0, direct_distance - relay_distance) / direct_distance

        # 计算各因素
        battery_factor = 1.0 + max(0.0, (100.0 - uav.battery) / 100.0 * 0.5)
        payload = float(getattr(task, "payload", 1.0))
        payload_factor = 1.0 + payload * 0.2
        priority_factor = 1.0 - (task.priority - 1) * 0.1
        priority_factor = max(0.5, priority_factor)

        # 计算评分
        direct_score = direct_distance * battery_factor * payload_factor * priority_factor
        relay_score = relay_distance * battery_factor * payload_factor * priority_factor * (1 - relay_benefit * 0.3)

        # 决策
        use_relay = relay_score < direct_score
        best_score = min(direct_score, relay_score)

        decision_info = {
            "direct_distance": direct_distance,
            "relay_distance": relay_distance,
            "relay_benefit": relay_benefit,
            "battery_level": uav.battery,
            "payload": payload,
            "priority": task.priority
        }

        return best_score, use_relay, decision_info

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
