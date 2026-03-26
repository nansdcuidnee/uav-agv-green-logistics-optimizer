class AGV:
    """地面车辆类
    
    属性：
        id: AGV唯一标识符
        position: 当前位置 (x, y)
        status: 状态（空闲、运输、充电）
    """
    
    def __init__(self, agv_id, position):
        """初始化AGV
        
        Args:
            agv_id: AGV ID
            position: 初始位置 (x, y)
        """
        self.id = agv_id
        self.position = position
        self.status = "idle"  # idle, transporting, charging
    
    def move_to(self, target_position):
        """移动到目标位置
        
        Args:
            target_position: 目标位置 (x, y)
        """
        self.position = target_position
    
    def charge(self, uav):
        """为无人机充电
        
        Args:
            uav: 无人机对象
        """
        # 为无人机充电，每次充电增加20点电量
        uav.update_battery(20)
        print(f"AGV {self.id} 为 UAV {uav.id} 充电，UAV电量从 {uav.battery - 20}% 增加到 {uav.battery}%")