"""UAV-AGV协同绿色配送优化系统 - 在线演示页面"""

import streamlit as st
import json
import os
from pathlib import Path
import pandas as pd
from PIL import Image
import base64

st.set_page_config(
    page_title="UAV-AGV协同配送优化系统",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)


def find_latest_run_dir():
    """查找最新的单次运行目录"""
    runs_root = Path("results/runs")
    if not runs_root.exists():
        return None
    all_runs = []
    for scene_dir in runs_root.iterdir():
        if scene_dir.is_dir():
            for run_dir in scene_dir.iterdir():
                if run_dir.is_dir() and run_dir.name.startswith("202"):
                    all_runs.append(run_dir)
    if not all_runs:
        return None
    return sorted(all_runs, key=lambda x: x.stat().st_mtime, reverse=True)[0]


def find_latest_ablation_dir():
    """查找最新的消融实验目录"""
    ablation_root = Path("results/ablation")
    if not ablation_root.exists():
        return None
    all_dirs = []
    for d in ablation_root.iterdir():
        if d.is_dir() and d.name.startswith("alns_ablation_"):
            all_dirs.append(d)
    if not all_dirs:
        return None
    return sorted(all_dirs, key=lambda x: x.stat().st_mtime, reverse=True)[0]


def load_json(path):
    """安全加载JSON文件"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def load_csv(path):
    """安全加载CSV文件"""
    try:
        return pd.read_csv(path)
    except:
        return None


def render_homepage():
    """渲染首页"""
    st.title("🚁 UAV-AGV协同绿色配送优化系统")
    st.markdown("### 基于自适应大规模邻域搜索的无人机-无人车协同配送优化")

    st.markdown("---")
    st.markdown("## 📋 项目简介")
    st.info("""
    本项目是一个面向低空物流配送的能耗与碳效优化仿真平台，支持空地协同配送场景下的：
    - 能耗建模与碳效评估
    - 直送/中继统一决策
    - 自适应大规模邻域搜索优化

    适用场景：城市末端配送、园区物流、应急物资运输等
    """)

    st.markdown("## ✨ 核心技术亮点")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🛸 UAV-AGV协同配送\n- 无人机负责快速配送\n- 无人车提供中继支撑\n- 动态选择最优配送模式")
    with col2:
        st.markdown("### 🌱 绿色配送优化\n- 能耗模型精确计算\n- 碳排放量化评估\n- 时间-能耗多目标权衡")
    with col3:
        st.markdown("### 🔬 ALNS优化算法\n- 候选池统一构建\n- 自适应算子权重\n- 模拟退火全局搜索")

    st.markdown("---")
    st.markdown("## 📦 配送模式说明")
    mode_col1, mode_col2 = st.columns(2)
    with mode_col1:
        st.markdown("### ✈️ 直接配送模式\n路径：UAV当前位置 → 任务起点 → 任务终点 → 返航\n\n特点：\n- 适用于电量充足、任务距离适中的情况\n- 无需AGV配合，独立完成配送\n- 配送速度快，无等待延迟")
    with mode_col2:
        st.markdown("### 🔄 中继配送模式\n路径：AGV移动到中继点 → UAV从中继起飞 → 任务起点 → 任务终点 → 中继返航\n\n特点：\n- 适用于远距离任务或电量受限情况\n- AGV提供能量补给和位置支撑\n- 可降低UAV能耗，延长作业时间")

    st.markdown("---")
    st.markdown("## ⚙️ 消融实验设计")
    st.markdown("""
    为验证各模块贡献，设计了以下消融变体：

    | 变体名称 | 配置说明 |
    |---------|---------|
    | **unified_full** | 完整ALNS统一策略（基准） |
    | **direct_only** | 仅使用直接配送模式 |
    | **relay_only** | 仅使用中继配送模式 |
    | **greedy_pool** | 贪婪候选池策略 |
    | **random_pool** | 随机候选池策略 |
    | **fixed_weights** | 固定算子权重（禁用自适应） |
    | **simple_ops** | 简化算子集 |
    """)


def render_single_run(run_dir):
    """渲染单次运行展示"""
    st.header("📊 单次运行结果展示")
    if run_dir is None:
        st.warning("⚠️ 未找到单次运行结果目录")
        return
    st.markdown(f"**当前展示目录**: `{run_dir}`")

    metrics = load_json(run_dir / "metrics.json")
    metadata = load_json(run_dir / "metadata.json")

    st.subheader("📈 关键性能指标")
    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("任务完成率", f"{metrics.get('completion_rate', 0) * 100:.1f}%")
        with col2:
            st.metric("总能耗", f"{metrics.get('total_energy', 0):.2f} Wh")
        with col3:
            st.metric("平均配送时间", f"{metrics.get('avg_delivery_time', 0):.2f}")
        with col4:
            relay = metrics.get("relay_count", 0)
            direct = metrics.get("direct_count", 0)
            st.metric("直送/中继", f"{direct}/{relay}")

        st.markdown("#### 详细指标")
        extra_col1, extra_col2, extra_col3 = st.columns(3)
        with extra_col1:
            st.markdown(f"- 总配送距离: **{metrics.get('total_distance', 0):.2f}**")
            st.markdown(f"- UAV距离: **{metrics.get('total_distance_uav', 0):.2f}**")
        with extra_col2:
            st.markdown(f"- AGV距离: **{metrics.get('total_distance_agv', 0):.2f}**")
            st.markdown(f"- 充电次数: **{metrics.get('charging_count', 0)}**")
        with extra_col3:
            st.markdown(f"- 失败任务: **{metrics.get('failed_tasks', 0)}**")
            st.markdown(f"- 中继等待: **{metrics.get('avg_wait_time_at_relay', 0):.2f}**")

    st.subheader("📉 结果可视化")
    plots_dir = run_dir / "plots"
    if not plots_dir.exists():
        st.info("该运行目录未生成可视化图表")
        return

    available_plots = {
        "trajectory_map.png": "🚁 轨迹地图",
        "task_progress.png": "📦 任务进度",
        "energy_curve.png": "⚡ 能耗曲线",
        "kpi_summary.png": "📊 KPI汇总",
        "battery_status.png": "🔋 电池状态",
        "coordination_events.png": "🤝 协同事件"
    }
    existing = {k: v for k, v in available_plots.items() if (plots_dir / k).exists()}
    if not existing:
        st.info("该运行目录未生成可视化图表")
        return

    selected = st.multiselect("选择要展示的图表", list(existing.keys()),
                              default=list(existing.keys())[:4],
                              format_func=lambda x: existing[x])
    for i in range(0, len(selected), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(selected):
                plot_file = selected[i + j]
                with cols[j]:
                    st.markdown(f"**{existing[plot_file]}**")
                    try:
                        st.image(Image.open(plots_dir / plot_file), use_container_width=True)
                    except Exception as e:
                        st.error(f"加载图片失败: {e}")

    st.subheader("⚙️ 实验配置")
    if metadata:
        st.json(metadata)
    else:
        st.info("未找到配置信息")


def render_ablation(ablation_dir):
    """渲染消融实验展示"""
    st.header("🔬 ALNS消融实验结果")
    if ablation_dir is None:
        st.warning("⚠️ 未找到消融实验结果目录")
        return
    st.markdown(f"**当前展示目录**: `{ablation_dir}`")

    metadata = load_json(ablation_dir / "metadata.json")
    if metadata:
        st.subheader("📋 实验配置")
        config_col1, config_col2 = st.columns(2)
        with config_col1:
            st.markdown(f"**场景配置**: {metadata.get('configs', 'N/A')}")
            st.markdown(f"**随机种子**: {metadata.get('seeds', 'N/A')}")
        with config_col2:
            st.markdown(f"**最大步数**: {metadata.get('max_steps', 'N/A')}")
            st.markdown(f"**消融变体**: {len(metadata.get('variants', []))} 个")

    st.subheader("📊 消融实验对比图")
    figures_dir = ablation_dir / "figures"
    plots_summary_dir = ablation_dir / "plots_summary"

    if figures_dir.exists():
        overview = figures_dir / "ablation_overview.png"
        delta = figures_dir / "ablation_vs_full_delta.png"
        if overview.exists():
            st.markdown("#### 综合对比图")
            try:
                st.image(Image.open(overview), use_container_width=True)
            except Exception as e:
                st.error(f"加载图片失败: {e}")
        if delta.exists():
            st.markdown("#### 与Full ALNS的差值对比")
            try:
                st.image(Image.open(delta), use_container_width=True)
            except Exception as e:
                st.error(f"加载图片失败: {e}")

    if plots_summary_dir.exists():
        st.markdown("#### 详细指标对比")
        available_plots = {
            "completion_rate_by_variant.png": "📦 任务完成率对比",
            "total_energy_by_variant.png": "⚡ 总能耗对比",
            "avg_delivery_time_by_variant.png": "⏱️ 平均配送时间对比",
            "relay_direct_count_by_variant.png": "🤝 直送/中继次数对比",
            "comparison_vs_full_energy_delta.png": "📉 能耗差值对比",
            "comparison_vs_full_completion_delta.png": "📉 完成率差值对比"
        }
        existing = {k: v for k, v in available_plots.items() if (plots_summary_dir / k).exists()}
        if existing:
            selected = st.multiselect("选择要展示的详细图表", list(existing.keys()),
                                      default=list(existing.keys())[:3],
                                      format_func=lambda x: existing[x])
            for plot_file in selected:
                st.markdown(f"**{existing[plot_file]}**")
                try:
                    st.image(Image.open(plots_summary_dir / plot_file), use_container_width=True)
                except Exception as e:
                    st.error(f"加载图片失败: {e}")

    st.subheader("📄 聚合数据表格")
    aggregate_path = ablation_dir / "aggregate_by_variant.csv"
    comparison_path = ablation_dir / "comparison_vs_full.csv"

    if aggregate_path.exists():
        df = load_csv(aggregate_path)
        if df is not None and not df.empty:
            scenes = df["scene_name"].unique()
            selected_scene = st.selectbox("选择场景", scenes)
            filtered = df[df["scene_name"] == selected_scene]
            display_cols = ["variant_name", "completion_rate_mean", "total_energy_mean",
                          "avg_delivery_time_mean", "relay_count_mean", "direct_count_mean"]
            available = [c for c in display_cols if c in filtered.columns]
            if available:
                st.dataframe(filtered[available].round(2))

    if comparison_path.exists():
        st.markdown("#### 与Full ALNS对比")
        comp_df = load_csv(comparison_path)
        if comp_df is not None and not comp_df.empty:
            comp_df = comp_df[comp_df["variant_name"] != "unified_full"]
            if not comp_df.empty:
                display_cols = ["variant_name", "scene_name", "completion_rate_delta",
                              "total_energy_delta", "total_energy_relative_delta"]
                available = [c for c in display_cols if c in comp_df.columns]
                if available:
                    st.dataframe(comp_df[available].round(2))


def render_about():
    """渲染关于页面"""
    st.header("ℹ️ 关于本项目")
    st.markdown("""
    ### 数据来源说明

    本页面展示的所有数据均来源于本项目的真实实验结果：

    - **单次运行数据**：保存在 `results/runs/<场景名>/<时间戳>/` 目录
    - **消融实验数据**：保存在 `results/ablation/alns_ablation_<时间戳>/` 目录

    所有图表和数据均为实验实际运行生成，未经人工修改。

    ### 项目结构

    ```
    results/
    ├── runs/                           # 单次运行结果
    │   └── <场景名>/
    │       └── <时间戳>/
    │           ├── metrics.json         # 关键指标
    │           ├── plots/               # 可视化图表
    │           └── records/            # 详细记录
    │
    └── ablation/                       # 消融实验结果
        └── alns_ablation_<时间戳>/
            ├── aggregate_by_variant.csv # 聚合数据
            ├── comparison_vs_full.csv  # 与Full对比
            ├── figures/                # 汇总图表
            └── plots_summary/          # 详细图表
    ```

    ### 相关文档

    - [README](README.md) - 项目说明
    - [技术路线](docs/technical_route.md) - 技术架构
    - [消融实验设计](experiments/alns_ablation_design.md) - 实验设计
    - [ALNS架构说明](docs/alns_relay_architecture.md) - 算法详解
    """)
    st.markdown("---")
    st.markdown("""
    ### 技术栈

    - **仿真引擎**: Python + NumPy
    - **能耗模型**: 自定义分阶段能耗计算
    - **路径规划**: A* 算法
    - **优化算法**: ALNS (自适应大规模邻域搜索)
    - **可视化**: Matplotlib + Streamlit
    """)


def main():
    """主函数"""
    st.sidebar.title("📌 导航")
    latest_run = find_latest_run_dir()
    latest_ablation = find_latest_ablation_dir()

    page = st.sidebar.radio("选择页面",
                           ["🏠 首页", "📊 单次运行展示", "🔬 消融实验展示", "ℹ️ 关于"])

    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ 高级选项", expanded=False):
        st.markdown("#### 目录选择")
        if latest_run:
            st.markdown("**最新运行目录**:")
            st.code(str(latest_run))
        if latest_ablation:
            st.markdown("**最新消融目录**:")
            st.code(str(latest_ablation))

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 使用说明")
    st.sidebar.markdown("""
    1. 首页展示项目概述
    2. 单次运行展示查看详细结果
    3. 消融实验展示查看算法对比
    4. 关于页面查看数据来源

    **本地运行**:
    ```bash
    python -m streamlit run demo_app.py
    ```

    **部署到云端**:
    ```bash
    python -m streamlit run demo_app.py --server.port 8501
    ```
    """)

    if page == "🏠 首页":
        render_homepage()
    elif page == "📊 单次运行展示":
        render_single_run(latest_run)
    elif page == "🔬 消融实验展示":
        render_ablation(latest_ablation)
    elif page == "ℹ️ 关于":
        render_about()


if __name__ == "__main__":
    main()
