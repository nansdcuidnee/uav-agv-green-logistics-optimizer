"""
ALNS 消融实验结果可视化脚本

读取实验结果目录下的 metrics.json 文件，生成汇总图表。

用法：
    python scripts/plot_ablation_summary.py results/ablation/alns_ablation_<timestamp>

输出：
    - completion_rate_by_variant.png
    - total_energy_by_variant.png
    - avg_delivery_time_by_variant.png
    - relay_direct_count_by_variant.png
    - comparison_vs_full_energy_delta.png
    - comparison_vs_full_completion_delta.png
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def load_metrics_from_dir(run_dir: Path) -> Dict[str, Any]:
    """从运行目录加载 metrics.json"""
    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def collect_run_results(ablation_dir: Path) -> List[Dict[str, Any]]:
    """
    从实验目录收集所有运行结果
    
    Args:
        ablation_dir: 实验结果根目录，如 results/ablation/alns_ablation_20260605_xxx
    
    Returns:
        包含所有运行结果的列表
    """
    results = []
    runs_dir = ablation_dir / "runs"
    
    if not runs_dir.exists():
        print(f"警告：未找到 runs 目录: {runs_dir}")
        return results
    
    for scene_dir in runs_dir.iterdir():
        if not scene_dir.is_dir():
            continue
        scene_name = scene_dir.name
        
        for run_dir in scene_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            # 解析 variant_name 和 seed
            parts = run_dir.name.split("_seed_")
            if len(parts) != 2:
                continue
            variant_name = parts[0]
            try:
                seed = int(parts[1])
            except ValueError:
                continue
            
            # 加载 metrics
            metrics = load_metrics_from_dir(run_dir)
            if not metrics:
                continue
            
            # 构建结果记录
            result = {
                "scene_name": scene_name,
                "variant_name": variant_name,
                "seed": seed,
                "run_dir": str(run_dir),
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
            }
            results.append(result)
    
    return results


def aggregate_results(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    按 scene + variant 聚合结果，计算均值和标准差
    
    Args:
        results: 单次运行结果列表
    
    Returns:
        聚合后的 DataFrame
    """
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # 需要聚合的数值指标
    numeric_cols = [
        "completion_rate", "total_energy", "avg_delivery_time",
        "avg_wait_time_at_relay", "relay_count", "direct_count",
        "fallback_count", "charging_count", "failed_tasks",
        "total_distance", "total_distance_uav", "total_distance_agv"
    ]
    
    # 按 scene + variant 分组聚合
    agg_dict = {}
    for col in numeric_cols:
        if col in df.columns:
            agg_dict[f"{col}_mean"] = (col, "mean")
            agg_dict[f"{col}_std"] = (col, "std")
    
    if agg_dict:
        grouped = df.groupby(["scene_name", "variant_name"]).agg(**agg_dict)
        grouped = grouped.reset_index()
        return grouped
    else:
        return pd.DataFrame()


def build_comparison_vs_full(aggregate_df: pd.DataFrame) -> pd.DataFrame:
    """
    构建与 unified_full 的对比结果
    
    Args:
        aggregate_df: 聚合后的结果 DataFrame
    
    Returns:
        对比结果 DataFrame
    """
    if aggregate_df.empty:
        return pd.DataFrame()
    
    comparisons = []
    
    for scene in aggregate_df["scene_name"].unique():
        scene_data = aggregate_df[aggregate_df["scene_name"] == scene]
        
        # 获取 unified_full 的数据
        full_data = scene_data[scene_data["variant_name"] == "unified_full"]
        if full_data.empty:
            continue
        
        full_row = full_data.iloc[0]
        
        # 对每个消融变体与 unified_full 比较
        for _, row in scene_data.iterrows():
            variant_name = row["variant_name"]
            if variant_name == "unified_full":
                continue
            
            comparison = {
                "scene_name": scene,
                "variant_name": variant_name,
                "baseline_variant": "unified_full",
            }
            
            # 计算 delta 和 relative_delta
            metrics_to_compare = [
                "completion_rate", "total_energy", "avg_delivery_time",
                "fallback_count", "charging_count", "relay_count", "direct_count"
            ]
            
            for metric in metrics_to_compare:
                mean_col = f"{metric}_mean"
                if mean_col in row and mean_col in full_row:
                    ablation_val = row[mean_col]
                    full_val = full_row[mean_col]
                    
                    # 计算 delta
                    delta = ablation_val - full_val if pd.notna(ablation_val) and pd.notna(full_val) else None
                    comparison[f"{metric}_delta"] = delta
                    
                    # 计算 relative_delta (百分比)
                    if pd.notna(ablation_val) and pd.notna(full_val) and full_val != 0:
                        comparison[f"{metric}_relative_delta"] = (delta / full_val) * 100
                    else:
                        comparison[f"{metric}_relative_delta"] = None
            
            comparisons.append(comparison)
    
    return pd.DataFrame(comparisons)


