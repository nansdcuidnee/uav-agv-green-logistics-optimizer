from src.planning.path_planner import PathPlanner
from src.energy.energy_model import EnergyModel
from src.utils.math_utils import calculate_distance


# 固定充电站类
class ChargingStation:
    """固定充电站类
    
    属性：
        id: 充电站唯一标识符
        position: 充电站位置 (x, y)
        available: 是否可用
    """
    
    def __init__(self, station_id, position):
        """初始化充电站
        
        Args:
            station_id: 充电站ID
            position: 充电站位置 (x, y)
        """
        self.id = station_id
        self.position = position
        self.available = True
    
    def charge_uav(self, uav):
        """为无人机充电
        
        Args:
            uav: 无人机对象
        """
        # 固定充电站充电速度更快，每次充电增加30点电量
        uav.update_battery(30)
        print(f"充电站 {self.id} 为 UAV {uav.id} 充电，UAV电量从 {uav.battery - 30}% 增加到 {uav.battery}%")


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
        self.path_planner = PathPlanner()
        self.energy_model = EnergyModel()
    
    def fixed_charging(self, uavs, charging_stations):
        """固定充电策略
        
        Args:
            uavs: 无人机列表
            charging_stations: 固定充电站列表
        """
        for uav in uavs:
            if uav.needs_charging():
                # 找到最近的可用充电站
                available_stations = [station for station in charging_stations if station.available]
                if not available_stations:
                    print(f"没有可用的固定充电站为 UAV {uav.id} 充电")
                    continue
                
                nearest_station = min(available_stations, 
                                    key=lambda s: calculate_distance(uav.position, s.position))
                
                print(f"UAV {uav.id} 飞往充电站 {nearest_station.id} 充电")
                
                # 规划路径并移动到充电站
                path = self.path_planner.plan_path(uav.position, nearest_station.position)
                uav.update_position(path[-1])  # 移动到充电站位置
                
                # 充电直到电量充足
                while uav.needs_charging():
                    nearest_station.charge_uav(uav)
                
                print(f"UAV {uav.id} 充电完成，当前电量: {uav.battery}%")
    
    def mobile_charging(self, uavs, agvs):
        """移动充电策略
        
        Args:
            uavs: 无人机列表
            agvs: AGV列表
        """
        for uav in uavs:
            if uav.needs_charging():
                # 找到最近的空闲AGV
                available_agvs = [agv for agv in agvs if agv.status == "idle"]
                if not available_agvs:
                    print(f"没有可用的AGV为 UAV {uav.id} 充电")
                    continue
                
                nearest_agv = min(available_agvs, 
                                key=lambda a: calculate_distance(uav.position, a.position))
                
                print(f"AGV {nearest_agv.id} 前往 UAV {uav.id} 位置进行移动充电")
                
                # AGV移动到无人机位置
                nearest_agv.move_to(uav.position)
                nearest_agv.status = "charging"
                
                # 充电直到电量充足
                while uav.needs_charging():
                    nearest_agv.charge(uav)
                
                nearest_agv.status = "idle"
                print(f"UAV {uav.id} 移动充电完成，当前电量: {uav.battery}%")
    
    def predictive_charging(self, uavs, agvs, tasks):
        """预测性充电策略
        
        Args:
            uavs: 无人机列表
            agvs: AGV列表
            tasks: 任务列表
        """
        for uav in uavs:
            if uav.task:
                # 预测完成当前任务和未来任务所需的能量
                total_energy_needed = 0
                
                # 当前任务所需能量
                current_path = [uav.position, uav.task.start_point, uav.task.end_point]
                current_energy = self.energy_model.calculate_energy_uav(uav, current_path, (0, 0))
                total_energy_needed += current_energy
                
                # 未来任务所需能量
                for task in tasks:
                    if task.status == "pending":
                        future_path = [task.start_point, task.end_point]
                        future_energy = self.energy_model.calculate_energy_uav(uav, future_path, (0, 0))
                        total_energy_needed += future_energy
                
                # 计算剩余能量是否足够完成所有任务
                energy_consumption_per_step = self.energy_model.compute(uav)
                estimated_battery_after_tasks = uav.battery - total_energy_needed
                
                print(f"UAV {uav.id} 当前电量: {uav.battery}%，预计完成所有任务后剩余电量: {estimated_battery_after_tasks:.2f}%")
                
                # 如果预计电量不足，提前安排充电
                if estimated_battery_after_tasks < 20:
                    print(f"预测UAV {uav.id} 电量不足，提前安排充电")
                    
                    # 优先使用移动充电，因为它更灵活
                    available_agvs = [agv for agv in agvs if agv.status == "idle"]
                    if available_agvs:
                        nearest_agv = min(available_agvs, 
                                        key=lambda a: calculate_distance(uav.position, a.position))
                        
                        self.charge(uav, nearest_agv)
                    else:
                        print(f"没有可用的AGV，UAV {uav.id} 将继续执行任务")
    
    def charge(self, uav, agv):
        """执行充电
        
        Args:
            uav: 无人机对象
            agv: AGV对象
        """
        # 根据模式选择充电策略
        if self.mode == "fixed":
            print(f"使用固定充电策略为 UAV {uav.id} 充电")
            # 固定充电需要充电站，这里假设我们有一个默认充电站
            # 实际应用中应该传递充电站列表
        elif self.mode == "mobile":
            print(f"使用移动充电策略为 UAV {uav.id} 充电")
            # 充电直到电量充足
            while uav.needs_charging():
                agv.charge(uav)
        elif self.mode == "smart":
            print(f"使用智能充电策略为 UAV {uav.id} 充电")
            # 智能充电可以根据情况选择固定或移动充电
            # 这里简单实现为电量低于10%时使用移动充电，否则使用固定充电
            if uav.battery < 10:
                self.mode = "mobile"
            else:
                self.mode = "fixed"
            self.charge(uav, agv)
        else:
            print(f"使用默认充电策略为 UAV {uav.id} 充电")
            # 默认使用移动充电
            while uav.needs_charging():
                agv.charge(uav)