class UAV:
    """无人机类
    
    属性:
        id: 无人机唯一标识符
        position: 当前位置 (x, y)
        battery: 电量百分比 (0-100)
        task: 当前执行的任务
        max_battery: 最大电量
        payload_capacity: 最大负载能力
        speed: 飞行速度
    """
    
    def __init__(self, uav_id, position, battery=100, max_battery=100, payload_capacity=5, speed=10):
        """初始化无人机
        
        Args:
            uav_id: 无人机ID
            position: 初始位置 (x, y)
            battery: 初始电量
            max_battery: 最大电量
            payload_capacity: 最大负载
            speed: 飞行速度
        """
        self.id = uav_id
        self.position = position
        self.battery = battery
        self.task = None
        self.max_battery = max_battery
        self.payload_capacity = payload_capacity
        self.speed = speed
    
    def update_position(self, new_position):
        """更新无人机位置
        
        Args:
            new_position: 新位置 (x, y)
        """
        # 实现位置更新逻辑
        pass
    
    def update_battery(self, amount):
        """更新电量
        
        Args:
            amount: 电量变化值（正数为充电，负数为耗电）
        """
        # 实现电量更新逻辑
        pass
    
    def assign_task(self, task):
        """分配任务
        
        Args:
            task: 任务对象
        """
        # 实现任务分配逻辑
        pass
    
    def complete_task(self):
        """完成当前任务"""
        # 实现任务完成逻辑
        pass
    
    def needs_charging(self):
        """判断是否需要充电
        
        Returns:
            bool: 是否需要充电
        """
        # 实现充电需求判断逻辑
        pass