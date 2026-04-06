#!/usr/bin/env python3
"""
集成检查脚本

用于验证整个系统的集成功能，包括策略切换和基本功能验证
"""

import argparse
import random
import sys
from pathlib import Path


from src.simulation.environment import Environment
from src.core.uav import UAV
from src.core.agv import AGV
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.simulation.simulator import Simulator


def run_self_check(strategy_type, seed):
    """运行集成检查
    
    Args:
        strategy_type: 策略类型
        seed: 随机种子
    """
    # 设置随机种子
    random.seed(seed)
    
    print(f"开始集成检查: 策略={strategy_type}, 种子={seed}")
    
    # 创建环境
    environment = Environment()
    
    # 添加 UAV 和 AGV
    uav1 = UAV(id=1, position=(0, 0))
    uav2 = UAV(id=2, position=(100, 100))
    agv1 = AGV(id=1, position=(50, 50))
    agv2 = AGV(id=2, position=(150, 150))
    environment.uavs = [uav1, uav2]
    environment.agvs = [agv1, agv2]
    
    # 生成任务
    environment.generate_tasks(3, seed=seed)
    print(f"生成了 {len(environment.tasks)} 个任务")
    
    # 初始化模拟器
    energy_model = EnergyModel()
    path_planner = PathPlanner()
    scheduler = Scheduler()
    
    simulator = Simulator(
        environment=environment,
        energy_model=energy_model,
        path_planner=path_planner,
        scheduler=scheduler,
        strategy_type=strategy_type
    )
    
    # 运行模拟
    max_steps = 100
    output_dir = simulator.run(max_steps=max_steps, experiment_name=f"self_check_{strategy_type}")
    
    # 验证结果
    metrics = simulator.calculate_metrics()
    print("\n集成检查结果:")
    print(f"总能耗: {metrics['total_energy']}")
    print(f"任务完成率: {metrics['task_completion_rate']:.2f}%")
    print(f"完成任务数: {metrics['completed_tasks']}/{len(environment.tasks)}")
    print(f"充电次数: {metrics['charging_count']}")
    print(f"结果保存到: {output_dir}")
    
    # 验证关键指标
    assert metrics['completed_tasks'] > 0, "没有完成任何任务"
    assert metrics['total_energy'] > 0, "总能耗为 0"
    
    print("\n集成检查通过！")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="集成检查脚本")
    parser.add_argument("--strategy", type=str, default="baseline_direct",
                        choices=["baseline_direct", "relay_coop", "energy_priority"],
                        help="策略类型")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    args = parser.parse_args()
    
    try:
        run_self_check(args.strategy, args.seed)
        return 0
    except Exception as e:
        print(f"集成检查失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())