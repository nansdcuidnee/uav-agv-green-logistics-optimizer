#!/usr/bin/env python3
"""鲁棒性实验脚本"""

import argparse
import csv
import json
import os
import random
import yaml
from pathlib import Path
from datetime import datetime
import numpy as np

from src.utils.simulator_helper import build_environment, build_simulator
from src.utils.result_layout import create_robustness_layout, create_robustness_summary_layout, write_metadata


def run_round1_single_factor(campaign_name, max_steps, seeds, strategies):
    """运行第一轮：单因素敏感性分析"""
    results = []
    
    # 定义不同场景
    scenes = [
        {'name': 'scene_small', 'num_tasks': 3, 'num_uavs': 1, 'num_agvs': 1, 'map_size': {'width': 500, 'height': 500}},
        {'name': 'scene_medium', 'num_tasks': 5, 'num_uavs': 2, 'num_agvs': 2, 'map_size': {'width': 1000, 'height': 1000}},
        {'name': 'scene_large', 'num_tasks': 8, 'num_uavs': 3, 'num_agvs': 3, 'map_size': {'width': 1500, 'height': 1500}}
    ]
    
    for scene in scenes:
        for strategy in strategies:
            for seed in seeds:
                print(f"\n=== Round 1: Single Factor - Scene: {scene['name']}, Strategy: {strategy}, Seed: {seed} ===")
                
                # 构建配置
                config = {
                    'seed': seed,
                    'max_steps': max_steps,
                    'num_tasks': scene['num_tasks'],
                    'num_uavs': scene['num_uavs'],
                    'num_agvs': scene['num_agvs'],
                    'map_size': scene['map_size']
                }
                
                # 构建环境和仿真器
                env = build_environment(config)
                simulator = build_simulator(env, strategy, scenario_name=f"round1_{scene['name']}_{strategy}", seed=seed)
                
                # 运行仿真器
                output_dir = simulator.run(
                    max_steps=max_steps,
                    experiment_name=f"{scene['name']}_{strategy}_seed{seed}",
                    result_type="round1_single_factor",
                    campaign_name=campaign_name
                )
                
                # 读取metrics
                metrics_file = Path(output_dir) / "metrics.json"
                if metrics_file.exists():
                    with open(metrics_file, 'r', encoding='utf-8') as f:
                        metrics = json.load(f)
                        results.append({
                            'round': 1,
                            'strategy': strategy,
                            'seed': seed,
                            'scene': scene['name'],
                            'completion_rate': metrics.get('completion_rate', 0),
                            'on_time_rate': metrics.get('on_time_rate', 0),
                            'total_energy': metrics.get('total_energy', 0),
                            'total_time': metrics.get('total_time', 0),
                            'charging_count': metrics.get('charging_count', 0),
                            'avg_wait_time_at_relay': metrics.get('avg_wait_time_at_relay', 0),
                            'run_dir': output_dir
                        })
                else:
                    raise FileNotFoundError(f"metrics.json not found in {output_dir}")
    
    # 校验样本数
    expected = len(scenes) * len(strategies) * len(seeds)
    actual = len(results)
    if actual != expected:
        raise ValueError(f"Round 1: Expected {expected} results, got {actual}")
    
    return results


