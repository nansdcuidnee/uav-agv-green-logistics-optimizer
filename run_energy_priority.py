#!/usr/bin/env python3
"""
运行 energy_priority 策略的脚本
"""

from src.simulation.environment import Environment
from src.simulation.simulator import Simulator
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler


def main():
    """运行 energy_priority 策略"""
    print("=== 运行 energy_priority 策略 ===")
    
    # 创建环境
    env = Environment(map_size=(1000, 1000))
    
    # 添加UAV和AGV
    from src.core.uav import UAV
    from src.core.agv import AGV
    
    # 添加2个UAV
    uav1 = UAV(1, (100, 100))
    uav1.battery = 200.0
    uav2 = UAV(2, (200, 200))
    uav2.battery = 200.0
    env.uavs.extend([uav1, uav2])
    
    # 添加2个AGV
    agv1 = AGV(1, (300, 300))
    agv2 = AGV(2, (400, 400))
    env.agvs.extend([agv1, agv2])
    
    # 生成5个任务
    env.generate_tasks(5, seed=42)
    
    # 创建仿真器，指定策略
    simulator = Simulator(
        environment=env,
        energy_model=EnergyModel(),
        path_planner=PathPlanner(),
        scheduler=Scheduler(),
        strategy_type="energy_priority"  # 指定策略
    )
    
    # 运行仿真
    output_dir = simulator.run(max_steps=200, experiment_name="energy_priority", result_type="runs")
    print(f"结果保存到: {output_dir}")


if __name__ == "__main__":
    main()
