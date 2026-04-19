"""
消融实验 (Ablation Study) - UAV-AGV 绿色物流优化器

本实验设计用于验证系统中各个关键组件的贡献，通过逐步移除或修改特定组件，
评估其对整体性能的影响。

消融维度:
1. 策略消融 (Strategy Ablation): 比较不同调度策略的性能
2. AGV协同消融 (AGV Cooperation Ablation): 评估AGV中继协同的贡献
3. 能耗模型消融 (Energy Model Ablation): 评估精细化能耗模型的影响
4. 充电策略消融 (Charging Strategy Ablation): 评估智能充电策略的贡献
5. 路径规划消融 (Path Planning Ablation): 评估路径规划算法的影响

作者: czr
日期: 2026-04-18
"""

import os
import sys
import json
import csv
import time
import random
import argparse
import copy
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config_loader import load_config
from config.config import (
    AGV_MAX_BATTERY, MAP_SIZE, UAV_INIT_BATTERY, UAV_MAX_BATTERY,
    DEFAULT_SIMULATION_STEPS, RANDOM_SEED
)
from src.core.agv import AGV
from src.core.uav import UAV
from src.core.task import Task
from src.simulation.environment import Environment
from src.simulation.simulator import Simulator
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.strategies.baseline_direct import BaselineDirectStrategy
from src.strategies.relay_coop import RelayCoopStrategy
from src.strategies.energy_priority import EnergyPriorityStrategy
from src.utils.simulator_helper import build_simulator
from src.utils.math_utils import generate_random_point


@dataclass
class AblationConfig:
    """消融实验配置"""
    name: str
    description: str
    enabled_components: Dict[str, bool]
    strategy_type: str
    modify_params: Dict[str, Any]


@dataclass
class ExperimentResult:
    """实验结果数据结构"""
    experiment_name: str
    config_name: str
    strategy_type: str
    seed: int
    num_uavs: int
    num_agvs: int
    num_tasks: int
    max_steps: int
    
    # 性能指标
    completion_rate: float
    on_time_rate: float
    avg_delivery_time: float
    total_energy: float
    avg_energy_per_task: float
    energy_per_km: float
    total_distance: float
    total_distance_agv: float
    charging_count: int
    avg_wait_time_at_relay: Optional[float]
    
    # 时间戳
    timestamp: str
    duration_seconds: float