def save_csv_outputs(ablation_dir: Path, run_results: List[Dict], aggregate_df: pd.DataFrame, comparison_df: pd.DataFrame):
    """保存 CSV 输出文件"""
    # run_level_results.csv
    if run_results:
        run_df = pd.DataFrame(run_results)
        run_df.to_csv(ablation_dir / "run_level_results.csv", index=False)
        print(f"已保存: {ablation_dir / 'run_level_results.csv'}")
    
    # aggregate_by_variant.csv
    if not aggregate_df.empty:
        aggregate_df.to_csv(ablation_dir / "aggregate_by_variant.csv", index=False)
        print(f"已保存: {ablation_dir / 'aggregate_by_variant.csv'}")
    
    # comparison_vs_full.csv
    if not comparison_df.empty:
        comparison_df.to_csv(ablation_dir / "comparison_vs_full.csv", index=False)
        print(f"已保存: {ablation_dir / 'comparison_vs_full.csv'}")


def plot_completion_rate_by_variant(aggregate_df: pd.DataFrame, output_dir: Path):
    """绘制各变体完成率对比图"""
    if aggregate_df.empty or "completion_rate_mean" not in aggregate_df.columns:
        print("警告：缺少 completion_rate 数据，跳过该图")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    scenes = aggregate_df["scene_name"].unique()
    variants = aggregate_df["variant_name"].unique()
    x = np.arange(len(variants))
    width = 0.8 / len(scenes)
    
    for i, scene in enumerate(scenes):
        scene_data = aggregate_df[aggregate_df["scene_name"] == scene]
        means = []
        stds = []
        for variant in variants:
            var_data = scene_data[scene_data["variant_name"] == variant]
            if not var_data.empty:
                means.append(var_data["completion_rate_mean"].values[0] * 100)  # 转为百分比
                stds.append(var_data["completion_rate_std"].values[0] * 100 if "completion_rate_std" in var_data.columns else 0)
            else:
                means.append(0)
                stds.append(0)
        
        offset = (i - len(scenes)/2 + 0.5) * width
        bars = ax.bar(x + offset, means, width, label=scene, yerr=stds, capsize=3, alpha=0.8)
    
    ax.set_xlabel("Variant")
    ax.set_ylabel("Completion Rate (%)")
    ax.set_title("Completion Rate by Variant")
    ax.set_xticks(x)
    ax.set_xticklabels(variants, rotation=45, ha="right")
    ax.legend(title="Scene", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    
    # 添加 100% 参考线
    ax.axhline(y=100, color="red", linestyle="--", alpha=0.5, label="100%")
    
    plt.tight_layout()
    output_path = output_dir / "completion_rate_by_variant.png"
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"已保存: {output_path}")


def plot_total_energy_by_variant(aggregate_df: pd.DataFrame, output_dir: Path):
    """绘制各变体总能耗对比图"""
    if aggregate_df.empty or "total_energy_mean" not in aggregate_df.columns:
        print("警告：缺少 total_energy 数据，跳过该图")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    scenes = aggregate_df["scene_name"].unique()
    variants = aggregate_df["variant_name"].unique()
    x = np.arange(len(variants))
    width = 0.8 / len(scenes)
    
    for i, scene in enumerate(scenes):
        scene_data = aggregate_df[aggregate_df["scene_name"] == scene]
        means = []
        stds = []
        for variant in variants:
            var_data = scene_data[scene_data["variant_name"] == variant]
            if not var_data.empty:
                means.append(var_data["total_energy_mean"].values[0])
                stds.append(var_data["total_energy_std"].values[0] if "total_energy_std" in var_data.columns else 0)
            else:
                means.append(0)
                stds.append(0)
        
        offset = (i - len(scenes)/2 + 0.5) * width
        bars = ax.bar(x + offset, means, width, label=scene, yerr=stds, capsize=3, alpha=0.8)
    
    ax.set_xlabel("Variant")
    ax.set_ylabel("Total Energy")
    ax.set_title("Total Energy by Variant")
    ax.set_xticks(x)
    ax.set_xticklabels(variants, rotation=45, ha="right")
    ax.legend(title="Scene", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / "total_energy_by_variant.png"
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"已保存: {output_path}")


