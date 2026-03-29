from src.utils.math_utils import calculate_distance
from config.config import UAV_CHARGE_THRESHOLD, ALPHA, BETA, GAMMA, DELTA


class Scheduler:
    """调度器类

    负责任务分配和调度，包含评分函数
    """

    def __init__(self):
        """初始化调度器"""
        pass

    def score_task(self, task, uav, alpha=0.25, beta=0.25, gamma=0.25, delta=0.25):
        """任务评分函数

        基于距离、电量、负载和优先级四个维度计算任务与无人机的匹配度评分。
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
        # 1. 距离评分：计算无人机当前位置到任务起点的距离
        # 使用最大可能距离进行归一化（假设地图最大尺寸为200）
        max_distance = 300  # 对角线距离
        distance = calculate_distance(uav.position, task.start_point)
        distance_score = 1 - min(distance / max_distance, 1.0)

        # 2. 电量评分：电量越高的无人机越适合
        battery_score = uav.battery / 100.0

        # 3. 负载评分：无人机负载能力大于任务需求得高分
        if uav.payload_capacity >= task.payload:
            load_score = 1.0
        else:
            # 负载不足时，得分为负载能力与需求的比例
            load_score = uav.payload_capacity / task.payload if task.payload > 0 else 0

        # 4. 优先级评分：优先级越高，任务越紧急
        # 假设优先级范围为1-5，归一化到0-1
        priority_score = min(task.priority / 5.0, 1.0)

        # 加权计算总分
        total_score = (alpha * distance_score +
                       beta * battery_score +
                       gamma * load_score +
                       delta * priority_score)

        return total_score

    def assign_tasks(self, tasks, uavs):
        """分配任务给无人机

        使用贪心算法，为每个待分配的任务选择评分最高的可用无人机。

        Args:
            tasks: 任务列表
            uavs: 无人机列表

        Returns:
            list: 分配结果列表，每个元素为 (task, uav) 元组
        """
        # 过滤出待分配的任务和空闲的无人机
        pending_tasks = [t for t in tasks if t.status == "pending" and t.assigned_uav is None]
        idle_uavs = [u for u in uavs if u.task is None]

        # 按优先级降序排序（优先分配高优先级任务）
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)

        assignments = []

        for task in pending_tasks:
            best_uav = None
            best_score = -1

            for uav in idle_uavs:
                # 跳过正在执行任务的无人机
                if uav.task is not None:
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
            if best_uav is not None:
                # 分配任务给无人机
                best_uav.assign_task(task)
                task.assign_to_uav(best_uav)
                assignments.append((task, best_uav))

                # 从空闲列表中移除（标记为已分配）
                idle_uavs.remove(best_uav)

        return assignments

    def schedule_charging(self, uavs, agvs):
        """调度充电

        协调AGV移动到低电量无人机位置进行充电。
        只调度电量低于阈值的无人机。

        Args:
            uavs: 无人机列表
            agvs: AGV列表

        Returns:
            list: 充电调度结果列表，每个元素为 (agv, uav) 元组
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

        for uav in uavs_needing_charge:
            if not idle_agvs:
                break  # 没有更多空闲AGV

            # 选择距离最近的空闲AGV
            best_agv = None
            min_distance = float('inf')

            for agv in idle_agvs:
                dist = calculate_distance(agv.position, uav.position)
                if dist < min_distance:
                    min_distance = dist
                    best_agv = agv

            if best_agv is not None:
                # 调度AGV前往无人机位置
                best_agv.update_status("transporting")
                best_agv.charge_uav(uav)

                charging_assignments.append((best_agv, uav))
                idle_agvs.remove(best_agv)

        return charging_assignments