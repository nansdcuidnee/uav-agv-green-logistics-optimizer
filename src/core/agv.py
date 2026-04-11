from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class AGV:
    """地面车辆类
    
    属性：
        id: AGV唯一标识符
        position: 当前位置 (x, y)
        max_payload: 最大负载能力 (kg)
        max_speed: 最大行驶速度 (m/s)
        max_endurance: 最大续航时间 (min)
        max_range: 最大作业半径 (m)
        start_time: 启动时间 (s)
        docking_time: 停靠时间 (s)
        turning_radius: 转弯半径 (m)
        charging_power: 充电功率 (W)
        status: 状态
        path: 行驶路径
        task: 当前执行的任务
    """
    id: int
    position: Tuple[float, float]
    max_payload: float = field(default=20.0)
    max_speed: float = field(default=5.0)
    max_endurance: float = field(default=120.0)
    max_range: float = field(default=5000.0)
    start_time: float = field(default=5.0)
    docking_time: float = field(default=10.0)
    turning_radius: float = field(default=2.0)
    charging_power: float = field(default=200.0)
    status: str = field(default="idle")  # idle, transporting, charging
    path: List[Tuple[float, float]] = field(default_factory=list)  # 剩余路径
    path_history: List[Tuple[float, float]] = field(default_factory=list)  # 历史轨迹
    task: Optional[object] = field(default=None)
    
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
            raise ValueError("最大行驶速度必须大于0")
        if self.max_endurance <= 0:
            raise ValueError("最大续航时间必须大于0")
        if self.max_range <= 0:
            raise ValueError("最大作业半径必须大于0")
        if self.start_time < 0:
            raise ValueError("启动时间不能为负数")
        if self.docking_time < 0:
            raise ValueError("停靠时间不能为负数")
        if self.turning_radius < 0:
            raise ValueError("转弯半径不能为负数")
        if self.charging_power < 0:
            raise ValueError("充电功率不能为负数")
    
    def move_to(self, target_position):
        """移动到目标位置
        
        Args:
            target_position: 目标位置 (x, y)
        """
        self.position = target_position
        self.path_history.append(target_position)
    
    def charge(self, uav):
        """为无人机充电
        
        Args:
            uav: 无人机对象
        """
        # 简单的固定步长充电模型
        uav.update_battery(20)
        print(
            f"AGV {self.id} charged UAV {uav.id}: "
            f"{max(0, uav.battery - 20)}% -> {uav.battery}%"
        )
    
    def assign_task(self, task):
        """分配任务
        
        Args:
            task: 任务对象
        """
        self.task = task
        self.status = "transporting"
    
    def complete_task(self):
        """完成当前任务"""
        self.task = None
        self.status = "idle"
    
    def is_idle(self):
        """判断AGV是否空闲
        
        Returns:
            bool: 是否空闲
        """
        return self.status == "idle"
    
    def calculate_energy_consumption(self, distance, payload, speed=None):
        """计算行驶能耗
        
        Args:
            distance: 行驶距离 (m)
            payload: 负载重量 (kg)
            speed: 行驶速度 (m/s)，默认使用最大速度
        
        Returns:
            float: 能耗百分比
        """
        if speed is None:
            speed = self.max_speed
        
        # 基础能耗：与距离成正比
        base_consumption = distance / (self.max_range * 2) * 100
        
        # 负载能耗：与负载重量成正比
        payload_factor = 1 + (payload / self.max_payload) * 0.3
        
        # 速度能耗：速度越快能耗越高
        speed_factor = 1 + (speed / self.max_speed) * 0.2
        
        total_consumption = base_consumption * payload_factor * speed_factor
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
        # 简化模型，假设电量与续航里程成正比
        return self.max_range * 0.8  # 假设剩余80%的续航里程
    
    def get_driving_time(self, distance, speed=None):
        """计算行驶时间
        
        Args:
            distance: 行驶距离 (m)
            speed: 行驶速度 (m/s)，默认使用最大速度
        
        Returns:
            float: 行驶时间 (min)
        """
        if speed is None:
            speed = self.max_speed
        time_seconds = distance / speed + self.start_time + self.docking_time
        return time_seconds / 60