def run_round2_perturbation(campaign_name, max_steps, seeds, strategies):
    """运行第二轮：扰动鲁棒性测试"""
    results = []
    
    # 定义不同的扰动因子
    perturbations = [
        {'name': 'obstacles_high', 'obstacles': {'count': 10}, 'num_no_fly_zones': 0, 'task_density': 0.5, 'time_window': {'min': 200, 'max': 300}},
        {'name': 'no_fly_zones_high', 'obstacles': {'count': 5}, 'num_no_fly_zones': 5, 'task_density': 0.5, 'time_window': {'min': 200, 'max': 300}},
        {'name': 'task_density_high', 'obstacles': {'count': 5}, 'num_no_fly_zones': 0, 'task_density': 0.9, 'time_window': {'min': 200, 'max': 300}},
        {'name': 'time_window_short', 'obstacles': {'count': 5}, 'num_no_fly_zones': 0, 'task_density': 0.5, 'time_window': {'min': 50, 'max': 100}},
        {'name': 'battery_low', 'obstacles': {'count': 5}, 'num_no_fly_zones': 0, 'task_density': 0.5, 'time_window': {'min': 200, 'max': 300}}  # 初始电量较低
    ]
    
    for perturbation in perturbations:
        for strategy in strategies:
            for seed in seeds:
                print(f"\n=== Round 2: Perturbation - Factor: {perturbation['name']}, Strategy: {strategy}, Seed: {seed} ===")
                
                # 构建配置，添加扰动
                config = {
                    'seed': seed,
                    'max_steps': max_steps,
                    'num_tasks': 5,
                    'num_uavs': 2,
                    'num_agvs': 2,
                    'obstacles': perturbation['obstacles'],
                    'num_no_fly_zones': perturbation['num_no_fly_zones'],
                    'task_density': perturbation['task_density'],
                    'time_window': perturbation['time_window']
                }
                
                # 构建环境和仿真器
                env = build_environment(config)
                # 如果指定了初始电量，修改UAV的电池容量
                if 'uav_battery' in perturbation:
                    for uav in env.uavs:
                        uav.battery = perturbation['uav_battery']
                simulator = build_simulator(env, strategy, scenario_name=f"round2_{perturbation['name']}_{strategy}", seed=seed)
                
                # 运行仿真器
                output_dir = simulator.run(
                    max_steps=max_steps,
                    experiment_name=f"{perturbation['name']}_{strategy}_seed{seed}",
                    result_type="round2_perturbation",
                    campaign_name=campaign_name
                )
                
                # 读取metrics
                metrics_file = Path(output_dir) / "metrics.json"
                if metrics_file.exists():
                    with open(metrics_file, 'r', encoding='utf-8') as f:
                        metrics = json.load(f)
                        results.append({
                            'round': 2,
                            'strategy': strategy,
                            'seed': seed,
                            'perturbation': perturbation['name'],
                            'completion_rate': metrics.get('completion_rate', 0),
                            'on_time_rate': metrics.get('on_time_rate', 0),
                            'total_energy': metrics.get('total_energy', 0),
                            'total_time': metrics.get('total_time', 0),
                            'charging_count': metrics.get('charging_count', 0),
                            'avg_wait_time_at_relay': metrics.get('avg_wait_time_at_relay', 0),
                            'run_dir': output_dir
                        })
                else:
                    raise FileNotFoundError(f"metrics.json not found in {output_dir}")
    
    # 校验样本数
    expected = len(perturbations) * len(strategies) * len(seeds)
    actual = len(results)
    if actual != expected:
        raise ValueError(f"Round 2: Expected {expected} results, got {actual}")
    
    return results


def run_round3_extreme_combo(campaign_name, max_steps, seeds, strategies):
    """运行第三轮：极端组合测试"""
    results = []
    
    # 基于前两轮最差的因子组合成极端场景
    extreme_scenarios = [
        {
            'name': 'extreme_1',
            'description': '高障碍物 + 高禁飞区 + 高任务密度',
            'config': {
                'num_tasks': 10,
                'num_uavs': 2,
                'num_agvs': 1,
                'obstacles': {'count': 15},
                'num_no_fly_zones': 8,
                'task_density': 0.95,
                'time_window': {'min': 50, 'max': 100}
            }
        },
        {
            'name': 'extreme_2',
            'description': '短时间窗口 + 低初始电量 + 少AGV',
            'config': {
                'num_tasks': 8,
                'num_uavs': 2,
                'num_agvs': 1,
                'obstacles': {'count': 5},
                'num_no_fly_zones': 0,
                'task_density': 0.8,
                'time_window': {'min': 30, 'max': 60}
            }
        },
        {
            'name': 'extreme_3',
            'description': '大场景 + 高任务密度 + 短时间窗口',
            'config': {
                'num_tasks': 12,
                'num_uavs': 3,
                'num_agvs': 2,
                'obstacles': {'count': 10},
                'num_no_fly_zones': 5,
                'task_density': 0.9,
                'time_window': {'min': 40, 'max': 80},
                'map_size': {'width': 2000, 'height': 2000}
            }
        }
    ]
    
    for scenario in extreme_scenarios:
        for strategy in strategies:
            for seed in seeds:
                print(f"\n=== Round 3: Extreme Combo - Scenario: {scenario['name']}, Strategy: {strategy}, Seed: {seed} ===")
                print(f"  Description: {scenario['description']}")
                
                # 构建配置
                config = {
                    'seed': seed,
                    'max_steps': max_steps,
                    **scenario['config']
                }
                
                # 构建环境和仿真器
                env = build_environment(config)
                # 设置初始电量较低
                for uav in env.uavs:
                    uav.battery = 40  # 初始电量较低
                simulator = build_simulator(env, strategy, scenario_name=f"round3_{scenario['name']}_{strategy}", seed=seed)
                
                # 运行仿真器
                output_dir = simulator.run(
                    max_steps=max_steps,
                    experiment_name=f"{scenario['name']}_{strategy}_seed{seed}",
                    result_type="round3_extreme_combo",
                    campaign_name=campaign_name
                )
                
                # 读取metrics
                metrics_file = Path(output_dir) / "metrics.json"
                if metrics_file.exists():
                    with open(metrics_file, 'r', encoding='utf-8') as f:
                        metrics = json.load(f)
                        results.append({
                            'round': 3,
                            'strategy': strategy,
                            'seed': seed,
                            'scenario': scenario['name'],
                            'description': scenario['description'],
                            'completion_rate': metrics.get('completion_rate', 0),
                            'on_time_rate': metrics.get('on_time_rate', 0),
                            'total_energy': metrics.get('total_energy', 0),
                            'total_time': metrics.get('total_time', 0),
                            'charging_count': metrics.get('charging_count', 0),
                            'avg_wait_time_at_relay': metrics.get('avg_wait_time_at_relay', 0),
                            'run_dir': output_dir
                        })
                else:
                    raise FileNotFoundError(f"metrics.json not found in {output_dir}")
    
    # 校验样本数
    expected = len(extreme_scenarios) * len(strategies) * len(seeds)
    actual = len(results)
    if actual != expected:
        raise ValueError(f"Round 3: Expected {expected} results, got {actual}")
    
    return results


