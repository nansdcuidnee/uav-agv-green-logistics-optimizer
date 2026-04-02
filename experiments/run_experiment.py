import random
from src.core.uav import UAV
from src.core.agv import AGV
<<<<<<< HEAD
from src.core.task import Task
=======
>>>>>>> dev
from src.simulation.environment import Environment
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.simulation.simulator import Simulator
from src.visualization.visualizer import Visualizer
from config.config import MAP_SIZE, UAV_MAX_BATTERY, AGV_MAX_BATTERY


def run_experiment(experiment_name, num_uavs=2, num_agvs=2, num_tasks=3, max_steps=50):
    """运行实验
    
    Args:
        experiment_name: 实验名称
        num_uavs: 无人机数量
        num_agvs: AGV数量
        num_tasks: 任务数量
        max_steps: 最大模拟步数
    """
    print(f"Running experiment: {experiment_name}")
    print(f"UAVs: {num_uavs}, AGVs: {num_agvs}, Tasks: {num_tasks}")
    
    # 1. 创建环境
    environment = Environment(map_size=MAP_SIZE)
    
    # 2. 创建无人机
    for i in range(num_uavs):
        # 随机初始位置
        from src.utils.math_utils import generate_random_point
        position = generate_random_point(MAP_SIZE)
<<<<<<< HEAD
        uavs.append(UAV(i+1, position))
=======
<<<<<<< HEAD
        uav = UAV(i+1, position)
        uav.battery = UAV_MAX_BATTERY  # 设置初始电量
        environment.uavs.append(uav)
=======
        uavs.append(UAV(i+1, position, UAV_MAX_BATTERY))
>>>>>>> origin/dev
>>>>>>> dev
    
    # 3. 创建AGV
    for i in range(num_agvs):
        # 随机初始位置
        from src.utils.math_utils import generate_random_point
        position = generate_random_point(MAP_SIZE)
<<<<<<< HEAD
        agvs.append(AGV(i+1, position))
=======
<<<<<<< HEAD
        agv = AGV(i+1, position)
        environment.agvs.append(agv)
=======
        agvs.append(AGV(i+1, position, AGV_MAX_BATTERY))
>>>>>>> origin/dev
>>>>>>> dev
    
    # 4. 生成任务
    environment.generate_tasks(num_tasks)
    
    # 5. 初始化各个模块
    energy_model = EnergyModel()
    path_planner = PathPlanner()
    scheduler = Scheduler()
<<<<<<< HEAD
    charging_strategy = ChargingStrategy(enable_visualization=True)
=======
    strategy_type = "baseline_direct"  # 可选值："baseline_direct", "relay_coop", "energy_priority"
>>>>>>> dev
    visualizer = Visualizer()
    
    # 为每个UAV初始化路径
    for uav in environment.uavs:
        uav.path = path_planner.plan(environment.delivery_points)
    
    # 将UAVs、AGVs和Tasks添加到环境中
    environment.uavs = uavs
    environment.agvs = agvs
    environment.tasks = tasks
    
    # 6. 创建模拟器
    simulator = Simulator(
        environment,
        energy_model,
        path_planner,
        scheduler,
<<<<<<< HEAD
        charging_strategy
=======
        strategy_type=strategy_type
>>>>>>> dev
    )
    
    # 7. 运行模拟
    output_dir = simulator.run(max_steps=max_steps, experiment_name=experiment_name)
    
    # 8. 显示最终结果
    visualizer.show()
    
    print(f"Experiment {experiment_name} completed")
    print(f"实验结果保存在: {output_dir}")


if __name__ == "__main__":
    # 运行默认实验
    run_experiment("Default Experiment")
    
    # 可以添加更多实验配置
    # run_experiment("High Task Load", num_tasks=5)
    # run_experiment("Limited AGV", num_agvs=1)