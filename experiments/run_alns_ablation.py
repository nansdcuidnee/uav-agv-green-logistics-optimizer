
"""
ALNS ablation experiment runner.

Runs complete ALNS ablation experiments across multiple scenarios, random seeds, and ablation variants, automatically generating results tables suitable for paper/report analysis.
"""

import os
import sys
import json
import csv
import argparse
import traceback
import shutil
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.config_loader import load_config
from src.utils.simulator_helper import build_environment, build_simulator
from src.utils.result_layout import ResultLayout


# Define ablation variant configuration
@dataclass
class AblationVariant:
    name: str
    description: str
    strategy_kwargs: dict


def get_ablation_variants():
    """Get all ablation variant configurations."""
    variants = []
    
    # Complete method (baseline)
    variants.append(AblationVariant(
        name="unified_full",
        description="Complete ALNS Unified Strategy (baseline)",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": True,
            "destroy_operator_set": ["random_remove", "worst_remove", "high_energy_remove"],
            "repair_operator_set": ["greedy_insert", "regret_insert", "relay_aware_regret_insert"]
        }
    ))
    
    # Main ablation group
    variants.append(AblationVariant(
        name="direct_only",
        description="Direct only mode (relay disabled)",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": False,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": True
        }
    ))
    
    variants.append(AblationVariant(
        name="relay_only",
        description="Relay only mode (direct disabled)",
        strategy_kwargs={
            "allow_direct": False,
            "allow_relay": True,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": True
        }
    ))
    
    variants.append(AblationVariant(
        name="greedy_pool",
        description="Greedy candidate pool strategy",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "greedy_topk",
            "adaptive_operator_weights": True
        }
    ))
    
    variants.append(AblationVariant(
        name="random_pool",
        description="Random candidate pool strategy",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "random_topk",
            "adaptive_operator_weights": True
        }
    ))
    
    variants.append(AblationVariant(
        name="fixed_weights",
        description="Fixed operator weights (adaptive disabled)",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": False
        }
    ))
    
    variants.append(AblationVariant(
        name="simple_ops",
        description="Simple operator set",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": True,
            "destroy_operator_set": ["random_remove"],
            "repair_operator_set": ["greedy_insert"]
        }
    ))
    
    return variants


def get_ablation_config(variant_name):
    """Get ablation configuration by variant name."""
    for variant in get_ablation_variants():
        if variant.name == variant_name:
            return variant
    return None


def aggregate_results(results):
    """Aggregate results by scenario and variant."""
    grouped = defaultdict(list)
    
    for result in results:
        key = (result["scene_name"], result["variant_name"])
        grouped[key].append(result)
    
    aggregated = []
    for (scene_name, variant_name), group_results in grouped.items():
        aggregated_row = {
            "scene_name": scene_name,
            "variant_name": variant_name,
            "num_runs": len(group_results)
        }
        
        metrics = [
            "completion_rate",
            "total_energy",
            "avg_delivery_time",
            "avg_wait_time_at_relay",
            "relay_count",
            "direct_count",
            "fallback_count",
            "charging_count",
            "failed_tasks",
            "total_distance",
            "total_distance_uav",
            "total_distance_agv"
        ]
        
        for metric in metrics:
            values = [r[metric] for r in group_results if r[metric] is not None]
            if values:
                mean_val = sum(values) / len(values)
                if len(values) > 1:
                    std_val = (sum((x - mean_val) ** 2 for x in values) / len(values)) ** 0.5
                else:
                    std_val = 0.0
                aggregated_row[f"{metric}_mean"] = mean_val
                aggregated_row[f"{metric}_std"] = std_val
            else:
                aggregated_row[f"{metric}_mean"] = None
                aggregated_row[f"{metric}_std"] = None
        
        aggregated.append(aggregated_row)
    
    return aggregated


def build_comparison_vs_full(aggregate_rows):
    """Build comparison vs unified_full results."""
    scene_results = defaultdict(dict)
    for row in aggregate_rows:
        scene_results[row["scene_name"]][row["variant_name"]] = row
    
    comparisons = []
    for scene_name, scene_variants in scene_results.items():
        baseline = scene_variants.get("unified_full")
        if not baseline:
            continue
        
        for variant_name, variant_row in scene_variants.items():
            comparison_row = {
                "scene_name": scene_name,
                "variant_name": variant_name,
                "baseline_variant": "unified_full"
            }
            
            metrics = [
                ("completion_rate", float),
                ("total_energy", float),
                ("avg_delivery_time", float),
                ("fallback_count", float),
                ("charging_count", float)
            ]
            
            for metric, _ in metrics:
                baseline_val = baseline.get(f"{metric}_mean")
                variant_val = variant_row.get(f"{metric}_mean")
                
                if baseline_val is not None and variant_val is not None:
                    delta = variant_val - baseline_val
                    relative_delta = None
                    if abs(baseline_val) > 1e-9:
                        relative_delta = (variant_val - baseline_val) / baseline_val * 100.0
                    
                    comparison_row[f"{metric}_delta"] = delta
                    comparison_row[f"{metric}_relative_delta"] = relative_delta
                else:
                    comparison_row[f"{metric}_delta"] = None
                    comparison_row[f"{metric}_relative_delta"] = None
            
            comparisons.append(comparison_row)
    
    return comparisons


