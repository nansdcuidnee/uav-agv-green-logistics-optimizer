class AGV:
    """地面车辆类
    
    属性:
        id: AGV唯一标识符
        position: 当前位置 (x, y)
        status: 状态（空闲、运输、充电）
        battery: 电量百分比 (0-100)
        max_battery: 最大电量
        speed: 行驶速度
        charging_capacity: 充电能力
    """
    
    def __init__(self, agv_id, position, battery=100, max_battery=100, speed=5, charging_capacity=20):
        """初始化AGV
        
        Args:
            agv_id: AGV ID
            position: 初始位置 (x, y)
            battery: 初始电量
            max_battery: 最大电量
            speed: 行驶速度
            charging_capacity: 充电能力
        """
        self.id = agv_id
        self.position = position
        self.status = "idle"  # idle, transporting, charging
        self.battery = battery
        self.max_battery = max_battery
        self.speed = speed
        self.charging_capacity = charging_capacity
    
    def update_position(self, new_position):
        """更新AGV位置
        
        Args:
            new_position: 新位置 (x, y)
        """
        # 实现位置更新逻辑
        pass
    
    def update_status(self, new_status):
        """更新状态
        
        Args:
            new_status: 新状态
        """
        # 实现状态更新逻辑
        pass
    
    def update_battery(self, amount):
        """更新电量
        
        Args:
            amount: 电量变化值（正数为充电，负数为耗电）
        """
        # 实现电量更新逻辑
        pass
    
    def charge_uav(self, uav):
        """为无人机充电
        
        Args:
            uav: 无人机对象
        """
        # 实现为无人机充电的逻辑
        pass