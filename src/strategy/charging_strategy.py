import sys
import os
import matplotlib.pyplot as plt
import time


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
    
    def __init__(self, mode="mobile", enable_visualization=False):
        """初始化充电策略
        
        Args:
            mode: 充电模式，可选值："fixed", "mobile", "smart"
            enable_visualization: 是否启用可视化
        """
        self.mode = mode
        self.path_planner = PathPlanner()
        self.energy_model = EnergyModel()
        self.enable_visualization = enable_visualization
        
        # 初始化可视化
        if self.enable_visualization:
            self._init_visualization()
    

    

    
    def _init_visualization(self):
        """初始化可视化窗口"""
        # 设置matplotlib字体支持中文
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        
        plt.ion()  # 启用交互模式
        self.fig, self.ax = plt.subplots(figsize=(12, 10))  # 增大窗口尺寸以容纳表格
        self.fig.canvas.manager.set_window_title('UAV Charging Strategy Visualization')
        
        # 设置坐标轴
        self.ax.set_xlim(0, 500)
        self.ax.set_ylim(0, 500)
        self.ax.set_xlabel('X Position')
        self.ax.set_ylabel('Y Position')
        self.ax.set_title('UAV Charging Strategy Visualization')
        self.ax.grid(True)
    
    def _display_charging_info(self, uavs, charging_stations, agvs):
        """在可视化窗口中显示无人机充电信息表格
        
        Args:
            uavs: 无人机列表
            charging_stations: 固定充电站列表
            agvs: AGV列表
        """
        # 创建表格数据
        table_data = [
            ["无人机ID", "充电方式", "充电时间", "充电接口类型", "电池容量", "充电注意事项"]
        ]
        
        # 为每个无人机添加充电信息
        for uav in uavs:
            # 使用实际的充电方式决策逻辑
            actual_charging_method = self.decide_charging_method(uav, charging_stations, agvs)
            charging_method = "移动充电" if actual_charging_method == "mobile" else "固定充电"
            
            # 根据实际充电方式计算充电时间
            charge_needed = 100 - uav.battery
            if actual_charging_method == "fixed":
                # 固定充电：30%电量/分钟（与系统一致）
                charging_time = f"{charge_needed / 30:.1f}分钟"
            else:
                # 移动充电：10%电量/分钟（与系统一致）
                charging_time = f"{charge_needed / 10:.1f}分钟"
            
            # 真实的充电注意事项
            if uav.battery < 15:
                notes = "电量低于15%，触发紧急移动充电"
            elif uav.needs_charging():
                notes = "电量低于20%，触发充电"
            else:
                notes = "电量充足，无需充电"
            
            table_data.append([
                uav.id,
                charging_method,
                charging_time,
                "Type-C",  # 充电接口类型
                "5000 mAh",  # 电池容量
                notes
            ])
        
        # 在图表下方添加表格
        table = self.ax.table(
            cellText=table_data,
            cellLoc='center',
            loc='bottom',
            bbox=[0.0, -0.6, 1.0, 0.5]
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)  # 调整表格大小
    
    def visualize_charging(self, uavs, agvs=None, charging_stations=None, tasks=None):
        """可视化充电策略执行情况
        
        Args:
            uavs: 无人机列表
            agvs: AGV列表（可选）
            charging_stations: 固定充电站列表（可选）
            tasks: 任务列表（可选）
        """
        if not self.enable_visualization:
            return
        
        # 清空当前图
        self.ax.clear()
        
        # 设置坐标轴
        self.ax.set_xlim(0, 500)
        self.ax.set_ylim(0, 500)
        self.ax.set_xlabel('X Position')
        self.ax.set_ylabel('Y Position')
        self.ax.set_title('UAV Charging Strategy Visualization')
        self.ax.grid(True)
        
        # 绘制固定充电站
        if charging_stations:
            for station in charging_stations:
                color = 'g' if station.available else 'r'
                self.ax.plot(station.position[0], station.position[1], f'{color}s', markersize=12, label='Charging Station')
                # 标注充电站ID
                self.ax.text(station.position[0], station.position[1] + 5, f'Station {station.id}', 
                            fontsize=8, ha='center', va='bottom')
        
        # 绘制AGV
        if agvs:
            for agv in agvs:
                color = 'c' if agv.status == 'idle' else 'm' if agv.status == 'charging' else 'y'
                self.ax.plot(agv.position[0], agv.position[1], f'{color}d', markersize=10, label='AGV')
                # 标注AGV ID和状态
                self.ax.text(agv.position[0], agv.position[1] + 5, 
                            f'AGV {agv.id}\nStatus: {agv.status}', 
                            fontsize=8, ha='center', va='bottom')
        
        # 绘制任务
        if tasks:
            for task in tasks:
                if hasattr(task, 'status'):
                    # Task对象
                    status = task.status
                    start = task.start_point
                    end = task.end_point
                else:
                    # 字典任务
                    status = task['status']
                    start = task['start']
                    end = task['end']
                
                color = 'y' if status == 'pending' else 'c' if status == 'in_progress' else 'g'
                
                # 绘制任务起点和终点
                self.ax.plot(start[0], start[1], f'{color}o', markersize=6, label='Task Start')
                self.ax.plot(end[0], end[1], f'{color}x', markersize=6, label='Task End')
                # 绘制任务路径
                self.ax.plot([start[0], end[0]], [start[1], end[1]], f'{color}--', linewidth=1, label='Task Path')
        
        # 绘制无人机
        for uav in uavs:
            # 根据电量选择颜色
            if uav.battery > 70:
                color = 'g'
            elif uav.battery > 30:
                color = 'y'
            else:
                color = 'r'
            
            self.ax.plot(uav.position[0], uav.position[1], f'{color}^', markersize=12, label='UAV')
            
            # 标注无人机ID和电量
            battery_text = f'UAV {uav.id}\nBattery: {uav.battery}%'
            if uav.task:
                if hasattr(uav.task, 'id'):
                    battery_text += f'\nTask: {uav.task.id}'
                else:
                    battery_text += f'\nTask: {uav.task["id"]}'
            
            self.ax.text(uav.position[0], uav.position[1] + 5, battery_text, 
                        fontsize=9, ha='center', va='bottom', 
                        bbox=dict(facecolor='white', alpha=0.7, boxstyle='round'))
            
            # 绘制无人机路径
            if hasattr(uav, 'path_history') and uav.path_history and len(uav.path_history) > 1:
                path_x = [point[0] for point in uav.path_history]
                path_y = [point[1] for point in uav.path_history]
                self.ax.plot(path_x, path_y, 'b--', linewidth=1, label='UAV Path')
            elif uav.path and len(uav.path) > 1:
                path_x = [point[0] for point in uav.path]
                path_y = [point[1] for point in uav.path]
                self.ax.plot(path_x, path_y, 'b--', linewidth=1, label='UAV Path')
        
        # 显示图例（避免重复标签）
        handles, labels = self.ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        self.ax.legend(by_label.values(), by_label.keys(), loc='upper right')
        
        # 显示无人机充电信息表格
        if charging_stations and agvs:
            self._display_charging_info(uavs, charging_stations, agvs)
        
        # 更新显示
        plt.tight_layout()
        plt.draw()
        plt.pause(0.5)  # 暂停以便观察
    
    def fixed_charging(self, uavs, charging_stations, agvs=None, tasks=None, target_uav=None):
        """固定充电策略
        
        Args:
            uavs: 所有无人机列表（用于可视化）
            charging_stations: 固定充电站列表
            agvs: AGV列表（可选，用于可视化）
            tasks: 任务列表（可选，用于可视化）
            target_uav: 目标无人机（可选，仅为该无人机执行充电）
        """
        # 确定需要处理的无人机列表
        if target_uav:
            process_uavs = [target_uav]
        else:
            process_uavs = [uav for uav in uavs if uav.needs_charging()]
            
        for uav in process_uavs:
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
                
                # 可视化
                self.visualize_charging(uavs, agvs, charging_stations, tasks)
                
                # 充电直到电量充足
                while uav.needs_charging():
                    nearest_station.charge_uav(uav)
                    # 可视化每一次充电
                    self.visualize_charging(uavs, agvs, charging_stations, tasks)
                    time.sleep(0.3)  # 暂停以观察充电过程
                
                print(f"UAV {uav.id} 充电完成，当前电量: {uav.battery}%")
                # 可视化最终状态
                self.visualize_charging(uavs, agvs, charging_stations, tasks)
        
        
    
    def mobile_charging(self, uavs, agvs, charging_stations=None, tasks=None, target_uav=None):
        """移动充电策略
        
        Args:
            uavs: 所有无人机列表（用于可视化）
            agvs: AGV列表
            charging_stations: 固定充电站列表（可选，用于可视化）
            tasks: 任务列表（可选，用于可视化）
            target_uav: 目标无人机（可选，仅为该无人机执行充电）
        """
        # 确定需要处理的无人机列表
        if target_uav:
            process_uavs = [target_uav]
        else:
            process_uavs = [uav for uav in uavs if uav.needs_charging()]
            
        for uav in process_uavs:
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
                
                # 可视化AGV到达无人机位置
                self.visualize_charging(uavs, agvs, charging_stations, tasks)
                time.sleep(0.5)
                
                # 充电直到电量充足
                while uav.needs_charging():
                    nearest_agv.charge(uav)
                    # 可视化每一次充电
                    self.visualize_charging(uavs, agvs, charging_stations, tasks)
                    time.sleep(0.3)  # 暂停以观察充电过程
                
                nearest_agv.status = "idle"
                print(f"UAV {uav.id} 移动充电完成，当前电量: {uav.battery}%")
                # 可视化最终状态
                self.visualize_charging(uavs, agvs, charging_stations, tasks)
        
        
    
    def predictive_charging(self, uavs, agvs, tasks, charging_stations=None):
        """预测性充电策略
        
        Args:
            uavs: 无人机列表
            agvs: AGV列表
            tasks: 任务列表
            charging_stations: 固定充电站列表（可选）
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
                
                # 可视化当前状态
                self.visualize_charging(uavs, agvs, charging_stations, tasks)
                time.sleep(0.5)
                
                # 如果预计电量不足，提前安排充电
                if estimated_battery_after_tasks < 20:
                    print(f"预测UAV {uav.id} 电量不足，提前安排充电")
                    
                    # 优先使用移动充电，因为它更灵活
                    available_agvs = [agv for agv in agvs if agv.status == "idle"]
                    if available_agvs:
                        nearest_agv = min(available_agvs, 
                                        key=lambda a: calculate_distance(uav.position, a.position))
                        
                        self.charge(uav, nearest_agv, uavs, agvs, charging_stations, tasks)
                else:
                    print(f"没有可用的AGV，UAV {uav.id} 将继续执行任务")
        
        
    
    def charge(self, uav, agv, uavs, agvs, charging_stations=None, tasks=None):
        """执行充电
        
        Args:
            uav: 当前需要充电的无人机对象
            agv: 用于充电的AGV对象
            uavs: 所有无人机列表（用于完整可视化）
            agvs: 所有AGV列表（用于完整可视化）
            charging_stations: 固定充电站列表（可选）
            tasks: 任务列表（可选）
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
                # 可视化充电过程 - 使用完整列表显示所有元素
                self.visualize_charging(uavs, agvs, charging_stations, tasks)
                time.sleep(0.3)
        elif self.mode == "smart":
            print(f"使用智能充电策略为 UAV {uav.id} 充电")
            # 智能充电可以根据情况选择固定或移动充电
            # 这里简单实现为电量低于10%时使用移动充电，否则使用固定充电
            if uav.battery < 10:
                self.mode = "mobile"
            else:
                self.mode = "fixed"
            self.charge(uav, agv, uavs, agvs, charging_stations, tasks)
        else:
            print(f"使用默认充电策略为 UAV {uav.id} 充电")
            # 默认使用移动充电
            while uav.needs_charging():
                agv.charge(uav)
                # 可视化充电过程 - 使用完整列表显示所有元素
                self.visualize_charging(uavs, agvs, charging_stations, tasks)
                time.sleep(0.3)
        
        print(f"UAV {uav.id} 充电完成，当前电量: {uav.battery}%")
    
    def decide_charging_method(self, uav, charging_stations, agvs):
        """决定充电方法（固定或移动）
        
        Args:
            uav: 无人机对象
            charging_stations: 固定充电站列表
            agvs: AGV列表
            
        Returns:
            str: 充电方法，"fixed"或"mobile"
        """
        # 计算到最近固定充电站的距离
        available_stations = [station for station in charging_stations if station.available]
        if not available_stations:
            return "mobile"  # 没有固定充电站可用，只能使用移动充电
        
        nearest_station = min(available_stations, 
                            key=lambda s: calculate_distance(uav.position, s.position))
        distance_to_station = calculate_distance(uav.position, nearest_station.position)
        
        # 计算到最近空闲AGV的距离
        available_agvs = [agv for agv in agvs if agv.status == "idle"]
        if not available_agvs:
            return "fixed"  # 没有AGV可用，只能使用固定充电
        
        nearest_agv = min(available_agvs, 
                        key=lambda a: calculate_distance(uav.position, a.position))
        distance_to_agv = calculate_distance(uav.position, nearest_agv.position)
        
        # 计算充电时间和移动时间
        # 假设UAV飞行速度为5单位/秒，AGV移动速度为2单位/秒
        uav_speed = 5
        agv_speed = 2
        
        # UAV飞往固定充电站的时间
        uav_flight_time = distance_to_station / uav_speed
        
        # AGV飞往UAV的时间
        agv_travel_time = distance_to_agv / agv_speed
        
        # 充电时间（假设固定充电站充电速度更快）
        # 固定充电：30%电量/秒，移动充电：10%电量/秒
        charge_needed = 100 - uav.battery
        fixed_charge_time = charge_needed / 30
        mobile_charge_time = charge_needed / 10
        
        # 总时间计算
        total_fixed_time = uav_flight_time + fixed_charge_time
        total_mobile_time = agv_travel_time + mobile_charge_time
        
        # 考虑电量紧急情况：如果电量低于15%，优先使用移动充电
        if uav.battery < 15:
            return "mobile"
        
        # 否则选择总时间更短的充电方式
        if total_fixed_time < total_mobile_time:
            return "fixed"
        else:
            return "mobile"
    
    def smart_charging(self, uavs, charging_stations, agvs, tasks=None):
        """智能充电策略，自动选择固定或移动充电
        
        Args:
            uavs: 无人机列表
            charging_stations: 固定充电站列表
            agvs: AGV列表
            tasks: 任务列表（可选，用于可视化）
        """
        for uav in uavs:
            if uav.needs_charging():
                # 决定使用哪种充电方式
                charging_method = self.decide_charging_method(uav, charging_stations, agvs)
                
                print(f"UAV {uav.id} 电量: {uav.battery}%，选择 {charging_method} 充电")
                
                if charging_method == "fixed":
                    # 使用固定充电 - 传递完整列表以便显示所有元素，并指定目标无人机
                    self.fixed_charging(uavs, charging_stations, agvs, tasks, target_uav=uav)
                else:
                    # 使用移动充电 - 传递完整列表以便显示所有元素，并指定目标无人机
                    self.mobile_charging(uavs, agvs, charging_stations, tasks, target_uav=uav)
        
        # 保持可视化窗口打开
        if self.enable_visualization:
            plt.ioff()  # 关闭交互式模式
            plt.show()  # 保持窗口打开，直到用户手动关闭