def plot_avg_delivery_time_by_variant(aggregate_df: pd.DataFrame, output_dir: Path):
    """绘制各变体平均配送时间对比图"""
    if aggregate_df.empty or "avg_delivery_time_mean" not in aggregate_df.columns:
        print("警告：缺少 avg_delivery_time 数据，跳过该图")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    scenes = aggregate_df["scene_name"].unique()
    variants = aggregate_df["variant_name"].unique()
    x = np.arange(len(variants))
    width = 0.8 / len(scenes)
    
    for i, scene in enumerate(scenes):
        scene_data = aggregate_df[aggregate_df["scene_name"] == scene]
        means = []
        stds = []
        for variant in variants:
            var_data = scene_data[scene_data["variant_name"] == variant]
            if not var_data.empty:
                means.append(var_data["avg_delivery_time_mean"].values[0])
                stds.append(var_data["avg_delivery_time_std"].values[0] if "avg_delivery_time_std" in var_data.columns else 0)
            else:
                means.append(0)
                stds.append(0)
        
        offset = (i - len(scenes)/2 + 0.5) * width
        bars = ax.bar(x + offset, means, width, label=scene, yerr=stds, capsize=3, alpha=0.8)
    
    ax.set_xlabel("Variant")
    ax.set_ylabel("Average Delivery Time")
    ax.set_title("Average Delivery Time by Variant")
    ax.set_xticks(x)
    ax.set_xticklabels(variants, rotation=45, ha="right")
    ax.legend(title="Scene", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / "avg_delivery_time_by_variant.png"
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"已保存: {output_path}")


def plot_relay_direct_count_by_variant(aggregate_df: pd.DataFrame, output_dir: Path):
    """绘制各变体中继/直送次数对比图"""
    if aggregate_df.empty:
        print("警告：缺少 relay/direct 数据，跳过该图")
        return
    
    has_relay = "relay_count_mean" in aggregate_df.columns
    has_direct = "direct_count_mean" in aggregate_df.columns
    
    if not has_relay and not has_direct:
        print("警告：缺少 relay_count 和 direct_count 数据，跳过该图")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    variants = aggregate_df["variant_name"].unique()
    x = np.arange(len(variants))
    width = 0.35
    
    # relay_count 图
    if has_relay:
        relay_means = []
        relay_stds = []
        for variant in variants:
            var_data = aggregate_df[aggregate_df["variant_name"] == variant]
            if not var_data.empty:
                relay_means.append(var_data["relay_count_mean"].values[0])
                relay_stds.append(var_data["relay_count_std"].values[0] if "relay_count_std" in var_data.columns else 0)
            else:
                relay_means.append(0)
                relay_stds.append(0)
        ax1.bar(x, relay_means, width, label="Relay Count", yerr=relay_stds, capsize=3, alpha=0.8, color="steelblue")
        ax1.set_xlabel("Variant")
        ax1.set_ylabel("Relay Count")
        ax1.set_title("Relay Count by Variant")
        ax1.set_xticks(x)
        ax1.set_xticklabels(variants, rotation=45, ha="right")
        ax1.grid(axis="y", alpha=0.3)
    
    # direct_count 图
    if has_direct:
        direct_means = []
        direct_stds = []
        for variant in variants:
            var_data = aggregate_df[aggregate_df["variant_name"] == variant]
            if not var_data.empty:
                direct_means.append(var_data["direct_count_mean"].values[0])
                direct_stds.append(var_data["direct_count_std"].values[0] if "direct_count_std" in var_data.columns else 0)
            else:
                direct_means.append(0)
                direct_stds.append(0)
        ax2.bar(x, direct_means, width, label="Direct Count", yerr=direct_stds, capsize=3, alpha=0.8, color="coral")
        ax2.set_xlabel("Variant")
        ax2.set_ylabel("Direct Count")
        ax2.set_title("Direct Count by Variant")
        ax2.set_xticks(x)
        ax2.set_xticklabels(variants, rotation=45, ha="right")
        ax2.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / "relay_direct_count_by_variant.png"
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"已保存: {output_path}")


def plot_comparison_vs_full_energy_delta(comparison_df: pd.DataFrame, output_dir: Path):
    """绘制与 unified_full 对比的能耗差值图"""
    if comparison_df.empty or "total_energy_delta" not in comparison_df.columns:
        print("警告：缺少 total_energy_delta 数据，跳过该图")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    scenes = comparison_df["scene_name"].unique()
    variants = comparison_df[comparison_df["variant_name"] != "unified_full"]["variant_name"].unique()
    
    x = np.arange(len(variants))
    width = 0.8 / len(scenes)
    
    for i, scene in enumerate(scenes):
        scene_data = comparison_df[comparison_df["scene_name"] == scene]
        deltas = []
        for variant in variants:
            var_data = scene_data[scene_data["variant_name"] == variant]
            if not var_data.empty:
                delta = var_data["total_energy_delta"].values[0]
                deltas.append(delta if pd.notna(delta) else 0)
            else:
                deltas.append(0)
        
        offset = (i - len(scenes)/2 + 0.5) * width
        ax.bar(x + offset, deltas, width, label=scene, alpha=0.8)
    
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.8)
    ax.set_xlabel("Variant (vs unified_full)")
    ax.set_ylabel("Energy Delta")
    ax.set_title("Total Energy Delta vs unified_full")
    ax.set_xticks(x)
    ax.set_xticklabels(variants, rotation=45, ha="right")
    ax.legend(title="Scene", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / "comparison_vs_full_energy_delta.png"
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"已保存: {output_path}")


