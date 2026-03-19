from src.core.uav import UAV
from src.core.agv import AGV
from src.core.task import Task
from src.core.environment import Environment
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.strategy.charging_strategy import ChargingStrategy
from src.simulation.simulator import Simulator
from src.visualization.visualizer import Visualizer
from config.config import MAP_SIZE, UAV_MAX_BATTERY, AGV_MAX_BATTERY


def main():
    """主函数，展示系统使用示例"""
    # 1. 创建环境
    environment = Environment(map_size=MAP_SIZE)
    
    # 添加配送点
    delivery_points = [(50, 50), (100, 100), (150, 50), (50, 150), (150, 150)]
    for point in delivery_points:
        environment.add_delivery_point(point)
    
    # 2. 创建无人机
    uavs = [
        UAV(1, (0, 0), battery=40),
        UAV(2, (200, 200), battery=40)
    ]
    
    # 3. 创建AGV
    agvs = [
        AGV(1, (100, 0), battery=AGV_MAX_BATTERY),
        AGV(2, (0, 100), battery=AGV_MAX_BATTERY)
    ]
    
    # 4. 创建任务
    tasks = [
        Task(1, (0, 0), (100, 100), payload=2, priority=1),
        Task(2, (200, 200), (50, 50), payload=1, priority=2),
        Task(3, (100, 0), (150, 150), payload=3, priority=1)
    ]
    
    # 5. 初始化各个模块
    energy_model = EnergyModel()
    path_planner = PathPlanner()
    scheduler = Scheduler()
    charging_strategy = ChargingStrategy()
    visualizer = Visualizer()
    
    # 为每个UAV初始化路径
    for uav in uavs:
        uav.path = path_planner.plan(environment.delivery_points)
    
    # 6. 创建模拟器
    simulator = Simulator(
        environment,
        uavs,
        agvs,
        tasks,
        scheduler,
        charging_strategy,
        energy_model,
        path_planner
    )
    
    # 7. 运行模拟
    for i in range(50):  # 运行50个时间步
        simulator.step()
        # 可视化当前状态
        visualizer.plot_system(environment, uavs, agvs, tasks)
    
    # 8. 显示最终结果
    visualizer.show()


if __name__ == "__main__":
    main()