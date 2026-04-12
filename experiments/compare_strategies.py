#!/usr/bin/env python3
"""Compare different strategies."""

import argparse
import csv
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import yaml
from pathlib import Path

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

def compute_relative_metrics(strategy_metrics, baseline_metrics):
    """计算相对指标
    
    Args:
        strategy_metrics: 策略的指标
        baseline_metrics: 基准策略的指标
    
    Returns:
        dict: 包含相对指标的字典
    """
    result = {
        "energy_saving_rate_vs_baseline": None,
        "emission_reduction_rate_vs_baseline": None,
    }

    if not baseline_metrics:
        return result

    baseline_energy = baseline_metrics.get("total_energy")
    strategy_energy = strategy_metrics.get("total_energy")
    if baseline_energy is not None and baseline_energy > 0 and strategy_energy is not None:
        result["energy_saving_rate_vs_baseline"] = (
            (baseline_energy - strategy_energy) / baseline_energy * 100.0
        )

    baseline_carbon = baseline_metrics.get("carbon_emission")
    strategy_carbon = strategy_metrics.get("carbon_emission")
    if baseline_carbon is not None and baseline_carbon > 0 and strategy_carbon is not None:
        result["emission_reduction_rate_vs_baseline"] = (
            (baseline_carbon - strategy_carbon) / baseline_carbon * 100.0
        )

    return result
    
    # 计算节能率
    if baseline_metrics and baseline_metrics.get('total_energy', 0) > 0:
        energy_saving_rate = ((baseline_metrics['total_energy'] - strategy_metrics.get('total_energy', 0)) / 
                            baseline_metrics['total_energy']) * 100
    else:
        energy_saving_rate = None
    
    # 计算减排率
    if baseline_metrics and baseline_metrics.get('carbon_emission', 0) > 0:
        emission_reduction_rate = ((baseline_metrics['carbon_emission'] - strategy_metrics.get('carbon_emission', 0)) / 
                                baseline_metrics['carbon_emission']) * 100
    else:
        emission_reduction_rate = None
    
    result['energy_saving_rate_vs_baseline'] = energy_saving_rate
    result['emission_reduction_rate_vs_baseline'] = emission_reduction_rate
    
    return result

