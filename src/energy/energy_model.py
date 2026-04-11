class EnergyModel:
    """能耗模型类
    
    提供能耗计算函数，考虑距离、负载和风速等因素
    """
    
    def __init__(self):
        """初始化能耗模型"""
        # 能耗参数
        self.takeoff_energy_base = 10.0  # 起飞基础能耗
        self.cruise_energy_per_km = 5.0  # 巡航每公里能耗
        self.hover_energy_per_min = 2.0  # 悬停每分钟能耗
        self.landing_energy_base = 5.0  # 降落基础能耗
        self.agv_energy_per_km = 3.0  # AGV每公里能耗
    
    def calculate_takeoff_energy(self, uav, payload):
        """计算起飞能耗
        
        Args:
            uav: 无人机对象
            payload: 负载重量
            
        Returns:
            float: 起飞能耗值
        """
        # 起飞能耗与负载成正比
        payload_factor = 1.0 + (payload / uav.max_payload) * 0.5
        return self.takeoff_energy_base * payload_factor
    
    def calculate_cruise_energy(self, uav, distance, payload, wind=0):
        """计算巡航能耗
        
        Args:
            uav: 无人机对象
            distance: 巡航距离（米）
            payload: 负载重量
            wind: 风速（米/秒）
            
        Returns:
            float: 巡航能耗值
        """
        # 转换为公里
        distance_km = distance / 1000
        # 负载因素
        payload_factor = 1.0 + (payload / uav.max_payload) * 0.3
        # 风速因素（逆风增加能耗）
        wind_factor = 1.0 + (wind / 10) * 0.2
        return self.cruise_energy_per_km * distance_km * payload_factor * wind_factor
    
    def calculate_hover_energy(self, uav, duration, payload):
        """计算悬停能耗
        
        Args:
            uav: 无人机对象
            duration: 悬停时间（分钟）
            payload: 负载重量
            
        Returns:
            float: 悬停能耗值
        """
        # 负载因素
        payload_factor = 1.0 + (payload / uav.max_payload) * 0.4
        return self.hover_energy_per_min * duration * payload_factor
    
    def calculate_landing_energy(self, uav, payload):
        """计算降落能耗
        
        Args:
            uav: 无人机对象
            payload: 负载重量
            
        Returns:
            float: 降落能耗值
        """
        # 降落能耗与负载成正比
        payload_factor = 1.0 + (payload / uav.max_payload) * 0.3
        return self.landing_energy_base * payload_factor
    
    def calculate_total_energy(self, uav, distance, duration, payload, wind=0):
        """计算总能耗
        
        Args:
            uav: 无人机对象
            distance: 飞行距离（米）
            duration: 飞行时间（分钟）
            payload: 负载重量
            wind: 风速（米/秒）
            
        Returns:
            float: 总能耗值
        """
        takeoff = self.calculate_takeoff_energy(uav, payload)
        cruise = self.calculate_cruise_energy(uav, distance, payload, wind)
        hover = self.calculate_hover_energy(uav, duration * 0.2, payload)  # 假设20%时间在悬停
        landing = self.calculate_landing_energy(uav, payload)
        return takeoff + cruise + hover + landing
    
    def calculate_energy_agv(self, agv, distance):
        """计算AGV能耗
        
        Args:
            agv: AGV对象
            distance: 行驶距离（米）
            
        Returns:
            float: AGV能耗值
        """
        # 转换为公里
        distance_km = distance / 1000
        return self.agv_energy_per_km * distance_km
    
    def compute(self, uav):
        """计算无人机能耗
        
        Args:
            uav: 无人机对象
            
        Returns:
            float: 能耗值
        """
        if uav.task:
            distance = (
                (uav.position[0] - uav.task.end_point[0]) ** 2
                + (uav.position[1] - uav.task.end_point[1]) ** 2
            ) ** 0.5
            payload = float(getattr(uav.task, "payload", 1.0))
            # 估算飞行时间（分钟）
            duration = distance / (uav.max_speed * 60)  # 转换为分钟
            return self.calculate_total_energy(uav, distance, duration, payload)
        else:
            # 没有任务时，能耗较低
            return 0.5