def plot_comparison_vs_full_completion_delta(comparison_df: pd.DataFrame, output_dir: Path):
    """绘制与 unified_full 对比的完成率差值图"""
    if comparison_df.empty or "completion_rate_delta" not in comparison_df.columns:
        print("警告：缺少 completion_rate_delta 数据，跳过该图")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    scenes = comparison_df["scene_name"].unique()
    variants = comparison_df[comparison_df["variant_name"] != "unified_full"]["variant_name"].unique()
    
    x = np.arange(len(variants))
    width = 0.8 / len(scenes)
    
    for i, scene in enumerate(scenes):
        scene_data = comparison_df[comparison_df["scene_name"] == scene]
        deltas = []
        for variant in variants:
            var_data = scene_data[scene_data["variant_name"] == variant]
            if not var_data.empty:
                delta = var_data["completion_rate_delta"].values[0]
                # 转为百分比
                deltas.append(delta * 100 if pd.notna(delta) else 0)
            else:
                deltas.append(0)
        
        offset = (i - len(scenes)/2 + 0.5) * width
        ax.bar(x + offset, deltas, width, label=scene, alpha=0.8)
    
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.8)
    ax.set_xlabel("Variant (vs unified_full)")
    ax.set_ylabel("Completion Rate Delta (%)")
    ax.set_title("Completion Rate Delta vs unified_full")
    ax.set_xticks(x)
    ax.set_xticklabels(variants, rotation=45, ha="right")
    ax.legend(title="Scene", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / "comparison_vs_full_completion_delta.png"
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"已保存: {output_path}")


def main():
    # 解析命令行参数
    if len(sys.argv) < 2:
        print("用法: python scripts/plot_ablation_summary.py <ablation_result_dir>")
        print("示例: python scripts/plot_ablation_summary.py results/ablation/alns_ablation_20260605_210233（异常排查记录）")
        sys.exit(1)
    
    ablation_dir = Path(sys.argv[1])
    
    if not ablation_dir.exists():
        print(f"错误：目录不存在: {ablation_dir}")
        sys.exit(1)
    
    print(f"读取实验结果目录: {ablation_dir}")
    
    # 1. 收集所有运行结果
    print("\n[1/6] 收集运行结果...")
    run_results = collect_run_results(ablation_dir)
    print(f"找到 {len(run_results)} 条运行记录")
    
    if not run_results:
        print("错误：未找到任何运行结果")
        sys.exit(1)
    
    # 2. 聚合结果
    print("\n[2/6] 聚合结果...")
    aggregate_df = aggregate_results(run_results)
    print(f"聚合后 {len(aggregate_df)} 条记录")
    
    # 3. 构建与 unified_full 的对比
    print("\n[3/6] 构建对比结果...")
    comparison_df = build_comparison_vs_full(aggregate_df)
    print(f"生成 {len(comparison_df)} 条对比记录")
    
    # 4. 保存 CSV 文件
    print("\n[4/6] 保存 CSV 文件...")
    save_csv_outputs(ablation_dir, run_results, aggregate_df, comparison_df)
    
    # 5. 创建输出目录
    output_dir = ablation_dir / "plots_summary"
    output_dir.mkdir(exist_ok=True)
    print(f"\n图表将保存到: {output_dir}")
    
    # 6. 生成图表
    print("\n[5/6] 生成图表...")
    plot_completion_rate_by_variant(aggregate_df, output_dir)
    plot_total_energy_by_variant(aggregate_df, output_dir)
    plot_avg_delivery_time_by_variant(aggregate_df, output_dir)
    plot_relay_direct_count_by_variant(aggregate_df, output_dir)
    plot_comparison_vs_full_energy_delta(comparison_df, output_dir)
    plot_comparison_vs_full_completion_delta(comparison_df, output_dir)
    
    print("\n[6/6] 完成！")
    print(f"\n图表已保存到: {output_dir}")
    print("\n生成的图表文件:")
    for f in sorted(output_dir.glob("*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()