def generate_summary(campaign_name, all_results):
    """生成汇总文件"""
    summary_dir = create_robustness_summary_layout(campaign_name)
    
    # 生成CSV文件（逐run明细）
    csv_file = summary_dir / "robustness_summary.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 写入表头，包含所有可能的字段
        writer.writerow(['round', 'strategy', 'seed', 'scene', 'perturbation', 'scenario', 'description', 'completion_rate', 'on_time_rate', 'total_energy', 'total_time', 'charging_count', 'avg_wait_time_at_relay', 'run_dir'])
        for result in all_results:
            writer.writerow([
                result.get('round', ''),
                result.get('strategy', ''),
                result.get('seed', ''),
                result.get('scene', ''),
                result.get('perturbation', ''),
                result.get('scenario', ''),
                result.get('description', ''),
                result.get('completion_rate', 0),
                result.get('on_time_rate', 0),
                result.get('total_energy', 0),
                result.get('total_time', 0),
                result.get('charging_count', 0),
                result.get('avg_wait_time_at_relay', 0),
                result.get('run_dir', '')
            ])
    
    # 生成JSON文件（逐run明细）
    json_file = summary_dir / "robustness_summary.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    # 生成按round+strategy聚合的统计文件
    stats_file = summary_dir / "robustness_stats_by_round.csv"
    with open(stats_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['round', 'strategy', 'median_completion_rate', 'p10_completion_rate', 'p90_completion_rate', 'median_on_time_rate', 'p10_on_time_rate', 'p90_on_time_rate', 'median_total_energy', 'p10_total_energy', 'p90_total_energy', 'median_total_time', 'p10_total_time', 'p90_total_time', 'failure_rate', 'n'])
        
        # 按round和strategy分组
        groups = {}
        for result in all_results:
            key = (result['round'], result['strategy'])
            if key not in groups:
                groups[key] = []
            groups[key].append(result)
        
        # 计算每组的统计指标
        for (round_num, strategy), group_results in groups.items():
            # 提取指标数据
            completion_rates = [r['completion_rate'] for r in group_results]
            on_time_rates = [r['on_time_rate'] for r in group_results]
            total_energies = [r['total_energy'] for r in group_results]
            total_times = [r['total_time'] for r in group_results]
            
            # 计算统计指标
            median_completion = np.median(completion_rates)
            p10_completion = np.percentile(completion_rates, 10)
            p90_completion = np.percentile(completion_rates, 90)
            
            median_on_time = np.median(on_time_rates)
            p10_on_time = np.percentile(on_time_rates, 10)
            p90_on_time = np.percentile(on_time_rates, 90)
            
            median_energy = np.median(total_energies)
            p10_energy = np.percentile(total_energies, 10)
            p90_energy = np.percentile(total_energies, 90)
            
            median_time = np.median(total_times)
            p10_time = np.percentile(total_times, 10)
            p90_time = np.percentile(total_times, 90)
            
            # 计算失败率（completion_rate < 1 计失败）
            failure_count = sum(1 for r in group_results if r['completion_rate'] < 1)
            failure_rate = failure_count / len(group_results) if group_results else 0
            
            # 写入统计数据
            writer.writerow([
                round_num,
                strategy,
                median_completion,
                p10_completion,
                p90_completion,
                median_on_time,
                p10_on_time,
                p90_on_time,
                median_energy,
                p10_energy,
                p90_energy,
                median_time,
                p10_time,
                p90_time,
                failure_rate,
                len(group_results)
            ])
    
    # 生成鲁棒性排名文件
    ranking_file = summary_dir / "robustness_ranking.csv"
    with open(ranking_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['rank', 'strategy', 'round', 'median_completion_rate', 'median_on_time_rate', 'median_total_energy', 'median_total_time', 'failure_rate', 'composite_score'])
        
        # 计算每个策略在每个轮次的综合得分
        ranking_data = []
        for (round_num, strategy), group_results in groups.items():
            # 提取指标数据
            completion_rates = [r['completion_rate'] for r in group_results]
            on_time_rates = [r['on_time_rate'] for r in group_results]
            total_energies = [r['total_energy'] for r in group_results]
            total_times = [r['total_time'] for r in group_results]
            
            # 计算统计指标
            median_completion = np.median(completion_rates)
            median_on_time = np.median(on_time_rates)
            median_energy = np.median(total_energies)
            median_time = np.median(total_times)
            
            # 计算失败率
            failure_count = sum(1 for r in group_results if r['completion_rate'] < 1)
            failure_rate = failure_count / len(group_results) if group_results else 0
            
            # 计算综合得分（越高越好）
            # 权重：完成率(0.4) + 准时率(0.2) + 能量效率(0.2) + 时间效率(0.2)
            # 能量和时间取倒数，因为越小越好
            energy_score = 1 / (median_energy + 1)  # +1避免除零
            time_score = 1 / (median_time + 1)      # +1避免除零
            composite_score = (median_completion * 0.4) + (median_on_time * 0.2) + (energy_score * 0.2) + (time_score * 0.2)
            
            ranking_data.append({
                'round': round_num,
                'strategy': strategy,
                'median_completion_rate': median_completion,
                'median_on_time_rate': median_on_time,
                'median_total_energy': median_energy,
                'median_total_time': median_time,
                'failure_rate': failure_rate,
                'composite_score': composite_score
            })
        
        # 按综合得分排序
        ranking_data.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # 写入排名数据
        for i, item in enumerate(ranking_data, 1):
            writer.writerow([
                i,
                item['strategy'],
                item['round'],
                item['median_completion_rate'],
                item['median_on_time_rate'],
                item['median_total_energy'],
                item['median_total_time'],
                item['failure_rate'],
                item['composite_score']
            ])
    
    # 生成排名规则的metadata文件
    ranking_metadata = {
        'ranking_rules': {
            'composite_score_calculation': '0.4 * median_completion_rate + 0.2 * median_on_time_rate + 0.2 * (1/(median_total_energy + 1)) + 0.2 * (1/(median_total_time + 1))',
            'ranking_criteria': 'Higher composite score is better',
            'weights': {
                'completion_rate': 0.4,
                'on_time_rate': 0.2,
                'energy_efficiency': 0.2,
                'time_efficiency': 0.2
            }
        }
    }
    metadata_file = summary_dir / "ranking_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(ranking_metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== 汇总文件生成完成 ===")
    print(f"明细CSV文件: {csv_file}")
    print(f"明细JSON文件: {json_file}")
    print(f"按轮次统计文件: {stats_file}")
    print(f"鲁棒性排名文件: {ranking_file}")
    print(f"排名规则文件: {metadata_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行鲁棒性实验")
    parser.add_argument("--campaign-name", type=str, default="default", help="鲁棒性实验名称")
    parser.add_argument("--round", type=str, default="all", choices=["1", "2", "3", "all"], help="运行的轮次")
    parser.add_argument("--max-steps", type=int, default=100, help="最大步数")
    parser.add_argument("--seeds", type=str, default="42", help="种子列表，逗号分隔")
    
    args = parser.parse_args()
    
    # 解析种子列表
    seeds = [int(seed.strip()) for seed in args.seeds.split(',')]
    
    # 策略列表
    strategies = ["baseline_direct", "relay_coop", "energy_priority"]
    
    # 运行实验
    all_results = []
    
    if args.round in ["1", "all"]:
        round1_results = run_round1_single_factor(args.campaign_name, args.max_steps, seeds, strategies)
        all_results.extend(round1_results)
    
    if args.round in ["2", "all"]:
        round2_results = run_round2_perturbation(args.campaign_name, args.max_steps, seeds, strategies)
        all_results.extend(round2_results)
    
    if args.round in ["3", "all"]:
        round3_results = run_round3_extreme_combo(args.campaign_name, args.max_steps, seeds, strategies)
        all_results.extend(round3_results)
    
    # 校验总样本数
    expected_total = 0
    if args.round in ["1", "all"]:
        expected_total += len(strategies) * len(seeds)
    if args.round in ["2", "all"]:
        expected_total += len(strategies) * len(seeds)
    if args.round in ["3", "all"]:
        expected_total += len(strategies) * len(seeds)
    
    actual_total = len(all_results)
    if actual_total != expected_total:
        raise ValueError(f"Expected {expected_total} total results, got {actual_total}")
    
    # 生成汇总文件
    generate_summary(args.campaign_name, all_results)
    
    print(f"\n=== 鲁棒性实验完成 ===")
    print(f"结果保存到: results/robustness/{args.campaign_name}")


if __name__ == "__main__":
    main()
