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



        # 子类实现具体的任务评分逻辑
        pass
    

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

        # 子类实现具体的任务分配逻辑
        pass
    
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

        # 子类实现具体的充电调度逻辑
        pass
    
    def select_agv(self, uav, agvs):
        """选择AGV为无人机充电
        
        Args:
            uav: 无人机对象
            agvs: AGV列表
            
        Returns:
            AGV: 选中的AGV
        """
        # 子类实现具体的AGV选择逻辑
        # 临时返回第一个AGV，实际项目中需要根据具体算法选择
        return agvs[0]

