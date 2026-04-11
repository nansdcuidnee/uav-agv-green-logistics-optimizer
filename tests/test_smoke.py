"""Smoke and reproducibility tests for the simulation pipeline."""

import json
import os
import random
import sys
from pathlib import Path


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

    environment.tasks = [
        Task(id=1, start_point=(10, 10), end_point=(20, 20), payload=1, priority=1),
        Task(id=2, start_point=(20, 20), end_point=(30, 30), payload=1, priority=1),
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
    output_dir = simulator.run(max_steps=200, experiment_name=experiment_name, result_type="tests")

    metrics_file = os.path.join(output_dir, "metrics.json")
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    return output_dir, metrics


def test_smoke_flow_and_required_artifacts():
    output_dir, metrics = _run_once(strategy_type="baseline_direct", seed=42, experiment_name="smoke_test")
    output_path = Path(output_dir)

    assert os.path.exists(output_dir), f"result dir does not exist: {output_dir}"
    assert os.path.exists(os.path.join(output_dir, "metrics.json")), "missing metrics.json"
    assert os.path.exists(os.path.join(output_dir, "metadata.json")), "missing metadata.json"
    assert (output_path / "records" / "steps.csv").exists(), "missing records/steps.csv"
    assert (output_path / "records" / "tasks.csv").exists(), "missing records/tasks.csv"
    assert (output_path / "plots" / "chart.png").exists(), "missing plots/chart.png"
    assert (output_path / "plots" / "energy_plot.png").exists(), "missing plots/energy_plot.png"
    assert (output_path / "plots" / "task_plot.png").exists(), "missing plots/task_plot.png"
    assert output_path.parent.parent.name == "tests", f"unexpected parent dir: {output_path.parent.parent}"
    assert output_path.parent.name == "smoke_test", f"unexpected experiment dir: {output_path.parent}"

    assert metrics["task_completion_rate"] > 0, "task completion rate should be > 0"


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
        assert metric in metrics, f"missing metric: {metric}"
        assert isinstance(metrics[metric], (int, float)), f"metric type error for {metric}"


def test_strategy_switching_runs_all_strategies():
    for strategy in ["baseline_direct", "relay_coop", "energy_priority"]:
        _, metrics = _run_once(strategy_type=strategy, seed=42, experiment_name=f"switch_{strategy}")
        assert metrics["total_time"] > 0, f"strategy did not run: {strategy}"


def test_reproducibility():
    _, metrics_1 = _run_once(strategy_type="baseline_direct", seed=42, experiment_name="repro_test_1")
    _, metrics_2 = _run_once(strategy_type="baseline_direct", seed=42, experiment_name="repro_test_2")

    for key in metrics_1:
        if isinstance(metrics_1[key], (int, float)):
            diff = abs(metrics_1[key] - metrics_2[key])
            assert diff <= 1e-6, f"metric drift too large for {key}: {diff}"


if __name__ == "__main__":
    test_smoke_flow_and_required_artifacts()
    test_metrics_schema_and_types()
    test_strategy_switching_runs_all_strategies()
    test_reproducibility()
    print("\n=== all tests passed ===\n")
