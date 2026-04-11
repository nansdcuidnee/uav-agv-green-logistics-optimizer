#!/usr/bin/env python3
"""Compare different strategies."""

import sys
import argparse
import csv
import json
import matplotlib.pyplot as plt
import os
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.utils.simulator_helper import build_environment, build_simulator
from src.utils.result_layout import create_comparison_layout

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
    """Compare different strategies."""
    parser = argparse.ArgumentParser(description="Compare different strategies")
    parser.add_argument("--config", type=str, default="configs/qualification.yaml", help="Configuration file path")
    parser.add_argument("--max-steps", type=int, help="Maximum number of steps")
    parser.add_argument("--compare-name", type=str, default="strategy_comparison", help="Comparison name")
    
    args = parser.parse_args()
    
    config_file = args.config
    
    if not os.path.exists(config_file):
        print(f"配置文件不存在: {config_file}")
        return
    
    # 加载配置
    config = load_config(config_file)
    
    # 命令行参数覆盖配置
    if args.max_steps is not None:
        config['max_steps'] = args.max_steps
    
    # Create comparison layout
    layout = create_comparison_layout(compare_name=args.compare_name)
    
    # Strategies to compare
    strategies = ["baseline_direct", "relay_coop", "energy_priority"]
    results = []
    
    for strategy_type in strategies:
        print(f"Running strategy: {strategy_type}")
        
        # 构建环境
        env = build_environment(config)
        
        # 构建仿真器
        simulator = build_simulator(env, strategy_type)
        
        # 确定最大步数
        max_steps = config.get('max_steps', 100)
        
        # Run simulation
        output_dir = simulator.run(
            max_steps=max_steps,
            experiment_name=f"{strategy_type}",
            result_type="runs"
        )
        
        # Load metrics
        metrics_file = Path(output_dir) / "metrics.json"
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        
        results.append({
            "strategy": strategy_type,
            "total_energy": metrics.get("total_energy", 0),
            "task_completion_rate": metrics.get("task_completion_rate", 0),
            "total_time": metrics.get("total_time", 0),
            "charging_count": metrics.get("charging_count", 0)
        })
    
    # Save comparison metrics
    comparison_metrics_file = layout.artifact_path("comparison_metrics.csv")
    with open(comparison_metrics_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy", "total_energy", "task_completion_rate", "total_time", "charging_count"])
        for result in results:
            writer.writerow([
                result["strategy"],
                result["total_energy"],
                result["task_completion_rate"],
                result["total_time"],
                result["charging_count"]
            ])
    
    # Generate strategy compare plot
    plt.figure(figsize=(10, 6))
    strategies = [r["strategy"] for r in results]
    total_energy = [r["total_energy"] for r in results]
    plt.bar(strategies, total_energy)
    plt.xlabel("Strategy")
    plt.ylabel("Total Energy")
    plt.title("Energy Consumption by Strategy")
    plt.savefig(layout.plot_path("strategy_compare.png"))
    plt.close()
    
    # Generate completion compare plot
    plt.figure(figsize=(10, 6))
    task_completion_rate = [r["task_completion_rate"] for r in results]
    plt.bar(strategies, task_completion_rate)
    plt.xlabel("Strategy")
    plt.ylabel("Task Completion Rate (%)")
    plt.title("Task Completion Rate by Strategy")
    plt.savefig(layout.plot_path("completion_compare.png"))
    plt.close()
    
    # Save comparison summary
    comparison_summary_file = layout.artifact_path("comparison_summary.txt")
    with open(comparison_summary_file, "w", encoding="utf-8") as f:
        f.write("Strategy Comparison Summary\n")
        f.write("============================\n")
        for result in results:
            f.write(f"Strategy: {result['strategy']}\n")
            f.write(f"  Total Energy: {result['total_energy']}\n")
            f.write(f"  Task Completion Rate: {result['task_completion_rate']}%\n")
            f.write(f"  Total Time: {result['total_time']} steps\n")
            f.write(f"  Charging Count: {result['charging_count']}\n")
            f.write("\n")
    
    print(f"Strategy comparison completed. Results saved to: {layout.run_dir}")

if __name__ == "__main__":
    main()
