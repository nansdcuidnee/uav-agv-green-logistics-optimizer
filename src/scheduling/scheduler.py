from src.utils.math_utils import calculate_distance
from config.config import (
    UAV_CHARGE_THRESHOLD, ALPHA, BETA, GAMMA, DELTA,
    MAP_SIZE, UAV_SPEED, AGV_SPEED, AGV_CHARGING_CAPACITY,
    BASE_ENERGY_CONSUMPTION, PAYLOAD_ENERGY_FACTOR
)


class Scheduler:
    """调度器类

    负责任务分配和调度，包含评分函数
    """

    def __init__(self):
        """初始化调度器"""
        # 计算地图对角线最大距离
        self.max_distance = (MAP_SIZE[0] ** 2 + MAP_SIZE[1] ** 2) ** 0.5

    def calculate_energy_consumption(self, uav, task):
        """计算无人机执行任务的预估能耗

        Args:
            uav: 无人机对象
            task: 任务对象

        Returns:
            float: 预估能耗
        """
        # 计算往返距离（从当前位置到起点，再到终点，最后返回起点附近）
        distance_to_start = calculate_distance(uav.position, task.start_point)
        task_distance = calculate_distance(task.start_point, task.end_point)
        # 假设任务完成后返回起始点附近（简化模型）
        return_distance = calculate_distance(task.end_point, uav.position)

        total_distance = distance_to_start + task_distance + return_distance

        # 能耗 = 基础能耗 + 距离能耗 + 负载能耗
        distance_energy = total_distance / UAV_SPEED * BASE_ENERGY_CONSUMPTION
        payload_energy = task.distance * PAYLOAD_ENERGY_FACTOR if hasattr(task, 'distance') else 0

        return distance_energy + payload_energy

    def can_complete_task(self, uav, task):
        """检查无人机是否有足够电量完成任务

        Args:
            uav: 无人机对象
            task: 任务对象

        Returns:
            bool: 是否可以完成任务的bool值
        """
        energy_needed = self.calculate_energy_consumption(uav, task)
        # 保留10%的电量作为安全余量
        safe_battery = uav.battery * 0.9
        return safe_battery >= energy_needed

    def score_task(self, task, uav, alpha=0.25, beta=0.25, gamma=0.25, delta=0.25):
        """任务评分函数

        基于距离、电量、负载、优先级和任务可行性五个维度计算任务与无人机的匹配度评分。
        评分越高，无人机越适合执行该任务。

        Args:
            task: 任务对象
            uav: 无人机对象
            alpha: 距离权重
            beta: 电量权重
            gamma: 负载权重
            delta: 优先级权重

        Returns:
            float: 评分值 (0-1之间，越高越适合)
        """
        # 0. 任务可行性检查：如果电量不足，直接返回最低分
        if not self.can_complete_task(uav, task):
            return 0.0

        # 1. 距离评分：计算无人机当前位置到任务起点的距离
        distance = calculate_distance(uav.position, task.start_point)
        distance_score = 1 - min(distance / self.max_distance, 1.0)

        # 2. 电量评分：电量越高的无人机越适合
        battery_score = uav.battery / 100.0

        # 3. 负载评分：无人机负载能力大于任务需求得高分
        if uav.payload_capacity >= task.payload:
            load_score = 1.0
        else:
            # 负载不足时，得分为负载能力与需求的比例
            load_score = uav.payload_capacity / task.payload if task.payload > 0 else 0

        # 4. 优先级评分：优先级越高，任务越紧急
        # 从配置读取默认优先级进行归一化
        max_priority = 5  # 假设最大优先级为5
        priority_score = min(task.priority / max_priority, 1.0)

        # 5. 能效评分：执行任务后的剩余电量比例（越高越好）
        energy_needed = self.calculate_energy_consumption(uav, task)
        remaining_battery = uav.battery - energy_needed
        efficiency_score = max(remaining_battery / 100.0, 0)

        # 加权计算总分（加入额外的能效权重）
        total_score = (alpha * distance_score +
                       beta * battery_score +
                       gamma * load_score +
                       delta * priority_score +
                       0.1 * efficiency_score)

        return total_score

    def assign_tasks(self, tasks, uavs):
        """分配任务给无人机

        使用贪心算法，为每个待分配的任务选择评分最高的可用无人机。
        优先分配高优先级任务，并确保无人机有足够电量完成任务。

        Args:
            tasks: 任务列表
            uavs: 无人机列表

        Returns:
            tuple: (分配结果列表, 未分配任务列表)
                   分配结果列表每个元素为 (task, uav) 元组
                   未分配任务列表为无法分配的任务列表
        """
        # 过滤出待分配的任务和空闲的无人机
        pending_tasks = [t for t in tasks if t.status == "pending" and t.assigned_uav is None]
        idle_uavs = [u for u in uavs if u.task is None]

        # 按优先级降序排序（优先分配高优先级任务）
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)

        assignments = []
        unassigned_tasks = []

        for task in pending_tasks:
            best_uav = None
            best_score = -1

            for uav in idle_uavs:
                # 跳过正在执行任务的无人机
                if uav.task is not None:
                    continue

                # 预先检查任务可行性
                if not self.can_complete_task(uav, task):
                    continue

                # 计算评分
                score = self.score_task(
                    task, uav,
                    alpha=ALPHA, beta=BETA, gamma=GAMMA, delta=DELTA
                )

                if score > best_score:
                    best_score = score
                    best_uav = uav

            # 如果找到合适的无人机，则分配任务
            if best_uav is not None and best_score > 0:
                # 分配任务给无人机
                best_uav.assign_task(task)
                task.assign_to_uav(best_uav)
                assignments.append((task, best_uav))

                # 从空闲列表中移除
                idle_uavs.remove(best_uav)
            else:
                # 无法分配的任务记录下来
                unassigned_tasks.append(task)

        return assignments, unassigned_tasks

    def estimate_charging_time(self, uav, agv):
        """估算AGV到达无人机位置并充满电所需时间

        Args:
            uav: 无人机对象
            agv: AGV对象

        Returns:
            float: 预计充电所需时间步数
        """
        # 计算AGV到达无人机位置的距离和时间
        distance = calculate_distance(agv.position, uav.position)
        travel_time = distance / AGV_SPEED

        # 计算需要充入的电量
        energy_to_charge = 100 - uav.battery
        # 充电时间 = 需要充入的电量 / 充电能力
        charging_time = max(energy_to_charge / AGV_CHARGING_CAPACITY, 0)

        return travel_time + charging_time

    def can_agv_reach_uav(self, agv, uav):
        """检查AGV是否有足够电量到达无人机位置

        Args:
            agv: AGV对象
            uav: 无人机对象

        Returns:
            bool: 是否可以到达
        """
        distance = calculate_distance(agv.position, uav.position)
        # 假设AGV基础能耗与速度相关
        energy_needed = distance / AGV_SPEED * 0.5
        return agv.battery >= energy_needed

    def schedule_charging(self, uavs, agvs):
        """调度充电

        协调AGV移动到低电量无人机位置进行充电。
        只调度电量低于阈值的无人机，并考虑AGV的到达时间和电量。

        Args:
            uavs: 无人机列表
            agvs: AGV列表

        Returns:
            tuple: (充电调度结果列表, 未能调度的无人机列表)
                   调度结果每个元素为 (agv, uav, estimated_time) 元组
        """
        # 找出需要充电的无人机（电量低于阈值且没有正在执行任务）
        uavs_needing_charge = [
            u for u in uavs
            if u.battery < UAV_CHARGE_THRESHOLD and u.task is None
        ]

        # 按电量升序排序（优先给电量最低的无人机充电）
        uavs_needing_charge.sort(key=lambda u: u.battery)

        # 找出空闲的AGV
        idle_agvs = [a for a in agvs if a.status == "idle"]

        charging_assignments = []
        unassigned_uavs = []

        for uav in uavs_needing_charge:
            if not idle_agvs:
                unassigned_uavs.append(uav)
                continue

            # 选择距离最近的可用AGV（且电量足够到达）
            best_agv = None
            min_distance = float('inf')

            for agv in idle_agvs:
                # 检查AGV是否有足够电量到达无人机位置
                if not self.can_agv_reach_uav(agv, uav):
                    continue

                dist = calculate_distance(agv.position, uav.position)
                if dist < min_distance:
                    min_distance = dist
                    best_agv = agv

            if best_agv is not None:
                # 估算充电所需时间
                estimated_time = self.estimate_charging_time(best_agv, uav)

                # 调度AGV前往无人机位置
                best_agv.update_status("transporting")
                best_agv.charge_uav(uav)

                charging_assignments.append((best_agv, uav, estimated_time))
                idle_agvs.remove(best_agv)
            else:
                unassigned_uavs.append(uav)

        return charging_assignments, unassigned_uavs
