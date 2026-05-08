import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from config.config import UAV_CHARGE_THRESHOLD


@dataclass
class UAV:
    """无人机类
    
    属性：
        id: 无人机唯一标识符
        position: 当前位置 (x, y)
        battery: 电量百分比 (0-100)
        max_payload: 最大负载能力 (kg)
        max_speed: 最大飞行速度 (m/s)
        max_endurance: 最大续航时间 (min)
        max_range: 最大作业半径 (m)
        hover_energy_consumption: 悬停能耗 (W)
        wind_resistance: 抗风能力 (m/s)
        path: 飞行路径
        task: 当前执行的任务
        status: 状态
    """
    id: int
    position: Tuple[float, float]
    max_payload: float = field(default=5.0)
    max_speed: float = field(default=10.0)
    max_endurance: float = field(default=30.0)
    max_range: float = field(default=2000.0)
    hover_energy_consumption: float = field(default=50.0)
    wind_resistance: float = field(default=10.0)
    battery: float = field(default=100.0)
    path: List[Tuple[float, float]] = field(default_factory=list)  # 剩余路径
    path_history: List[Tuple[float, float]] = field(default_factory=list)  # 历史轨迹
    task: Optional[object] = field(default=None)
    status: str = field(default="idle")  # idle, busy, charging
    
    def __post_init__(self):
        """初始化后验证参数"""
        self._validate_parameters()
        # 将初始位置添加到历史轨迹
        self.path_history.append(self.position)
    
    def _validate_parameters(self):
        """验证参数的合理性"""
        if self.max_payload < 0:
            raise ValueError("最大负载能力不能为负数")
        if self.max_speed <= 0:
            raise ValueError("最大飞行速度必须大于0")
        if self.max_endurance <= 0:
            raise ValueError("最大续航时间必须大于0")
        if self.max_range <= 0:
            raise ValueError("最大作业半径必须大于0")
        if self.hover_energy_consumption < 0:
            raise ValueError("悬停能耗不能为负数")
        if self.wind_resistance < 0:
            raise ValueError("抗风能力不能为负数")
    
    def update_position(self, new_position):
        """更新无人机位置
        
        Args:
            new_position: 新位置 (x, y)
        """
        self.position = new_position
        self.path_history.append(new_position)
    
    def update_battery(self, amount):
        """更新电量
        
        Args:
            amount: 电量变化值（正数为充电，负数为耗电）
        """
        self.battery = max(0, min(100, self.battery + amount))
    
    def needs_charging(self):
        """判断是否需要充电
        
        Returns:
            bool: 是否需要充电
        """
        return self.battery < UAV_CHARGE_THRESHOLD
    
    def assign_task(self, task):
        """分配任务
        
        Args:
            task: 任务对象
        """
        self.task = task
        self.status = "busy"
    
    def complete_task(self):
        """完成当前任务"""
        self.task = None
        self.status = "idle"
    
    def is_idle(self):
        """判断无人机是否空闲
        
        Returns:
            bool: 是否空闲
        """
        return self.status == "idle"
    
    def calculate_energy_consumption(self, distance, payload, height_diff=0):
        """计算飞行能耗
        
        Args:
            distance: 飞行距离 (m)
            payload: 负载重量 (kg)
            height_diff: 高度差 (m)
        
        Returns:
            float: 能耗百分比
        """
        # 基础能耗：与距离成正比
        base_consumption = distance / (self.max_range * 2) * 100
        
        # 负载能耗：与负载重量成正比
        payload_factor = 1 + (payload / self.max_payload) * 0.5
        
        # 高度能耗：上升消耗更多能量
        height_factor = 1 + max(0, height_diff) / 1000 * 0.2
        
        total_consumption = base_consumption * payload_factor * height_factor
        return total_consumption
    
    def can_carry(self, payload, volume):
        """判断是否能携带指定负载
        
        Args:
            payload: 负载重量 (kg)
            volume: 货物体积
        
        Returns:
            bool: 是否能携带
        """
        return payload <= self.max_payload
    
    def get_remaining_range(self):
        """获取剩余续航里程
        
        Returns:
            float: 剩余续航里程 (m)
        """
        return self.max_range * (self.battery / 100)
    
    def get_flight_time(self, distance, speed=None):
        """计算飞行时间
        
        Args:
            distance: 飞行距离 (m)
            speed: 飞行速度 (m/s)，默认使用最大速度
        
        Returns:
            float: 飞行时间 (min)
        """
        if speed is None:
            speed = self.max_speed
        time_seconds = distance / speed
        return time_seconds / 60