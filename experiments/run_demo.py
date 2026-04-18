#!/usr/bin/env python3
"""Run demo script for competition."""

import sys
import argparse
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from config.config_loader import load_config
from config.config import DEFAULT_SIMULATION_STEPS, MAX_SIMULATION_STEPS, RANDOM_SEED
from src.utils.simulator_helper import build_environment, build_simulator

def main():
    """Run demo simulation."""
    parser = argparse.ArgumentParser(description="Run demo simulation for competition")
    parser.add_argument("--config", type=str, default="configs/explicit/demo.yaml", help="Configuration file path")
    parser.add_argument("--max-steps", type=int, help="Maximum number of steps")
    parser.add_argument("--experiment-name", type=str, help="Experiment name")
    
    args = parser.parse_args()
    
    config_file = args.config
    
    print(f"运行场景: {config_file}")
    # 加载配置
    config = load_config(config_file)
    
    # 命令行参数覆盖配置
    if args.max_steps is not None:
        config['max_steps'] = args.max_steps
    
    # 构建环境
    env = build_environment(config)
    
    # 确定策略类型
    strategy_type = config.get('strategy', 'baseline_direct')
    
    # 构建仿真器
    simulator = build_simulator(env, strategy_type)
    
    # 确定实验名称
    if args.experiment_name:
        experiment_name = args.experiment_name
    elif 'experiment_name' in config:
        experiment_name = config['experiment_name']
    else:
        # 从配置文件名推导实验名称
        experiment_name = os.path.splitext(os.path.basename(config_file))[0]
    
    # 确定最大步数
    max_steps = config.get('max_steps', DEFAULT_SIMULATION_STEPS)
    # 裁剪max_steps到最大限制
    max_steps = min(max_steps, MAX_SIMULATION_STEPS)
    
    # Run simulation
    output_dir = simulator.run(
        max_steps=max_steps,
        experiment_name=experiment_name,
        result_type="runs"
    )
    
    print(f"Demo simulation completed. Results saved to: {output_dir}")

if __name__ == "__main__":
    main()
