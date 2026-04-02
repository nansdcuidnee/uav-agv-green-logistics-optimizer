"""Smoke and reproducibility tests for the refactored simulation flow."""

import json
import os
import random

from src.core.agv import AGV
from src.core.task import Task
from src.core.uav import UAV
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.simulation.environment import Environment
from src.simulation.simulator import Simulator


def _build_environment(seed=42):
    random.seed(seed)
    environment = Environment(map_size=(100, 100))

    uav = UAV(1, (10, 10))
    agv = AGV(1, (10, 10))

    environment.uavs.append(uav)
    environment.agvs.append(agv)

    # Use deterministic and short tasks so smoke tests are stable.
    environment.tasks = [
        Task(task_id=1, start_point=(10, 10), end_point=(20, 20), payload=1, priority=1),
        Task(task_id=2, start_point=(20, 20), end_point=(30, 30), payload=1, priority=1),
    ]
    environment.delivery_points = [task.end_point for task in environment.tasks]

    return environment


def _run_once(strategy_type="baseline_direct", seed=42, experiment_name="smoke_test"):
    environment = _build_environment(seed=seed)
    simulator = Simulator(
        environment,
        EnergyModel(),
        PathPlanner(),
        Scheduler(),
        strategy_type=strategy_type,
    )
    output_dir = simulator.run(max_steps=200, experiment_name=experiment_name)

    metrics_file = os.path.join(output_dir, "metrics.json")
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    return output_dir, metrics


def test_smoke_flow_and_required_artifacts():
    output_dir, metrics = _run_once(strategy_type="baseline_direct", seed=42, experiment_name="smoke_test")

    assert os.path.exists(output_dir), f"结果目录不存在: {output_dir}"
    assert os.path.exists(os.path.join(output_dir, "metrics.json")), "metrics.json 不存在"
    assert os.path.exists(os.path.join(output_dir, "records.csv")), "records.csv 不存在"
    assert os.path.exists(os.path.join(output_dir, "chart.png")), "chart.png 不存在"

    assert metrics["task_completion_rate"] > 0, "任务完成率应大于 0"


def test_metrics_schema_and_types():
    _, metrics = _run_once(strategy_type="baseline_direct", seed=42, experiment_name="metrics_test")

    required_metrics = [
        "total_energy",
        "avg_energy_per_task",
        "energy_per_km",
        "energy_saving_rate_vs_baseline",
        "emission_reduction_rate_vs_baseline",
        "task_completion_rate",
        "completed_tasks",
        "total_time",
        "charging_count",
        "total_distance_km",
        "baseline_energy",
    ]

    for metric in required_metrics:
        assert metric in metrics, f"缺少指标: {metric}"
        assert isinstance(metrics[metric], (int, float)), f"指标 {metric} 类型错误: {type(metrics[metric])}"


def test_strategy_switching_runs_all_strategies():
    for strategy in ["baseline_direct", "relay_coop", "energy_priority"]:
        _, metrics = _run_once(strategy_type=strategy, seed=42, experiment_name=f"switch_{strategy}")
        assert metrics["total_time"] > 0, f"策略 {strategy} 未正常运行"


def test_reproducibility():
    _, metrics_1 = _run_once(strategy_type="baseline_direct", seed=42, experiment_name="repro_test_1")
    _, metrics_2 = _run_once(strategy_type="baseline_direct", seed=42, experiment_name="repro_test_2")

    for key in metrics_1:
        if isinstance(metrics_1[key], (int, float)):
            diff = abs(metrics_1[key] - metrics_2[key])
            assert diff <= 1e-6, f"指标 {key} 差异过大: {diff}"


if __name__ == "__main__":
    test_smoke_flow_and_required_artifacts()
    test_metrics_schema_and_types()
    test_strategy_switching_runs_all_strategies()
    test_reproducibility()
    print("\n=== 所有测试通过 ===\n")
