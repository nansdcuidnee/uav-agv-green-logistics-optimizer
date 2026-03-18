class Task:
    """配送任务类
    
    属性:
        id: 任务唯一标识符
        start_point: 起点位置 (x, y)
        end_point: 终点位置 (x, y)
        payload: 负载重量
        priority: 优先级
        status: 状态（待分配、执行中、已完成）
        assigned_uav: 分配的无人机
    """
    
    def __init__(self, task_id, start_point, end_point, payload, priority=1):
        """初始化任务
        
        Args:
            task_id: 任务ID
            start_point: 起点位置 (x, y)
            end_point: 终点位置 (x, y)
            payload: 负载重量
            priority: 优先级
        """
        self.id = task_id
        self.start_point = start_point
        self.end_point = end_point
        self.payload = payload
        self.priority = priority
        self.status = "pending"  # pending, in_progress, completed
        self.assigned_uav = None
    
    def assign_to_uav(self, uav):
        """分配给无人机
        
        Args:
            uav: 无人机对象
        """
        # 实现任务分配逻辑
        pass
    
    def start(self):
        """开始执行任务"""
        # 实现任务开始逻辑
        pass
    
    def complete(self):
        """完成任务"""
        # 实现任务完成逻辑
        pass