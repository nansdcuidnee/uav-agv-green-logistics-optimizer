#!/usr/bin/env python3
"""Run demo script for competition."""

import sys
import argparse
import os
import yaml

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.utils.simulator_helper import build_environment, build_simulator

def deep_merge(base, override):
    """深合并两个字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def load_config(config_path, visited=None):
    """加载场景配置文件，支持继承"""
    if visited is None:
        visited = set()
    
    # 检测循环继承
    if config_path in visited:
        raise ValueError(f"循环继承 detected: {config_path}")
    visited.add(config_path)
    
    # 加载当前配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 处理继承
    if 'extends' in config:
        extends_path = config['extends']
        # 构建继承文件的完整路径
        extends_full_path = os.path.join(os.path.dirname(config_path), extends_path)
        # 递归加载父配置
        parent_config = load_config(extends_full_path, visited.copy())
        # 深合并配置（子配置覆盖父配置）
        config = deep_merge(parent_config, config)
        # 移除 extends 字段
        del config['extends']
    
    return config

def main():
    """Run demo simulation."""
    parser = argparse.ArgumentParser(description="Run demo simulation for competition")
    parser.add_argument("--config", type=str, default="configs/demo.yaml", help="Configuration file path")
    parser.add_argument("--max-steps", type=int, help="Maximum number of steps")
    parser.add_argument("--experiment-name", type=str, help="Experiment name")
    
    args = parser.parse_args()
    
    config_file = args.config
    
    if os.path.exists(config_file):
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
        max_steps = config.get('max_steps', 100)
        
        # Run simulation
        output_dir = simulator.run(
            max_steps=max_steps,
            experiment_name=experiment_name,
            result_type="runs"
        )
        
        print(f"Demo simulation completed. Results saved to: {output_dir}")
    else:
        print(f"配置文件不存在: {config_file}")

if __name__ == "__main__":
    main()