class AblationExperimentRunner:
    """消融实验运行器"""
    
    def __init__(self, base_seed: int = 42, output_dir: str = None):
        self.base_seed = base_seed
        self.output_dir = output_dir or os.path.join(project_root, "results", "ablation")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.experiment_dir = os.path.join(self.output_dir, f"ablation_{self.timestamp}")
        
        # 创建输出目录
        os.makedirs(self.experiment_dir, exist_ok=True)
        
        # 定义消融实验配置
        self.ablation_configs = self._define_ablation_configs()
        
    def _define_ablation_configs(self) -> List[AblationConfig]:
        """定义所有消融实验配置"""
        configs = []
        
        # ========== 基线对照组 ==========
        configs.append(AblationConfig(
            name="baseline_full",
            description="完整系统 - 所有组件启用（对照组）",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="energy_priority",
            modify_params={}
        ))
        
        # ========== 策略消融 ==========
        configs.append(AblationConfig(
            name="strategy_baseline_direct",
            description="策略消融 - 使用基线直送策略（无优化）",
            enabled_components={
                "agv_cooperation": False,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="baseline_direct",
            modify_params={}
        ))
        
        configs.append(AblationConfig(
            name="strategy_relay_coop",
            description="策略消融 - 使用中继协同策略",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="relay_coop",
            modify_params={}
        ))
        
        # ========== AGV协同消融 ==========
        configs.append(AblationConfig(
            name="no_agv_cooperation",
            description="AGV协同消融 - 禁用AGV中继协同（仅UAV直送）",
            enabled_components={
                "agv_cooperation": False,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="baseline_direct",
            modify_params={}
        ))
        
        configs.append(AblationConfig(
            name="full_agv_cooperation",
            description="AGV协同消融 - 启用完整AGV中继协同",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="relay_coop",
            modify_params={}
        ))
        
        # ========== 能耗模型消融 ==========
        configs.append(AblationConfig(
            name="simple_energy_model",
            description="能耗模型消融 - 使用简化能耗模型（仅距离计算）",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": False,  # 使用简化模型
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="energy_priority",
            modify_params={"energy_model_type": "simple"}
        ))
        
        configs.append(AblationConfig(
            name="full_energy_model",
            description="能耗模型消融 - 使用完整精细化能耗模型",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="energy_priority",
            modify_params={"energy_model_type": "full"}
        ))
        
        # ========== 充电策略消融 ==========
        configs.append(AblationConfig(
            name="no_smart_charging",
            description="充电策略消融 - 禁用智能充电（固定阈值）",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": False,
                "path_planning": True,
            },
            strategy_type="energy_priority",
            modify_params={"charge_threshold_fixed": True}
        ))
        
        configs.append(AblationConfig(
            name="smart_charging_enabled",
            description="充电策略消融 - 启用智能充电策略",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="energy_priority",
            modify_params={"charge_threshold_fixed": False}
        ))
        
        # ========== 路径规划消融 ==========
        configs.append(AblationConfig(
            name="direct_path_only",
            description="路径规划消融 - 仅使用直线路径（无避障）",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": False,
            },
            strategy_type="energy_priority",
            modify_params={"path_planning_type": "direct"}
        ))
        
        configs.append(AblationConfig(
            name="astar_path_planning",
            description="路径规划消融 - 使用A*路径规划",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="energy_priority",
            modify_params={"path_planning_type": "astar"}
        ))
        
        # ========== 综合消融 ==========
        configs.append(AblationConfig(
            name="minimal_system",
            description="综合消融 - 最小系统（仅基础功能）",
            enabled_components={
                "agv_cooperation": False,
                "energy_model": False,
                "smart_charging": False,
                "path_planning": False,
            },
            strategy_type="baseline_direct",
            modify_params={}
        ))
        
        configs.append(AblationConfig(
            name="full_system",
            description="综合消融 - 完整系统（所有优化）",
            enabled_components={
                "agv_cooperation": True,
                "energy_model": True,
                "smart_charging": True,
                "path_planning": True,
            },
            strategy_type="energy_priority",
            modify_params={}
        ))
        
        return configs
    
    def _create_modified_simulator(self, config: AblationConfig, 
                                   environment: Environment,
                                   seed: int) -> Simulator:
        """根据消融配置创建修改后的仿真器"""
        
        # 创建基础组件
        energy_model = EnergyModel()
        path_planner = PathPlanner()
        scheduler = Scheduler(strategy_type=config.strategy_type)
        
        # 根据消融配置修改组件
        if not config.enabled_components.get("energy_model", True):
            # 简化能耗模型 - 仅基于距离计算
            energy_model.cruise_energy_per_km = 5.0
            energy_model.takeoff_energy_base = 0.0
            energy_model.landing_energy_base = 0.0
            energy_model.hover_energy_per_min = 0.0
        
        if not config.enabled_components.get("path_planning", True):
            # 禁用复杂路径规划 - 使用直线路径
            path_planner = None
        
        # 创建仿真器
        simulator = Simulator(
            environment=environment,
            energy_model=energy_model,
            path_planner=path_planner,
            scheduler=scheduler,
            strategy_type=config.strategy_type,
            scenario_name=config.name,
            seed=seed
        )
        
        # 应用其他修改参数
        if config.modify_params.get("charge_threshold_fixed", False):
            simulator.charge_start_threshold = 30.0  # 固定阈值
        
        # 设置路径规划超时，防止A*算法陷入无限循环
        if hasattr(simulator, 'path_planner') and simulator.path_planner is not None:
            simulator.path_planner.max_iterations = 10000
            simulator.path_planner.time_limit = 5.0  # 5秒超时
        
        return simulator
    
    def run_single_experiment(self, config: AblationConfig, 
                              num_uavs: int = 3,
                              num_agvs: int = 2, 
                              num_tasks: int = 6,
                              max_steps: int = 200,
                              seed: int = None) -> ExperimentResult:
        """运行单个消融实验"""
        
        if seed is None:
            seed = self.base_seed
        
        random.seed(seed)
        start_time = time.time()
        
        # 创建环境
        environment = Environment(map_size=MAP_SIZE)
        
        # 创建UAV
        for i in range(num_uavs):
            position = generate_random_point(MAP_SIZE)
            uav = UAV(i + 1, position)
            uav.battery = UAV_INIT_BATTERY
            environment.uavs.append(uav)
        
        # 创建AGV（根据配置决定是否启用）
        if config.enabled_components.get("agv_cooperation", True):
            for i in range(num_agvs):
                position = generate_random_point(MAP_SIZE)
                agv = AGV(i + 1, position)
                agv.charging_power = AGV_MAX_BATTERY * 2
                environment.agvs.append(agv)
        
        # 生成任务
        environment.generate_tasks(num_tasks, seed=seed)
        
        # 创建仿真器
        simulator = self._create_modified_simulator(config, environment, seed)
        
        # 运行仿真
        output_dir = simulator.run(max_steps=max_steps, experiment_name=config.name)
        
        # 收集结果
        duration = time.time() - start_time
        
        # 从仿真器获取指标
        metrics = self._extract_metrics(simulator, output_dir)
        
        result = ExperimentResult(
            experiment_name=config.name,
            config_name=config.description,
            strategy_type=config.strategy_type,
            seed=seed,
            num_uavs=num_uavs,
            num_agvs=num_agvs if config.enabled_components.get("agv_cooperation", True) else 0,
            num_tasks=num_tasks,
            max_steps=max_steps,
            completion_rate=metrics.get("completion_rate", 0.0),
            on_time_rate=metrics.get("on_time_rate", 0.0),
            avg_delivery_time=metrics.get("avg_delivery_time", 0.0),
            total_energy=metrics.get("total_energy", 0.0),
            avg_energy_per_task=metrics.get("avg_energy_per_task", 0.0),
            energy_per_km=metrics.get("energy_per_km", 0.0),
            total_distance=metrics.get("total_distance", 0.0),
            total_distance_agv=metrics.get("total_distance_agv", 0.0),
            charging_count=metrics.get("charging_count", 0),
            avg_wait_time_at_relay=metrics.get("avg_wait_time_at_relay"),
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration
        )
        
        return result
    
    def _extract_metrics(self, simulator: Simulator, output_dir: str) -> Dict[str, Any]:
        """从仿真器输出中提取指标"""
        metrics = {}
        
        # 尝试从metrics.json读取
        metrics_file = os.path.join(output_dir, "metrics.json")
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
        else:
            # 从仿真器对象直接获取
            metrics = {
                "completion_rate": simulator.completed_tasks / max(simulator.initial_task_count, 1),
                "on_time_rate": getattr(simulator, 'on_time_rate', 0.0),
                "avg_delivery_time": getattr(simulator, 'avg_delivery_time', 0.0),
                "total_energy": simulator.total_energy,
                "avg_energy_per_task": simulator.total_energy / max(simulator.completed_tasks, 1),
                "energy_per_km": simulator.total_energy / max(simulator.total_distance, 1),
                "total_distance": simulator.total_distance,
                "total_distance_agv": getattr(simulator, 'total_distance_agv', 0.0),
                "charging_count": simulator.charging_count,
                "avg_wait_time_at_relay": getattr(simulator, 'avg_wait_time_at_relay', None),
            }
        
        return metrics
    
    def run_all_experiments(self, num_uavs: int = 3, num_agvs: int = 2,
                           num_tasks: int = 6, max_steps: int = 200,
                           num_runs: int = 3) -> List[ExperimentResult]:
        """运行所有消融实验"""
        
        all_results = []
        
        print(f"开始消融实验 - 共 {len(self.ablation_configs)} 个配置，每个运行 {num_runs} 次")
        print(f"实验目录: {self.experiment_dir}")
        print("=" * 80)
        
        for i, config in enumerate(self.ablation_configs, 1):
            print(f"\n[{i}/{len(self.ablation_configs)}] 运行配置: {config.name}")
            print(f"描述: {config.description}")
            print(f"策略: {config.strategy_type}")
            
            config_results = []
            for run in range(num_runs):
                seed = self.base_seed + run
                print(f"  运行 {run + 1}/{num_runs} (seed={seed})...", end=" ")
                
                try:
                    result = self.run_single_experiment(
                        config=config,
                        num_uavs=num_uavs,
                        num_agvs=num_agvs,
                        num_tasks=num_tasks,
                        max_steps=max_steps,
                        seed=seed
                    )
                    config_results.append(result)
                    print(f"完成 (耗时: {result.duration_seconds:.2f}s)")
                except Exception as e:
                    print(f"失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            all_results.extend(config_results)
        
        print("\n" + "=" * 80)
        print(f"所有实验完成！共收集 {len(all_results)} 个结果")
        
        return all_results
    
    def save_results(self, results: List[ExperimentResult]):
        """保存实验结果到文件"""
        
        # 保存为CSV
        csv_file = os.path.join(self.experiment_dir, "ablation_results.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=asdict(results[0]).keys())
                writer.writeheader()
                for result in results:
                    writer.writerow(asdict(result))
        
        print(f"\n结果已保存到: {csv_file}")
        
        # 保存为JSON
        json_file = os.path.join(self.experiment_dir, "ablation_results.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)
        
        print(f"结果已保存到: {json_file}")
        
        # 生成汇总报告
        self._generate_summary_report(results)
    
    def _generate_summary_report(self, results: List[ExperimentResult]):
        """生成消融实验汇总报告"""
        
        report_file = os.path.join(self.experiment_dir, "ablation_report.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("UAV-AGV 绿色物流优化器 - 消融实验报告\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"实验目录: {self.experiment_dir}\n")
            f.write("=" * 80 + "\n\n")
            
            # 按配置分组统计
            from collections import defaultdict
            config_groups = defaultdict(list)
            for r in results:
                config_groups[r.experiment_name].append(r)
            
            # 计算每个配置的平均值
            f.write("【各配置平均性能】\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'配置名称':<30} {'完成率':>10} {'准时率':>10} {'平均能耗':>12} {'总能量':>12}\n")
            f.write("-" * 80 + "\n")
            
            for config_name, config_results in sorted(config_groups.items()):
                avg_completion = sum(r.completion_rate for r in config_results) / len(config_results)
                avg_on_time = sum(r.on_time_rate for r in config_results) / len(config_results)
                avg_energy_per_task = sum(r.avg_energy_per_task for r in config_results) / len(config_results)
                avg_total_energy = sum(r.total_energy for r in config_results) / len(config_results)
                
                f.write(f"{config_name:<30} {avg_completion:>10.3f} {avg_on_time:>10.3f} "
                       f"{avg_energy_per_task:>12.2f} {avg_total_energy:>12.2f}\n")
            
            f.write("\n")
            
            # 消融分析
            f.write("【消融分析】\n")
            f.write("-" * 80 + "\n")
            
            # 策略消融对比
            f.write("\n1. 策略消融对比:\n")
            self._write_comparison(f, config_groups, 
                ["strategy_baseline_direct", "strategy_relay_coop", "baseline_full"],
                ["基线直送", "中继协同", "能耗优先(完整)"])
            
            # AGV协同消融
            f.write("\n2. AGV协同消融:\n")
            self._write_comparison(f, config_groups,
                ["no_agv_cooperation", "full_agv_cooperation"],
                ["无AGV协同", "有AGV协同"])
            
            # 能耗模型消融
            f.write("\n3. 能耗模型消融:\n")
            self._write_comparison(f, config_groups,
                ["simple_energy_model", "full_energy_model"],
                ["简化能耗模型", "完整能耗模型"])
            
            # 充电策略消融
            f.write("\n4. 充电策略消融:\n")
            self._write_comparison(f, config_groups,
                ["no_smart_charging", "smart_charging_enabled"],
                ["固定阈值充电", "智能充电"])
            
            # 路径规划消融
            f.write("\n5. 路径规划消融:\n")
            self._write_comparison(f, config_groups,
                ["direct_path_only", "astar_path_planning"],
                ["直线路径", "A*路径规划"])
            
            # 综合消融
            f.write("\n6. 综合消融对比:\n")
            self._write_comparison(f, config_groups,
                ["minimal_system", "full_system"],
                ["最小系统", "完整系统"])
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("报告生成完成\n")
        
        print(f"汇总报告已保存到: {report_file}")
    
    def _write_comparison(self, f, config_groups, keys, labels):
        """写入对比数据"""
        for key, label in zip(keys, labels):
            if key in config_groups:
                results = config_groups[key]
                avg_completion = sum(r.completion_rate for r in results) / len(results)
                avg_energy = sum(r.total_energy for r in results) / len(results)
                f.write(f"  {label:<20} - 完成率: {avg_completion:.3f}, 总能量: {avg_energy:.2f}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="UAV-AGV 消融实验")
    parser.add_argument("--num-uavs", type=int, default=3, help="UAV数量")
    parser.add_argument("--num-agvs", type=int, default=2, help="AGV数量")
    parser.add_argument("--num-tasks", type=int, default=6, help="任务数量")
    parser.add_argument("--max-steps", type=int, default=200, help="最大仿真步数")
    parser.add_argument("--num-runs", type=int, default=3, help="每个配置运行次数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--output-dir", type=str, default=None, help="输出目录")
    
    args = parser.parse_args()
    
    # 创建并运行实验
    runner = AblationExperimentRunner(
        base_seed=args.seed,
        output_dir=args.output_dir
    )
    
    results = runner.run_all_experiments(
        num_uavs=args.num_uavs,
        num_agvs=args.num_agvs,
        num_tasks=args.num_tasks,
        max_steps=args.max_steps,
        num_runs=args.num_runs
    )
    
    # 保存结果
    runner.save_results(results)
    
    print(f"\n消融实验全部完成！")
    print(f"结果保存在: {runner.experiment_dir}")


if __name__ == "__main__":
    main()
