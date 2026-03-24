class ChargingStrategy:
    """充电策略类
    
    包含三种充电方法：固定、移动和预测性
    """
    
    def __init__(self, mode="mobile"):
        """初始化充电策略
        
        Args:
            mode: 充电模式，可选值："fixed", "mobile", "smart"
        """
        self.mode = mode
    
    def fixed_charging(self, uavs, charging_stations):
        """固定充电策略
        
        Args:
            uavs: 无人机列表
            charging_stations: 固定充电站列表
        """
        # 子类实现具体的固定充电策略逻辑
        pass
    
    def mobile_charging(self, uavs, agvs):
        """移动充电策略
        
        Args:
            uavs: 无人机列表
            agvs: AGV列表
        """
        # 子类实现具体的移动充电策略逻辑
        pass
    
    def predictive_charging(self, uavs, agvs, tasks):
        """预测性充电策略
        
        Args:
            uavs: 无人机列表
            agvs: AGV列表
            tasks: 任务列表
        """
        # 子类实现具体的预测性充电策略逻辑
        pass
    
    def charge(self, uav, agv):
        """执行充电
        
        Args:
            uav: 无人机对象
            agv: AGV对象
        """
        # 根据模式选择充电策略
        if self.mode == "fixed":
            print(f"使用固定充电策略为 UAV {uav.id} 充电")
            # 子类实现具体的固定充电逻辑
        elif self.mode == "mobile":
            print(f"使用移动充电策略为 UAV {uav.id} 充电")
            # 子类实现具体的移动充电逻辑
        elif self.mode == "smart":
            print(f"使用智能充电策略为 UAV {uav.id} 充电")
            # 子类实现具体的智能充电逻辑
        else:
            print(f"使用默认充电策略为 UAV {uav.id} 充电")
        
        # 调用AGV充电
        agv.charge(uav)