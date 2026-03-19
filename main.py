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
from src.utils.math_utils import generate_random_point
from config.config import *


def generate_points(num_points):
    """生成指定数量的配送点
    
    Args:
        num_points: 配送点数量
        
    Returns:
        list: 配送点列表
    """
    points = []
    for _ in range(num_points):
        point = generate_random_point(MAP_SIZE)
        points.append(point)
    return points


def run_simulation(config):
    """运行模拟
    
    Args:
        config: 配置字典，包含模式等参数
        
    Returns:
        dict: 模拟结果，包含总能耗、总时间等
    """
    mode = config.get('mode', 'mobile')
    
    # 1. 创建环境
    environment = Environment(map_size=MAP_SIZE)
    
    # 添加配送点
    delivery_points = generate_points(NUM_POINTS)
    for point in delivery_points:
        environment.add_delivery_point(point)
    
    # 2. 创建无人机
    uavs = []
    for i in range(NUM_UAV):
        uav = UAV(i+1, (0, 0), battery=INIT_BATTERY)
        uavs.append(uav)
    
    # 3. 创建AGV
    agvs = []
    for i in range(NUM_AGV):
        agv = AGV(i+1, (100, 0), battery=AGV_MAX_BATTERY)
        agvs.append(agv)
    
    # 4. 创建任务
    tasks = []
    for i in range(NUM_POINTS):
        if i < len(delivery_points) - 1:
            start_point = delivery_points[i]
            end_point = delivery_points[i+1]
            task = Task(i+1, start_point, end_point, payload=1, priority=1)
            tasks.append(task)
    
    # 5. 初始化各个模块
    energy_model = EnergyModel()
    path_planner = PathPlanner()
    scheduler = Scheduler()
    charging_strategy = ChargingStrategy(mode=mode)
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
    total_energy = 0
    start_time = 0  # 可以使用实际时间
    
    for i in range(SIMULATION_STEPS):
        energy = simulator.step()
        total_energy += energy
        # 可视化当前状态
        visualizer.plot_system(environment, uavs, agvs, tasks)
    
    end_time = SIMULATION_STEPS  # 简化处理，使用模拟步数作为时间
    
    # 8. 显示最终结果
    visualizer.show()
    
    # 9. 返回结果
    results = {
        'mode': mode,
        'total_energy': total_energy,
        'total_time': end_time - start_time,
        'num_uavs': NUM_UAV,
        'num_agvs': NUM_AGV,
        'num_points': NUM_POINTS
    }
    
    return results


def run_experiment():
    """运行实验，测试不同充电策略"""
    modes = ["fixed", "mobile", "smart"]
    results = []
    
    for mode in modes:
        print(f"\n=== 运行 {mode} 模式实验 ===")
        config = {'mode': mode}
        result = run_simulation(config)
        results.append(result)
        print(f"{mode} 模式结果: 总能耗={result['total_energy']}, 总时间={result['total_time']}")
    
    # 打印对比结果
    print("\n=== 实验结果对比 ===")
    for result in results:
        print(f"{result['mode']}: 总能耗={result['total_energy']}, 总时间={result['total_time']}")
    
    return results


def main():
    """主函数"""
    print("开始运行实验...")
    results = run_experiment()
    print("实验完成！")


if __name__ == "__main__":
    main()