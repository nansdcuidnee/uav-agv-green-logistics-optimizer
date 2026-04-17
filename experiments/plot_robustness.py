#!/usr/bin/env python3
"""Generate robustness experiment plots."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_results(summary_dir: Path):
    """Load robustness results from CSV/JSON."""
    runs_file = summary_dir / "robustness_runs.csv"
    stats_file = summary_dir / "robustness_stats.csv"

    runs = []
    if runs_file.exists():
        with runs_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                runs.append(row)

    stats = []
    if stats_file.exists():
        with stats_file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats.append(row)

    return runs, stats


def plot_seed_errorbar(stats, output_dir: Path):
    """Plot seed stability error bar chart."""
    seed_stats = [s for s in stats if s["experiment_type"] == "seed_stability"]
    if not seed_stats:
        return

    strategies = sorted({s["strategy"] for s in seed_stats})
    case_names = sorted({s["case_name"] for s in seed_stats})

    # 按策略分组
    strategy_data = {}
    for strategy in strategies:
        strategy_data[strategy] = {
            "means": [],
            "stds": [],
            "cases": []
        }

    for stat in seed_stats:
        strategy = stat["strategy"]
        mean = float(stat["mean_completion_rate"])
        std = float(stat["std_completion_rate"])
        case = stat["case_name"]

        strategy_data[strategy]["means"].append(mean)
        strategy_data[strategy]["stds"].append(std)
        strategy_data[strategy]["cases"].append(case)

    # 绘制误差棒图
    plt.figure(figsize=(12, 6))
    x = np.arange(len(case_names))
    width = 0.25

    for i, (strategy, data) in enumerate(strategy_data.items()):
        plt.bar(
            x + i * width,
            data["means"],
            width=width,
            yerr=data["stds"],
            label=strategy,
            capsize=5
        )

    plt.xlabel("Seed")
    plt.ylabel("Completion Rate")
    plt.title("Seed Stability - Completion Rate with Std Dev")
    plt.xticks(x + width, case_names, rotation=45)
    plt.legend()
    plt.tight_layout()

    output_file = output_dir / "seed_stability_errorbar.png"
    plt.savefig(output_file)
    plt.close()
    print(f"Saved seed stability errorbar plot: {output_file}")


def plot_seed_boxplot(runs, output_dir: Path):
    """Plot seed stability boxplot."""
    seed_runs = [r for r in runs if r["experiment_type"] == "seed_stability"]
    if not seed_runs:
        return

    strategies = sorted({r["strategy"] for r in seed_runs})

    # 按策略收集数据
    strategy_data = {}
    for strategy in strategies:
        strategy_data[strategy] = []

    for run in seed_runs:
        strategy = run["strategy"]
        completion = float(run["completion_rate"])
        strategy_data[strategy].append(completion)

    # 绘制箱线图
    plt.figure(figsize=(10, 6))
    data = [strategy_data[s] for s in strategies]
    plt.boxplot(data, labels=strategies)
    plt.xlabel("Strategy")
    plt.ylabel("Completion Rate")
    plt.title("Seed Stability - Completion Rate Distribution")
    plt.tight_layout()

    output_file = output_dir / "seed_stability_boxplot.png"
    plt.savefig(output_file)
    plt.close()
    print(f"Saved seed stability boxplot: {output_file}")


def plot_scale_line(stats, output_dir: Path):
    """Plot scale scalability line chart."""
    scale_stats = [s for s in stats if s["experiment_type"] == "scale"]
    if not scale_stats:
        return

    strategies = sorted({s["strategy"] for s in scale_stats})
    case_names = sorted({s["case_name"] for s in scale_stats}, key=lambda x: int(x.split("_")[1]))

    # 按策略分组
    strategy_data = {}
    for strategy in strategies:
        strategy_data[strategy] = {
            "completion": [],
            "energy": []
        }

    for stat in scale_stats:
        strategy = stat["strategy"]
        case = stat["case_name"]
        completion = float(stat["mean_completion_rate"])
        energy = float(stat["mean_total_energy"])

        strategy_data[strategy]["completion"].append(completion)
        strategy_data[strategy]["energy"].append(energy)

    # 绘制完成率趋势
    plt.figure(figsize=(12, 6))
    for strategy, data in strategy_data.items():
        plt.plot(case_names, data["completion"], marker="o", label=strategy)

    plt.xlabel("Scale (Number of Tasks)")
    plt.ylabel("Completion Rate")
    plt.title("Scalability - Completion Rate Trend")
    plt.legend()
    plt.tight_layout()

    output_file = output_dir / "scale_completion_trend.png"
    plt.savefig(output_file)
    plt.close()
    print(f"Saved scale completion trend plot: {output_file}")

    # 绘制能耗趋势
    plt.figure(figsize=(12, 6))
    for strategy, data in strategy_data.items():
        plt.plot(case_names, data["energy"], marker="o", label=strategy)

    plt.xlabel("Scale (Number of Tasks)")
    plt.ylabel("Total Energy")
    plt.title("Scalability - Energy Consumption Trend")
    plt.legend()
    plt.tight_layout()

    output_file = output_dir / "scale_energy_trend.png"
    plt.savefig(output_file)
    plt.close()
    print(f"Saved scale energy trend plot: {output_file}")


def plot_failure_bar(stats, output_dir: Path):
    """Plot failure comparison bar chart."""
    failure_stats = [s for s in stats if s["experiment_type"] == "failure"]
    if not failure_stats:
        return

    strategies = sorted({s["strategy"] for s in failure_stats})
    case_names = sorted({s["case_name"] for s in failure_stats})

    # 按策略和case分组
    data = {}
    for strategy in strategies:
        data[strategy] = []

    for stat in failure_stats:
        strategy = stat["strategy"]
        completion = float(stat["mean_completion_rate"])
        data[strategy].append(completion)

    # 绘制对比柱状图
    plt.figure(figsize=(12, 6))
    x = np.arange(len(case_names))
    width = 0.25

    for i, (strategy, values) in enumerate(data.items()):
        plt.bar(x + i * width, values, width=width, label=strategy)

    plt.xlabel("Case")
    plt.ylabel("Completion Rate")
    plt.title("Failure Resistance - Completion Rate Comparison")
    plt.xticks(x + width, case_names)
    plt.legend()
    plt.tight_layout()

    output_file = output_dir / "failure_comparison.png"
    plt.savefig(output_file)
    plt.close()
    print(f"Saved failure comparison plot: {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate robustness experiment plots")
    parser.add_argument(
        "--campaign",
        type=str,
        required=True,
        help="Campaign name (results/robustness/<campaign>)")
    args = parser.parse_args()

    summary_dir = Path("results") / "robustness" / args.campaign / "summary"
    if not summary_dir.exists():
        print(f"Summary directory not found: {summary_dir}")
        return

    # 创建plots目录
    plots_dir = summary_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    # 加载数据
    runs, stats = load_results(summary_dir)

    if not runs or not stats:
        print("No results found")
        return

    # 生成图表
    plot_seed_errorbar(stats, plots_dir)
    plot_seed_boxplot(runs, plots_dir)
    plot_scale_line(stats, plots_dir)
    plot_failure_bar(stats, plots_dir)

    print("\n=== Plots Generated ===")
    print(f"All plots saved to: {plots_dir}")


if __name__ == "__main__":
    main()