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
    uavs = []
    for i in range(num_uavs):
        # 随机初始位置
        from src.utils.math_utils import generate_random_point
        position = generate_random_point(MAP_SIZE)
        uavs.append(UAV(i+1, position, battery=UAV_MAX_BATTERY))
    
    # 3. 创建AGV
    agvs = []
    for i in range(num_agvs):
        # 随机初始位置
        from src.utils.math_utils import generate_random_point
        position = generate_random_point(MAP_SIZE)
        agvs.append(AGV(i+1, position, battery=AGV_MAX_BATTERY))
    
    # 4. 创建任务
    tasks = []
    for i in range(num_tasks):
        # 随机起点和终点
        from src.utils.math_utils import generate_random_point
        start_point = generate_random_point(MAP_SIZE)
        end_point = generate_random_point(MAP_SIZE)
        tasks.append(Task(i+1, start_point, end_point, payload=1, priority=1))
    
    # 5. 初始化各个模块
    energy_model = EnergyModel()
    path_planner = PathPlanner()
    scheduler = Scheduler()
    charging_strategy = ChargingStrategy()
    visualizer = Visualizer()
    
    # 6. 创建模拟器
    simulator = Simulator(environment, uavs, agvs, tasks, scheduler, charging_strategy)
    
    # 7. 运行模拟
    for i in range(max_steps):
        simulator.step()
        # 可视化当前状态
        visualizer.plot_system(environment, uavs, agvs, tasks)
    
    # 8. 显示最终结果
    visualizer.show()
    
    print(f"Experiment {experiment_name} completed")


if __name__ == "__main__":
    # 运行默认实验
    run_experiment("Default Experiment")
    
    # 可以添加更多实验配置
    # run_experiment("High Task Load", num_tasks=5)
    # run_experiment("Limited AGV", num_agvs=1)