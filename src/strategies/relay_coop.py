"""Relay cooperative strategy."""

from typing import Any, Dict

from .base import BaseStrategy


class RelayCoopStrategy(BaseStrategy):
    """Assign nearest-AGV-assisted tasks and prefer paired AGV for charging."""

    def __init__(self, relay_distance: float = 200.0):
        super().__init__("relay_coop")
        self.relay_distance = relay_distance

    def assign_tasks(self, environment) -> Dict[str, Any]:
        idle_uavs = self.get_idle_uavs(environment)
        pending_tasks = self.get_pending_tasks(environment)

        assignments = []
        actions = []

        # 可用 AGV 集合（每次分配后移除已分配的 AGV，避免同一轮重复分配）
        available_agvs = list(environment.agvs)

        for task in pending_tasks:
            if not idle_uavs:
                break
            if not available_agvs:
                break

            # 从可用 AGV 集合中选择最近的 AGV（而不是全量 environment.agvs）
            nearest_agv = min(
                available_agvs,
                key=lambda agv: (
                    (agv.position[0] - task.start_point[0]) ** 2
                    + (agv.position[1] - task.start_point[1]) ** 2
                )
                ** 0.5,
            )

            # 从可用集合中移除已分配的 AGV
            available_agvs.remove(nearest_agv)

            # 计算 AGV 到任务起点的距离
            agv_to_task_distance = ((nearest_agv.position[0] - task.start_point[0]) ** 2 + 
                                   (nearest_agv.position[1] - task.start_point[1]) ** 2) ** 0.5
            
            # 动态计算中继点距离，不超过 AGV 到任务起点距离的一半
            relay_distance = min(self.relay_distance, agv_to_task_distance / 2)
            
            if relay_distance < 10:  # 如果距离太近，直接使用直接配送
                uav = idle_uavs.pop(0)
                uav.assign_task(task)
                task.status = "in_progress"  # 直接设置为进行中
                task.assigned_uav = uav
                
                assignments.append({
                    "uav_id": uav.id,
                    "task_id": task.id,
                    "agv_id": None,
                })
                continue

            direction = self._calculate_direction(nearest_agv.position, task.start_point)
            relay_point = (
                nearest_agv.position[0] + direction[0] * relay_distance,
                nearest_agv.position[1] + direction[1] * relay_distance,
            )

            # 计算 AGV 移动距离
            agv_move_distance = ((nearest_agv.position[0] - relay_point[0]) ** 2 + 
                               (nearest_agv.position[1] - relay_point[1]) ** 2) ** 0.5
            
            # 记录 AGV 移动信息到任务
            task.agv_move_distance = agv_move_distance
            task.relay_point = relay_point
            task.assigned_agv = nearest_agv
            task.assigned_time = 0  # 用于跟踪等待时间

            # 添加移动AGV的行动意图
            actions.append({
                "action": "move_agv_to_relay",
                "agv_id": nearest_agv.id,
                "relay_point": relay_point,
                "task_id": task.id
            })

            uav = idle_uavs.pop(0)
            uav.assign_task(task)
            task.status = "waiting_for_agv"  # 任务状态改为等待AGV
            task.assigned_uav = uav

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
            "actions": actions,
            "assigned_count": len(assignments),
        }

    def select_charging_station(self, uav, environment):
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
