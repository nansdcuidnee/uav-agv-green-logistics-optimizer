class UAV:
    """无人机类
    
    属性：
        id: 无人机唯一标识符
        position: 当前位置 (x, y)
        battery: 电量百分比 (0-100)
        path: 飞行路径
        task: 当前执行的任务
    """
    
    def __init__(self, uav_id, position):
        """初始化无人机
        
        Args:
            uav_id: 无人机ID
            position: 初始位置 (x, y)
        """
        self.id = uav_id
        self.position = position
        self.battery = 100  # 初始电量为100
        self.path = []  # 飞行路径
        self.task = None  # 当前任务
    
    def update_position(self, new_position):
        """更新无人机位置
        
        Args:
            new_position: 新位置 (x, y)
        """
        self.position = new_position
    
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
        return self.battery < 20
    
    def assign_task(self, task):
        """分配任务
        
        Args:
            task: 任务对象
        """
        self.task = task
    
    def complete_task(self):
        """完成当前任务"""
        self.task = None
    
    def is_idle(self):
        """判断无人机是否空闲
        
        Returns:
            bool: 是否空闲
        """
        return self.task is None and len(self.path) == 0