def load_metrics_from_dir(output_dir):
    """Load metrics.json from output directory."""
    metrics_file = os.path.join(output_dir, "metrics.json")
    if os.path.exists(metrics_file):
        with open(metrics_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def create_ablation_result_layout(
    output_base_dir,
    scene_name,
    variant_name,
    seed,
    ablation_timestamp
):
    """Create result layout for ablation experiment."""
    base_path = Path(output_base_dir) / f"alns_ablation_{ablation_timestamp}"
    runs_dir = base_path / "runs" / scene_name / f"{variant_name}_seed_{seed}"
    
    plots_dir = runs_dir / "plots"
    logs_dir = runs_dir / "logs"
    records_dir = runs_dir / "records"
    
    plots_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    records_dir.mkdir(parents=True, exist_ok=True)
    
    return ResultLayout(
        run_dir=runs_dir,
        plots_dir=plots_dir,
        logs_dir=logs_dir,
        records_dir=records_dir
    )


def run_single_experiment(
    config_path,
    variant,
    seed,
    max_steps,
    output_base_dir,
    ablation_timestamp
):
    """Run single ablation experiment."""
    config = load_config(config_path)
    config["random_seed"] = seed
    env = build_environment(config)
    scene_name = os.path.splitext(os.path.basename(config_path))[0]
    
    simulator = build_simulator(
        env,
        strategy_type="alns_unified",
        scenario_name=f"{variant.name}_seed_{seed}",
        seed=seed,
        strategy_kwargs=variant.strategy_kwargs
    )
    
    output_dir = simulator.run(max_steps=max_steps, experiment_name=f"{variant.name}_seed_{seed}")
    
    correct_layout = create_ablation_result_layout(
        output_base_dir,
        scene_name,
        variant.name,
        seed,
        ablation_timestamp
    )
    
    default_output_path = Path(output_dir)
    correct_output_path = correct_layout.run_dir
    
    for item in default_output_path.iterdir():
        dest = correct_output_path / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            if dest.exists():
                dest.unlink()
            shutil.copy2(item, dest)
    
    # Remove the default output directory to avoid duplication
    parent_dir = default_output_path.parent
    if parent_dir.exists() and parent_dir.name.endswith(f"_seed_{seed}"):
        shutil.rmtree(parent_dir)
    
    metrics = load_metrics_from_dir(str(correct_output_path))
    
    result = {
        "scene_name": scene_name,
        "config_path": config_path,
        "variant_name": variant.name,
        "seed": seed,
        "completion_rate": metrics.get("completion_rate"),
        "total_energy": metrics.get("total_energy"),
        "avg_delivery_time": metrics.get("avg_delivery_time"),
        "avg_wait_time_at_relay": metrics.get("avg_wait_time_at_relay"),
        "relay_count": metrics.get("relay_count"),
        "direct_count": metrics.get("direct_count"),
        "fallback_count": metrics.get("fallback_count"),
        "charging_count": metrics.get("charging_count"),
        "failed_tasks": metrics.get("failed_tasks"),
        "total_distance": metrics.get("total_distance"),
        "total_distance_uav": metrics.get("total_distance_uav"),
        "total_distance_agv": metrics.get("total_distance_agv"),
        "run_dir": str(correct_output_path)
    }
    
    return result


def save_run_level_results(results, output_dir):
    """Save run-level results to CSV."""
    csv_path = os.path.join(output_dir, "run_level_results.csv")
    fieldnames = [
        "scene_name", "config_path", "variant_name", "seed",
        "completion_rate", "total_energy", "avg_delivery_time",
        "avg_wait_time_at_relay", "relay_count", "direct_count",
        "fallback_count", "charging_count", "failed_tasks",
        "total_distance", "total_distance_uav", "total_distance_agv",
        "run_dir"
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print("Run-level results saved to:", csv_path)


def save_aggregated_results(aggregated, output_dir):
    """Save aggregated results to CSV."""
    csv_path = os.path.join(output_dir, "aggregate_by_variant.csv")
    if not aggregated:
        return
    
    fieldnames = list(aggregated[0].keys())
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in aggregated:
            writer.writerow(row)
    
    print("Aggregated results saved to:", csv_path)


def save_comparison_results(comparisons, output_dir):
    """Save comparison vs full results to CSV."""
    csv_path = os.path.join(output_dir, "comparison_vs_full.csv")
    if not comparisons:
        return
    
    fieldnames = list(comparisons[0].keys())
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in comparisons:
            writer.writerow(row)
    
    print("Comparison results saved to:", csv_path)


def save_metadata(
    config_paths,
    seeds,
    max_steps,
    variants,
    command_args,
    output_dir,
    timestamp
):
    """Save experiment metadata."""
    metadata = {
        "timestamp": timestamp,
        "configs": config_paths,
        "seeds": seeds,
        "max_steps": max_steps,
        "variants": [
            {"name": v.name, "description": v.description} for v in variants
        ],
        "command_args": command_args,
        "unsupported_optional_ablations": ["no_fallback", "no_charging_loop"],
        "note": "This file records the configuration of this ALNS ablation experiment, including scenarios, seeds, max_steps, and variant list."
    }
    
    metadata_file = os.path.join(output_dir, "metadata.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print("Metadata saved to:", metadata_file)


def save_summary(
    all_results,
    aggregated,
    comparisons,
    output_dir
):
    """Save summary data."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_runs": len(all_results),
        "results": all_results,
        "aggregated": aggregated,
        "comparisons": comparisons
    }
    
    summary_file = os.path.join(output_dir, "summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("Summary saved to:", summary_file)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="ALNS ablation experiment runner.")
    parser.add_argument("--config", type=str, default=None, help="Single scenario config (legacy)")
    parser.add_argument("--configs", type=str, nargs='+', default=[], help="Multiple scenario config files")
    parser.add_argument("--max-steps", type=int, default=500, help="Max simulation steps")
    parser.add_argument("--seeds", type=int, nargs='+', default=[42], help="Random seeds list")
    parser.add_argument("--output-dir", type=str, default="results/ablation", help="Output directory")
    
    args = parser.parse_args()
    
    config_paths = args.configs
    if args.config and not config_paths:
        config_paths = [args.config]
    
    if not config_paths:
        config_paths = [
            "configs/generated/pickup_delivery_generated.yaml",
            "configs/generated/scene_small.yaml",
            "configs/generated/scene_medium.yaml",
            "configs/generated/scene_large.yaml"
        ]
    
    valid_configs = []
    for cfg in config_paths:
        if os.path.exists(cfg):
            valid_configs.append(cfg)
        else:
            print("Warning: config file not found, skipping:", cfg)
    
    if not valid_configs:
        print("Error: no valid config files")
        return
    
    print("Using config files:", valid_configs)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(args.output_dir, f"alns_ablation_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    variants = get_ablation_variants()
    print("Ablation variants:", [v.name for v in variants])
    print("Random seeds:", args.seeds)
    print("Output directory:", output_dir)
    
    save_metadata(
        valid_configs, args.seeds, args.max_steps,
        variants, vars(args), output_dir, timestamp
    )
    
    all_results = []
    total_runs = len(valid_configs) * len(variants) * len(args.seeds)
    current_run = 0
    
    print("\nStarting ablation experiments, total runs:", total_runs)
    print("=" * 60)
    
    for config_path in valid_configs:
        scene_name = os.path.splitext(os.path.basename(config_path))[0]
        print("\nScenario:", scene_name)
        
        for variant in variants:
            print("  Variant:", variant.name)
            
            for seed in args.seeds:
                current_run += 1
                print(f"    Run {current_run}/{total_runs} (seed={seed})...", end="", flush=True)
                
                try:
                    result = run_single_experiment(
                        config_path, variant, seed, args.max_steps,
                        args.output_dir, timestamp
                    )
                    all_results.append(result)
                    print(" OK")
                except Exception as e:
                    print(" ERROR")
                    print(f"      Error:", str(e))
                    traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Aggregating results...")
    aggregated = aggregate_results(all_results)
    comparisons = build_comparison_vs_full(aggregated)
    
    print("\nSaving results...")
    save_run_level_results(all_results, output_dir)
    save_aggregated_results(aggregated, output_dir)
    save_comparison_results(comparisons, output_dir)
    save_summary(all_results, aggregated, comparisons, output_dir)
    
    # 自动生成论文用图
    print("\nGenerating figures...")
    try:
        # 导入绘图模块
        from scripts.plot_ablation_summary import generate_figures_from_csv
        generate_figures_from_csv(Path(output_dir))
    except Exception as e:
        print(f"Warning: Failed to generate figures: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("ALNS ablation experiments complete!")
    print("Results saved to:", output_dir)


if __name__ == "__main__":
    main()