def main():
    """Compare different strategies."""
    parser = argparse.ArgumentParser(description="Compare different strategies")
    parser.add_argument("--config", type=str, default="configs/qualification.yaml", help="Configuration file path")
    parser.add_argument("--max-steps", type=int, help="Maximum number of steps")
    parser.add_argument("--compare-name", type=str, default="strategy_comparison", help="Comparison name")
    parser.add_argument("--baseline-strategy", type=str, default="baseline_direct", help="Baseline strategy name")
    
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
    detailed_results = []
    
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
        
        detailed_results.append({
            "strategy": strategy_type,
            "run_dir": output_dir,
            "metrics": metrics
        })
    
    # 确定baseline策略
    baseline_strategy = args.baseline_strategy
    baseline_result = next((r for r in detailed_results if r['strategy'] == baseline_strategy), None)
    baseline_metrics = baseline_result['metrics'] if baseline_result else None
    
    # 校验三策略 scenario_name 与 seed 一致
    scenario_name = None
    seed = None
    for result in detailed_results:
        metrics = result['metrics']
        if scenario_name is None:
            scenario_name = metrics.get('scenario_name')
            seed = metrics.get('seed')
        else:
            if metrics.get("scenario_name") != scenario_name:
                raise ValueError(
                    f"strategy {result['strategy']} scenario_name mismatch: "
                    f"{metrics.get('scenario_name')} != {scenario_name}"
                )
                print(f"错误：策略 {result['strategy']} 的 scenario_name 与其他策略不一致")
                return
            if metrics.get("seed") != seed:
                raise ValueError(
                    f"strategy {result['strategy']} seed mismatch: "
                    f"{metrics.get('seed')} != {seed}"
                )
                print(f"错误：策略 {result['strategy']} 的 seed 与其他策略不一致")
                return
    
    # 定义需要的9个核心指标
    core_metrics = [
        'completion_rate',
        'on_time_rate',
        'avg_delivery_time',
        'total_energy',
        'avg_energy_per_task',
        'energy_per_km',
        'total_distance_agv',
        'avg_wait_time_at_relay',
        'charging_count'
    ]
    
    # 检查所有策略是否包含所有核心指标
    for result in detailed_results:
        metrics = result['metrics']
        for metric in core_metrics:
            if metric not in metrics:
                raise ValueError(f"策略 {result['strategy']} 缺少核心指标 {metric}")
    
    # 计算相对指标并准备结果
    results = []
    strategy_run_dir_map = {}
    for result in detailed_results:
        # 计算相对指标
        relative_metrics = compute_relative_metrics(result['metrics'], baseline_metrics)
        
        # 构建包含所有9个核心指标的结果
        combined_metrics = {
            "strategy": result['strategy'],
            "run_dir": result['run_dir']
        }
        
        # 添加所有核心指标
        for metric in core_metrics:
            combined_metrics[metric] = result['metrics'][metric]
        
        # 添加相对指标
        combined_metrics.update(relative_metrics)
        
        results.append(combined_metrics)
        strategy_run_dir_map[result['strategy']] = result['run_dir']
    
    # Save comparison metrics
    comparison_metrics_file = layout.artifact_path("comparison_metrics.csv")
    with open(comparison_metrics_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # 写入表头，按要求的顺序
        writer.writerow(["strategy"] + core_metrics)
        for result in results:
            row = [result["strategy"]]
            for metric in core_metrics:
                row.append(result[metric])
            writer.writerow(row)
    
    # 生成9张核心对比图
    strategies = [r["strategy"] for r in results]
    
    # 1. completion_rate_compare.png
    plt.figure(figsize=(10, 6))
    completion_rate = [r["completion_rate"] * 100 for r in results]  # 转换为百分比
    plt.bar(strategies, completion_rate)
    plt.xlabel("Strategy")
    plt.ylabel("Completion Rate (%)")
    plt.title("Completion Rate by Strategy")
    plt.savefig(layout.plot_path("completion_rate_compare.png"))
    plt.close()
    
    # 2. on_time_rate_compare.png
    plt.figure(figsize=(10, 6))
    on_time_rate = [r["on_time_rate"] * 100 for r in results]  # 转换为百分比
    plt.bar(strategies, on_time_rate)
    plt.xlabel("Strategy")
    plt.ylabel("On Time Rate (%)")
    plt.title("On Time Rate by Strategy")
    plt.savefig(layout.plot_path("on_time_rate_compare.png"))
    plt.close()
    
    # 3. avg_delivery_time_compare.png
    plt.figure(figsize=(10, 6))
    avg_delivery_time = [r["avg_delivery_time"] for r in results]
    plt.bar(strategies, avg_delivery_time)
    plt.xlabel("Strategy")
    plt.ylabel("Average Delivery Time (steps)")
    plt.title("Average Delivery Time by Strategy")
    plt.savefig(layout.plot_path("avg_delivery_time_compare.png"))
    plt.close()
    
    # 4. total_energy_compare.png
    plt.figure(figsize=(10, 6))
    total_energy = [r["total_energy"] for r in results]
    plt.bar(strategies, total_energy)
    plt.xlabel("Strategy")
    plt.ylabel("Total Energy")
    plt.title("Total Energy by Strategy")
    plt.savefig(layout.plot_path("total_energy_compare.png"))
    plt.close()
    
    # 5. avg_energy_per_task_compare.png
    plt.figure(figsize=(10, 6))
    avg_energy_per_task = []
    all_none = True
    for r in results:
        value = r["avg_energy_per_task"]
        if value is not None:
            all_none = False
            avg_energy_per_task.append(value)
        else:
            avg_energy_per_task.append(np.nan)
    
    if all_none:
        raise ValueError("avg_energy_per_task is null for all strategies")
        print("错误：avg_energy_per_task 所有值都是 null，无法生成图表")
        return
    
    plt.bar(strategies, avg_energy_per_task)
    plt.xlabel("Strategy")
    plt.ylabel("Average Energy per Task")
    plt.title("Average Energy per Task by Strategy")
    plt.savefig(layout.plot_path("avg_energy_per_task_compare.png"))
    plt.close()
    
    # 6. energy_per_km_compare.png
    plt.figure(figsize=(10, 6))
    energy_per_km = []
    all_none = True
    for r in results:
        value = r["energy_per_km"]
        if value is not None:
            all_none = False
            energy_per_km.append(value)
        else:
            energy_per_km.append(np.nan)
    
    if all_none:
        raise ValueError("energy_per_km is null for all strategies")
        print("错误：energy_per_km 所有值都是 null，无法生成图表")
        return
    
    plt.bar(strategies, energy_per_km)
    plt.xlabel("Strategy")
    plt.ylabel("Energy per km")
    plt.title("Energy per km by Strategy")
    plt.savefig(layout.plot_path("energy_per_km_compare.png"))
    plt.close()
    
    # 7. total_distance_agv_compare.png
    plt.figure(figsize=(10, 6))
    total_distance_agv = [r["total_distance_agv"] for r in results]
    plt.bar(strategies, total_distance_agv)
    plt.xlabel("Strategy")
    plt.ylabel("Total Distance (AGV)")
    plt.title("Total Distance (AGV) by Strategy")
    plt.savefig(layout.plot_path("total_distance_agv_compare.png"))
    plt.close()
    
    # 8. avg_wait_time_at_relay_compare.png
    plt.figure(figsize=(10, 6))
    avg_wait_time_at_relay = []
    all_none = True
    for r in results:
        value = r["avg_wait_time_at_relay"]
        # 检查是否所有值都是 None
        if value is None:
            avg_wait_time_at_relay.append(np.nan)
        else:
            avg_wait_time_at_relay.append(value)
    
    # 检查是否所有值都是 0（表示都是 None）
    if all(v == 0 for v in avg_wait_time_at_relay):
        print("错误：avg_wait_time_at_relay 所有值都是 null，无法生成图表")
        return
    
    plt.bar(strategies, avg_wait_time_at_relay)
    plt.xlabel("Strategy")
    plt.ylabel("Average Wait Time at Relay")
    plt.title("Average Wait Time at Relay by Strategy")
    plt.savefig(layout.plot_path("avg_wait_time_at_relay_compare.png"))
    plt.close()
    
    # 9. charging_count_compare.png
    plt.figure(figsize=(10, 6))
    charging_count = [r["charging_count"] for r in results]
    plt.bar(strategies, charging_count)
    plt.xlabel("Strategy")
    plt.ylabel("Charging Count")
    plt.title("Charging Count by Strategy")
    plt.savefig(layout.plot_path("charging_count_compare.png"))
    plt.close()
    
    # Save comparison summary
    comparison_summary_file = layout.artifact_path("comparison_summary.txt")
    with open(comparison_summary_file, "w", encoding="utf-8") as f:
        f.write("Strategy Comparison Summary\n")
        f.write("============================\n")
        for result in results:
            f.write(f"Strategy: {result['strategy']}\n")
            f.write(f"  Completion Rate: {result['completion_rate'] * 100:.2f}%\n")
            f.write(f"  On Time Rate: {result['on_time_rate'] * 100:.2f}%\n")
            f.write(f"  Average Delivery Time: {result['avg_delivery_time']:.2f} steps\n")
            f.write(f"  Total Energy: {result['total_energy']:.2f}\n")
            f.write(f"  Average Energy per Task: {result['avg_energy_per_task'] if result['avg_energy_per_task'] is not None else 'N/A'}\n")
            f.write(f"  Energy per km: {result['energy_per_km'] if result['energy_per_km'] is not None else 'N/A'}\n")
            f.write(f"  Total Distance (AGV): {result['total_distance_agv']:.2f}\n")
            f.write(f"  Average Wait Time at Relay: {result['avg_wait_time_at_relay'] if result['avg_wait_time_at_relay'] is not None else 'N/A'}\n")
            f.write(f"  Charging Count: {result['charging_count']}\n")
            f.write(f"  Energy Saving Rate: {result.get('energy_saving_rate_vs_baseline', 'N/A'):.2f}%\n")
            f.write(f"  Emission Reduction Rate: {result.get('emission_reduction_rate_vs_baseline', 'N/A'):.2f}%\n")
            f.write("\n")
    
    # Save comparison_summary.json
    comparison_summary_json = {
        "baseline_strategy_name": baseline_strategy,
        "scenario_name": scenario_name,
        "seed": seed,
        "strategy_run_dir_map": strategy_run_dir_map,
        "metrics": {}
    }
    
    # 添加每个策略的9项指标值
    for result in results:
        strategy_metrics = {}
        for metric in core_metrics:
            strategy_metrics[metric] = result[metric]
        comparison_summary_json["metrics"][result["strategy"]] = strategy_metrics
    
    comparison_summary_json_file = layout.artifact_path("comparison_summary.json")
    with open(comparison_summary_json_file, "w", encoding="utf-8") as f:
        json.dump(comparison_summary_json, f, indent=2, ensure_ascii=False)
    
    print(f"Strategy comparison completed. Results saved to: {layout.run_dir}")

if __name__ == "__main__":
    main()
