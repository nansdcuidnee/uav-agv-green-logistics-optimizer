from src.simulation.environment import Environment
from src.core.uav import UAV
from src.core.agv import AGV
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.strategy.charging_strategy import ChargingStrategy
from src.simulation.simulator import Simulator


def main():
    """主函数，运行整个仿真系统"""
    # 1. 创建环境
    environment = Environment()
    
    # 2. 创建 UAV
    num_uavs = 2
    for i in range(num_uavs):
        # UAV初始位置设置在地图中心附近
        position = (500, 500)
        uav = UAV(i + 1, position)
        environment.uavs.append(uav)
    
    # 3. 创建 AGV
    num_agvs = 1
    for i in range(num_agvs):
        # AGV初始位置设置在地图中心
        position = (500, 500)
        agv = AGV(i + 1, position)
        environment.agvs.append(agv)
    
    # 4. 生成任务
    num_tasks = 5
    environment.generate_tasks(num_tasks)
    print(f"生成了 {num_tasks} 个任务")
    
    # 5. 初始化能耗模型
    energy_model = EnergyModel()
    
    # 6. 初始化路径规划
    path_planner = PathPlanner()
    
    # 7. 初始化调度器
    scheduler = Scheduler()
    
    # 8. 初始化充电策略
    charging_strategy = ChargingStrategy(mode="mobile")
    
    # 9. 创建 Simulator
    simulator = Simulator(
        environment,
        energy_model,
        path_planner,
        scheduler,
        charging_strategy
    )
    
    # 10. 运行仿真
    max_steps = 500
    simulator.run(max_steps=max_steps)


if __name__ == "__main__":
    main()