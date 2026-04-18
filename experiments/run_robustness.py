﻿#!/usr/bin/env python3
"""Run robustness experiments in a config-driven way."""

import argparse
import csv
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
from config.config_loader import load_config
from src.utils.simulator_helper import build_environment, build_simulator
from src.utils.result_layout import create_robustness_summary_layout

SUPPORTED_EXPERIMENT_TYPES = {"seed_stability", "scale", "capacity", "failure"}
DEFAULT_STRATEGIES = ["baseline_direct", "relay_coop", "energy_priority"]


def load_campaign_config(config_path: str) -> dict[str, Any]:
    """Load robustness experiment config with extends/normalization support."""
    return load_config(config_path)


def normalize_cases(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize config into a uniform list of executable cases."""
    experiment_type = config.get("experiment_type")
    if experiment_type not in SUPPORTED_EXPERIMENT_TYPES:
        raise ValueError(
            f"Unsupported experiment_type: {experiment_type}. "
            f"Supported: {sorted(SUPPORTED_EXPERIMENT_TYPES)}"
        )

    cases: list[dict[str, Any]] = []

    if experiment_type == "seed_stability":
        for seed in config.get("seeds", []):
            cases.append({
                "name": f"seed_{seed}",
                "seed": int(seed),
                "overrides": {},
            })

    elif experiment_type == "scale":
        for scale in config.get("scales", []):
            cases.append({
                "name": scale["name"],
                "overrides": {
                    "num_tasks": int(scale["num_tasks"]),
                    "num_uavs": int(scale["num_uavs"]),
                    "num_agvs": int(scale["num_agvs"]),
                },
            })

    elif experiment_type == "capacity":
        for scale_cfg in config.get("battery_scales", []):
            factor = scale_cfg.get("uav_capacity_factor", scale_cfg.get("battery_factor", 1.0))
            cases.append({
                "name": scale_cfg["name"],
                "capacity_factor": float(factor),
                "overrides": {},
            })

    elif experiment_type == "failure":
        for failure_cfg in config.get("failures", []):
            cases.append({
                "name": failure_cfg["name"],
                "runtime_events": failure_cfg.get("events", []),
                "overrides": {},
            })

    if not cases:
        raise ValueError(f"No cases found for experiment_type={experiment_type}")

    return cases


def build_run_config(
    base_config: dict[str, Any],
    case: dict[str, Any],
    experiment_type: str,
    default_seed: int | None,
) -> dict[str, Any]:
    """Build one concrete run config from base + case."""
    run_config = deepcopy(base_config)

    run_config.update(case.get("overrides", {}))

    if experiment_type == "seed_stability":
        run_config["seed"] = int(case["seed"])
    elif "seed" not in run_config:
        run_config["seed"] = int(default_seed if default_seed is not None else 42)

    return run_config


def apply_capacity_case(env, capacity_factor: float) -> None:
    """Apply UAV capacity perturbation by scaling range/endurance."""
    for uav in env.uavs:
        if hasattr(uav, "max_range"):
            uav.max_range *= capacity_factor
        if hasattr(uav, "max_endurance"):
            uav.max_endurance *= capacity_factor


def attach_failure_events(simulator, runtime_events: list[dict[str, Any]]) -> None:
    """Attach runtime failure events to simulator (consumption is TODO in simulator loop)."""
    setattr(simulator, "runtime_events", runtime_events)
    if runtime_events:
        print(f"[TODO] runtime_events attached but not yet consumed in Simulator.run: {runtime_events}")


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _nan_stat(values: list[float], op: str) -> float | None:
    arr = np.array(values, dtype=float)
    if arr.size == 0 or np.isnan(arr).all():
        return None
    if op == "mean":
        return float(np.nanmean(arr))
    if op == "std":
        return float(np.nanstd(arr))
    if op == "min":
        return float(np.nanmin(arr))
    if op == "max":
        return float(np.nanmax(arr))
    raise ValueError(f"Unsupported op: {op}")


def run_case(
    campaign_name: str,
    run_config: dict[str, Any],
    case: dict[str, Any],
    strategy: str,
    experiment_type: str,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """Run one case-strategy pair."""
    case_name = case["name"]
    seed = int(run_config.get("seed", 42))
    max_steps = int(run_config.get("max_steps", 100))

    print(
        f"\n=== {experiment_type} - Case: {case_name}, "
        f"Strategy: {strategy}, Seed: {seed} ==="
    )

    if dry_run:
        print(f"  [DRY-RUN] run_config={run_config}")
        print(
            "  [DRY-RUN] "
            f"max_steps={max_steps}, experiment_name={case_name}_{strategy}_seed{seed}"
        )
        return None

    env = build_environment(run_config)

    if experiment_type == "capacity":
        apply_capacity_case(env, float(case.get("capacity_factor", 1.0)))

    simulator = build_simulator(
        env,
        strategy,
        scenario_name=f"{experiment_type}_{case_name}_{strategy}",
        seed=seed,
    )

    if experiment_type == "failure":
        attach_failure_events(simulator, case.get("runtime_events", []))

    output_dir = simulator.run(
        max_steps=max_steps,
        experiment_name=f"{case_name}_{strategy}_seed{seed}",
        result_type=experiment_type,
        campaign_name=campaign_name,
    )

    metrics_file = Path(output_dir) / "metrics.json"
    if not metrics_file.exists():
        raise FileNotFoundError(f"metrics.json not found in {output_dir}")

    with metrics_file.open("r", encoding="utf-8") as file_obj:
        metrics = json.load(file_obj)

    completion_rate = _safe_float(metrics.get("completion_rate"), 0.0)
    failed_tasks = int(metrics.get("failed_tasks", 0))
    initial_task_count = int(metrics.get("total_tasks", 0))
    completed_tasks = int(metrics.get("completed_tasks", 0))
    task_failure_rate = failed_tasks / initial_task_count if initial_task_count > 0 else 0.0
    on_time_rate = _safe_float(metrics.get("on_time_rate"), 0.0)
    if 'on_time_rate' not in metrics:
        print(f"[WARNING] on_time_rate not found in metrics for case {case_name}, strategy {strategy}")

    return {
        "experiment_type": experiment_type,
        "case_name": case_name,
        "strategy": strategy,
        "seed": seed,
        "initial_task_count": initial_task_count,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "completion_rate": completion_rate,
        "task_failure_rate": task_failure_rate,
        "total_energy": _safe_float(metrics.get("total_energy"), 0.0),
        "avg_energy_per_task": metrics.get("avg_energy_per_task"),
        "avg_wait_time_at_relay": metrics.get("avg_wait_time_at_relay"),
        "on_time_rate": on_time_rate,
        "run_dir": output_dir,
    }


def generate_summary(campaign_name: str, all_results: list[dict[str, Any]]) -> None:
    """Generate run-level and grouped summary files."""
    summary_dir = create_robustness_summary_layout(campaign_name)

    detail_fields = [
        "experiment_type",
        "case_name",
        "strategy",
        "seed",
        "initial_task_count",
        "completed_tasks",
        "failed_tasks",
        "completion_rate",
        "task_failure_rate",
        "total_energy",
        "avg_energy_per_task",
        "avg_wait_time_at_relay",
        "on_time_rate",
        "run_dir",
    ]

    csv_file = summary_dir / "robustness_runs.csv"
    with csv_file.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=detail_fields)
        writer.writeheader()
        for result in all_results:
            writer.writerow({key: result.get(key, "") for key in detail_fields})

    json_file = summary_dir / "robustness_runs.json"
    with json_file.open("w", encoding="utf-8") as file_obj:
        json.dump(all_results, file_obj, indent=2, ensure_ascii=False)

    # 计算退化率
    degradation_data = []
    # 按 experiment_type + strategy 分组
    exp_strategies: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for result in all_results:
        key = (result["experiment_type"], result["strategy"])
        exp_strategies.setdefault(key, []).append(result)

    for (exp_type, strategy), results in exp_strategies.items():
        # 找到 normal case
        normal_result = None
        if exp_type == "capacity":
            normal_result = next((r for r in results if r["case_name"] == "normal"), None)
        elif exp_type == "failure":
            normal_result = next((r for r in results if r["case_name"] == "no_failure"), None)

        if normal_result:
            normal_completion = _safe_float(normal_result.get("completion_rate"), 0.0)
            normal_energy = _safe_float(normal_result.get("total_energy"), 0.0)
            normal_wait = _safe_float(normal_result.get("avg_wait_time_at_relay"), 0.0)

            for result in results:
                if result["case_name"] == "normal" or result["case_name"] == "no_failure":
                    continue
                
                completion = _safe_float(result.get("completion_rate"), 0.0)
                energy = _safe_float(result.get("total_energy"), 0.0)
                wait = _safe_float(result.get("avg_wait_time_at_relay"), 0.0)

                completion_drop = 0.0
                energy_increase = 0.0
                wait_increase = 0.0

                if normal_completion > 0:
                    completion_drop = (normal_completion - completion) / normal_completion
                if normal_energy > 0:
                    energy_increase = (energy - normal_energy) / normal_energy
                if normal_wait > 0:
                    wait_increase = (wait - normal_wait) / normal_wait

                degradation_data.append({
                    "experiment_type": exp_type,
                    "case_name": result["case_name"],
                    "strategy": strategy,
                    "completion_drop": completion_drop,
                    "energy_increase": energy_increase,
                    "wait_increase": wait_increase,
                })

    # 生成统计文件
    stats_file = summary_dir / "robustness_stats.csv"
    with stats_file.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(
            [
                "experiment_type",
                "case_name",
                "strategy",
                "mean_completion_rate",
                "std_completion_rate",
                "min_completion_rate",
                "max_completion_rate",
                "mean_total_energy",
                "std_total_energy",
                "mean_avg_energy_per_task",
                "std_avg_energy_per_task",
                "mean_avg_wait_time",
                "std_avg_wait_time",
                "run_failure_rate",
                "task_failure_rate_mean",
                "task_failure_rate_std",
                "n",
            ]
        )

        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for result in all_results:
            key = (result["experiment_type"], result["case_name"], result["strategy"])
            groups.setdefault(key, []).append(result)

        for (experiment_type, case_name, strategy), group_results in groups.items():
            completion = [_safe_float(item.get("completion_rate"), 0.0) for item in group_results]
            total_energy = [_safe_float(item.get("total_energy"), 0.0) for item in group_results]

            avg_energy = [
                np.nan if item.get("avg_energy_per_task") is None else float(item["avg_energy_per_task"])
                for item in group_results
            ]
            avg_wait = [
                np.nan if item.get("avg_wait_time_at_relay") is None else float(item["avg_wait_time_at_relay"])
                for item in group_results
            ]

            # 计算任务失败率
            task_failure_rates = [item.get("task_failure_rate", 0.0) for item in group_results]
            
            # 计算运行失败率（这里简化为检查是否有异常数据，如缺失关键字段）
            run_failure_count = sum(1 for item in group_results if item.get("initial_task_count") is None or item.get("completed_tasks") is None)
            run_failure_rate = run_failure_count / len(group_results) if group_results else 0.0

            writer.writerow(
                [
                    experiment_type,
                    case_name,
                    strategy,
                    _nan_stat(completion, "mean"),
                    _nan_stat(completion, "std"),
                    _nan_stat(completion, "min"),
                    _nan_stat(completion, "max"),
                    _nan_stat(total_energy, "mean"),
                    _nan_stat(total_energy, "std"),
                    _nan_stat(avg_energy, "mean"),
                    _nan_stat(avg_energy, "std"),
                    _nan_stat(avg_wait, "mean"),
                    _nan_stat(avg_wait, "std"),
                    run_failure_rate,
                    _nan_stat(task_failure_rates, "mean"),
                    _nan_stat(task_failure_rates, "std"),
                    len(group_results),
                ]
            )

    # 生成退化率文件
    if degradation_data:
        degradation_file = summary_dir / "robustness_degradation.csv"
        with degradation_file.open("w", newline="", encoding="utf-8") as file_obj:
            writer = csv.writer(file_obj)
            writer.writerow([
                "experiment_type",
                "case_name",
                "strategy",
                "completion_drop",
                "energy_increase",
                "wait_increase",
            ])
            for data in degradation_data:
                writer.writerow([
                    data["experiment_type"],
                    data["case_name"],
                    data["strategy"],
                    data["completion_drop"],
                    data["energy_increase"],
                    data["wait_increase"],
                ])
        print(f"Degradation CSV: {degradation_file}")

    print("\n=== Summary Generated ===")
    print(f"Detail CSV: {csv_file}")
    print(f"Detail JSON: {json_file}")
    print(f"Stats CSV: {stats_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run robustness experiments")
    parser.add_argument("--config", type=str, required=True, help="Robustness config file path")
    parser.add_argument("--campaign-name", type=str, default="default", help="Campaign name")
    parser.add_argument("--dry-run", action="store_true", help="Expand cases and print plan only")
    args = parser.parse_args()

    config = load_campaign_config(args.config)
    experiment_type = config.get("experiment_type")

    if experiment_type not in SUPPORTED_EXPERIMENT_TYPES:
        raise ValueError(
            f"Unsupported experiment_type: {experiment_type}. "
            f"Supported: {sorted(SUPPORTED_EXPERIMENT_TYPES)}"
        )

    strategies = config.get("strategies", DEFAULT_STRATEGIES)
    base_config = config.get("base_config", {})
    default_seed = config.get("seed")

    cases = normalize_cases(config)

    all_results: list[dict[str, Any]] = []
    expected_total = len(cases) * len(strategies)

    print("\n=== Robustness Plan ===")
    print(f"Experiment Type: {experiment_type}")
    print(f"Strategies: {strategies}")
    print(f"Cases: {[case['name'] for case in cases]}")
    print(f"Expected Runs: {expected_total}")

    for case in cases:
        for strategy in strategies:
            run_config = build_run_config(base_config, case, experiment_type, default_seed)
            result = run_case(
                args.campaign_name,
                run_config,
                case,
                strategy,
                experiment_type,
                dry_run=args.dry_run,
            )
            if result is not None:
                all_results.append(result)

    if args.dry_run:
        print("\n=== DRY-RUN Complete ===")
        return

    actual_total = len(all_results)
    if actual_total != expected_total:
        raise ValueError(f"Expected {expected_total} total results, got {actual_total}")

    generate_summary(args.campaign_name, all_results)

    print("\n=== Robustness Experiment Complete ===")
    print(f"Results saved to: results/robustness/{args.campaign_name}")


if __name__ == "__main__":
    main()
