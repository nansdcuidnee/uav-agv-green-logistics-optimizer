import json
from dataclasses import dataclass, field
from typing import Tuple, Optional


@dataclass
class Task:
    """配送任务类
    
    属性:
        id: 任务唯一标识符
        start_point: 起点位置 (x, y)
        end_point: 终点位置 (x, y)
        payload: 负载重量
        volume: 货物体积
        task_type: 任务类型（取货、送货、巡检等）
        priority: 优先级（1-5级）
        time_window: 时间窗口 (最早开始时间, 最晚完成时间)
        status: 状态（待分配、执行中、已完成）
        assigned_uav: 分配的无人机
        assigned_agv: 分配的AGV
        start_time: 开始执行时间
        completion_time: 完成时间
    """
    id: int
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    payload: float
    volume: float = field(default=1.0)
    task_type: str = field(default="delivery")  # pickup, delivery, inspection
    priority: int = field(default=1)
    time_window: Tuple[float, float] = field(default=(0.0, 1440.0))  # 分钟
    status: str = field(default="pending")  # pending, in_progress, completed
    assigned_uav: Optional[object] = field(default=None)
    assigned_agv: Optional[object] = field(default=None)
    start_time: Optional[float] = field(default=None)
    completion_time: Optional[float] = field(default=None)
    
    def __post_init__(self):
        """初始化后验证参数"""
        self._validate_parameters()
    
    def _validate_parameters(self):
        """验证参数的合理性"""
        # 验证优先级
        if not 1 <= self.priority <= 5:
            raise ValueError("优先级必须在1-5之间")
        
        # 验证时间窗口
        if self.time_window[0] >= self.time_window[1]:
            raise ValueError("最早开始时间必须小于最晚完成时间")
        
        # 验证负载和体积
        if self.payload < 0:
            raise ValueError("负载重量不能为负数")
        if self.volume < 0:
            raise ValueError("货物体积不能为负数")
        
        # 验证任务类型
        valid_task_types = ["pickup", "delivery", "inspection"]
        if self.task_type not in valid_task_types:
            raise ValueError(f"任务类型必须是以下之一: {valid_task_types}")
    
    def assign_to_uav(self, uav):
        """分配给无人机
        
        Args:
            uav: 无人机对象
        """
        self.assigned_uav = uav
        self.status = "in_progress"
    
    def assign_to_agv(self, agv):
        """分配给AGV
        
        Args:
            agv: AGV对象
        """
        self.assigned_agv = agv
        self.status = "in_progress"
    
    def start(self, current_time):
        """开始执行任务
        
        Args:
            current_time: 当前时间（分钟）
        """
        self.start_time = current_time
        self.status = "in_progress"
    
    def complete(self, current_time):
        """完成任务
        
        Args:
            current_time: 当前时间（分钟）
        """
        self.completion_time = current_time
        self.status = "completed"
    
    def to_dict(self):
        """将任务转换为字典格式
        
        Returns:
            dict: 任务的字典表示
        """
        return {
            "id": self.id,
            "start_point": self.start_point,
            "end_point": self.end_point,
            "payload": self.payload,
            "volume": self.volume,
            "task_type": self.task_type,
            "priority": self.priority,
            "time_window": self.time_window,
            "status": self.status,
            "start_time": self.start_time,
            "completion_time": self.completion_time
        }
    
    def to_json(self):
        """将任务转换为JSON格式
        
        Returns:
            str: 任务的JSON表示
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建任务
        
        Args:
            data: 任务的字典表示
        
        Returns:
            Task: 任务对象
        """
        return cls(
            id=data["id"],
            start_point=tuple(data["start_point"]),
            end_point=tuple(data["end_point"]),
            payload=data["payload"],
            volume=data.get("volume", 1.0),
            task_type=data.get("task_type", "delivery"),
            priority=data.get("priority", 1),
            time_window=tuple(data.get("time_window", (0.0, 1440.0))),
            status=data.get("status", "pending"),
            start_time=data.get("start_time"),
            completion_time=data.get("completion_time")
        )
    
    @classmethod
    def from_json(cls, json_str):
        """从JSON创建任务
        
        Args:
            json_str: 任务的JSON表示
        
        Returns:
            Task: 任务对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)