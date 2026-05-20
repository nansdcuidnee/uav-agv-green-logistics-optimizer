#!/usr/bin/env python3
"""Streamlit dashboard for visualizing UAV-AGV logistics simulation results."""

import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

RESULTS_BASE = Path("results")
RUNS_DIR = RESULTS_BASE / "runs"
COMPARISONS_DIR = RESULTS_BASE / "comparisons"
ROBUSTNESS_DIR = RESULTS_BASE / "robustness"


def scan_experiment_dirs(base_dir: Path) -> list[Path]:
    """Scan for all experiment directories with metrics.json."""
    if not base_dir.exists():
        return []
    
    experiment_dirs = []
    for sub_dir in base_dir.iterdir():
        if sub_dir.is_dir() and not sub_dir.name.startswith("."):
            for timestamp_dir in sub_dir.iterdir():
                if timestamp_dir.is_dir():
                    # 检查当前层级是否包含 metrics.json
                    if (timestamp_dir / "metrics.json").exists():
                        experiment_dirs.append(timestamp_dir)
                    else:
                        # 如果没有，继续向下扫描一层（支持更深的目录结构）
                        for nested_dir in timestamp_dir.iterdir():
                            if nested_dir.is_dir() and (nested_dir / "metrics.json").exists():
                                experiment_dirs.append(nested_dir)
    return sorted(experiment_dirs, key=lambda p: p.stat().st_mtime, reverse=True)


def scan_comparison_dirs(base_dir: Path) -> list[Path]:
    """Scan for all comparison directories."""
    if not base_dir.exists():
        return []
    
    comparison_dirs = []
    for sub_dir in base_dir.iterdir():
        if sub_dir.is_dir() and not sub_dir.name.startswith("."):
            for timestamp_dir in sub_dir.iterdir():
                if timestamp_dir.is_dir():
                    # 检查 comparison_summary.json 或 metrics.json
                    if (timestamp_dir / "comparison_summary.json").exists():
                        comparison_dirs.append(timestamp_dir)
                    elif (timestamp_dir / "metrics.json").exists():
                        comparison_dirs.append(timestamp_dir)
    return sorted(comparison_dirs, key=lambda p: p.stat().st_mtime, reverse=True)


def load_comparison_metrics(run_dir: Path) -> Optional[dict]:
    """Load comparison summary data from directory."""
    # 优先加载 comparison_summary.json
    summary_file = run_dir / "comparison_summary.json"
    if summary_file.exists():
        with open(summary_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 转换为统一格式
            if "metrics" in data and isinstance(data["metrics"], dict):
                return {
                    "experiment_name": data.get("scenario_name", "Comparison"),
                    "timestamp": "",
                    "strategies": data["metrics"],
                    "summary": {},
                }
            return data
    
    # 后备加载 metrics.json
    metrics_file = run_dir / "metrics.json"
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    return None


def load_metrics(run_dir: Path) -> Optional[dict]:
    """Load metrics.json from a run directory."""
    metrics_file = run_dir / "metrics.json"
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def generate_sample_comparison_data() -> dict:
    """Generate sample comparison data for demonstration."""
    return {
        "experiment_name": "Sample Strategy Comparison",
        "timestamp": "2024-01-15 14:30:00",
        "strategies": {
            "baseline_direct": {
                "completion_rate": 0.72,
                "on_time_rate": 0.65,
                "total_energy": 1850.50,
                "avg_energy_per_task": 123.37,
                "avg_delivery_time": 45.2,
                "charging_count": 12,
                "energy_saving_rate_vs_baseline": 0.0,
            },
            "relay_coop": {
                "completion_rate": 0.85,
                "on_time_rate": 0.78,
                "total_energy": 1620.30,
                "avg_energy_per_task": 108.02,
                "avg_delivery_time": 38.5,
                "charging_count": 8,
                "energy_saving_rate_vs_baseline": 0.124,
            },
            "energy_priority": {
                "completion_rate": 0.92,
                "on_time_rate": 0.88,
                "total_energy": 1450.80,
                "avg_energy_per_task": 96.72,
                "avg_delivery_time": 42.1,
                "charging_count": 6,
                "energy_saving_rate_vs_baseline": 0.216,
            },
        },
        "summary": {
            "best_completion": "energy_priority",
            "best_energy": "energy_priority",
            "best_time": "relay_coop",
        },
    }


def generate_sample_robustness_data() -> dict:
    """Generate sample robustness data for demonstration."""
    return {
        "experiment_name": "Sample Robustness Test",
        "timestamp": "2024-01-15 15:00:00",
        "total_runs": 10,
        "avg_completion_rate": 0.86,
        "std_completion_rate": 0.085,
        "avg_total_energy": 1580.40,
        "avg_charging_count": 8.5,
        "runs": [
            {"completion_rate": 0.90, "total_energy": 1520.0, "charging_count": 7, "avg_delivery_time": 40.0},
            {"completion_rate": 0.88, "total_energy": 1560.0, "charging_count": 8, "avg_delivery_time": 41.5},
            {"completion_rate": 0.85, "total_energy": 1600.0, "charging_count": 9, "avg_delivery_time": 42.0},
            {"completion_rate": 0.92, "total_energy": 1480.0, "charging_count": 6, "avg_delivery_time": 39.0},
            {"completion_rate": 0.82, "total_energy": 1650.0, "charging_count": 10, "avg_delivery_time": 43.5},
            {"completion_rate": 0.87, "total_energy": 1590.0, "charging_count": 9, "avg_delivery_time": 41.0},
            {"completion_rate": 0.89, "total_energy": 1540.0, "charging_count": 8, "avg_delivery_time": 40.5},
            {"completion_rate": 0.84, "total_energy": 1620.0, "charging_count": 9, "avg_delivery_time": 42.5},
            {"completion_rate": 0.91, "total_energy": 1500.0, "charging_count": 7, "avg_delivery_time": 39.5},
            {"completion_rate": 0.86, "total_energy": 1580.0, "charging_count": 8, "avg_delivery_time": 41.0},
        ],
    }


def load_metadata(run_dir: Path) -> Optional[dict]:
    """Load metadata.json from a run directory."""
    metadata_file = run_dir / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_tasks_csv(run_dir: Path) -> Optional[pd.DataFrame]:
    """Load tasks.csv from a run directory."""
    tasks_file = run_dir / "records" / "tasks.csv"
    if tasks_file.exists():
        try:
            return pd.read_csv(tasks_file)
        except Exception:
            return None
    return None


def load_steps_csv(run_dir: Path) -> Optional[pd.DataFrame]:
    """Load steps.csv from a run directory."""
    steps_file = run_dir / "records" / "steps.csv"
    if steps_file.exists():
        try:
            return pd.read_csv(steps_file)
        except Exception:
            return None
    return None


def format_metric(value, metric_name: str) -> str:
    """Format a metric value for display."""
    if value is None:
        return "N/A"
    
    percentage_metrics = {"completion_rate", "on_time_rate", "on_time_rate_given_completed"}
    if metric_name in percentage_metrics:
        return f"{value * 100:.2f}%" if isinstance(value, (int, float)) else str(value)
    
    if isinstance(value, float):
        if abs(value) < 100:
            return f"{value:.4f}"
        return f"{value:.2f}"
    
    return str(value)


def render_kpi_section(metrics: dict):
    """Render the KPI metrics section with professional styling."""
    st.subheader("📊 Core Performance Metrics", divider="blue")
    
    # 创建三列布局
    col1, col2, col3 = st.columns(3)
    
    # KPI数据
    kpi_data = {
        "Task Completion": {
            "value": metrics.get("completion_rate"),
            "format": "percentage",
            "icon": "✅",
            "color": "green",
            "description": "任务完成率"
        },
        "On-Time Delivery": {
            "value": metrics.get("on_time_rate"),
            "format": "percentage", 
            "icon": "⏱️",
            "color": "blue",
            "description": "准时送达率"
        },
        "Total Tasks": {
            "value": metrics.get("total_tasks"),
            "format": "number",
            "icon": "📋",
            "color": "orange",
            "description": "总任务数"
        },
        "Total Energy": {
            "value": metrics.get("total_energy"),
            "format": "float",
            "icon": "⚡",
            "color": "purple",
            "description": "总能耗"
        },
        "Avg Energy/Task": {
            "value": metrics.get("avg_energy_per_task"),
            "format": "float",
            "icon": "📈",
            "color": "red",
            "description": "单任务平均能耗"
        },
        "Charging Count": {
            "value": metrics.get("charging_count"),
            "format": "number",
            "icon": "🔋",
            "color": "yellow",
            "description": "充电次数"
        },
    }
    
    # 渲染KPI卡片
    kpi_list = list(kpi_data.items())
    for col, (name, data) in zip([col1, col2, col3, col1, col2, col3], kpi_list):
        with col:
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); 
                            border-radius: 12px; 
                            padding: 16px; 
                            text-align: center;
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <div style="font-size: 28px; margin-bottom: 8px;">{data['icon']}</div>
                    <div style="color: #ffffff; font-size: 24px; font-weight: bold; margin-bottom: 4px;">
                        {format_metric(data['value'], 'completion_rate') if data['format'] == 'percentage' else 
                         (f"{data['value']:.2f}" if data['format'] == 'float' else data['value'])}
                    </div>
                    <div style="color: #b8d4e3; font-size: 12px;">{data['description']}</div>
                </div>
            """, unsafe_allow_html=True)


def render_plots_section(run_dir: Path):
    """Render the plots section with large view and zoom capabilities."""
    st.subheader("🎯 Visualization Gallery", divider="blue")
    
    plots_dir = run_dir / "plots"
    if not plots_dir.exists():
        st.info("No plots directory found.")
        return
    
    plot_files = {
        "trajectory_map.png": "🛸 Trajectory Map",
        "energy_curve.png": "⚡ Energy Curve",
        "battery_status.png": "🔋 Battery Status",
        "task_progress.png": "📊 Task Progress",
        "kpi_summary.png": "📈 KPI Summary",
        "coordination_events.png": "🤝 Coordination Events",
        "environment_state.png": "🌍 Environment State",
    }
    
    # 获取可用的图片
    available_plots = []
    for filename, title in plot_files.items():
        if (plots_dir / filename).exists():
            available_plots.append((filename, title))
    
    if not available_plots:
        st.info("No plot files available.")
        return
    
    # 视图模式选择
    view_mode = st.radio(
        "View Mode",
        ["🖼️ Gallery View", "🔍 Single View"],
        index=0,
        horizontal=True
    )
    
    if view_mode == "🖼️ Gallery View":
        # 网格布局显示缩略图
        cols = st.columns(3)
        
        for i, (filename, title) in enumerate(available_plots):
            with cols[i % 3]:
                plot_path = plots_dir / filename
                st.markdown(f"**{title}**")
                st.image(
                    str(plot_path), 
                    use_container_width=True,
                    caption=title.replace("🛸 ", "").replace("⚡ ", "").replace("🔋 ", "").replace("📊 ", "").replace("📈 ", "").replace("🤝 ", "").replace("🌍 ", ""),
                    output_format="PNG"
                )
                # 添加放大按钮
                if st.button(f"🔍 View {title.split()[1]}", key=f"zoom_{filename}"):
                    st.session_state["selected_plot"] = filename
    
    else:
        # 单图查看模式
        plot_titles = [title for _, title in available_plots]
        selected_title = st.selectbox("Select Plot", plot_titles)
        
        # 找到选中的文件
        selected_filename = None
        for filename, title in available_plots:
            if title == selected_title:
                selected_filename = filename
                break
        
        if selected_filename:
            plot_path = plots_dir / selected_filename
            st.markdown(f"### {selected_title}")
            
            # 大图显示
            st.image(
                str(plot_path),
                use_column_width="always",
                caption=f"{selected_title} - Click to view full size",
                output_format="PNG"
            )
            
            # 添加下载按钮
            with open(plot_path, "rb") as f:
                st.download_button(
                    label="📥 Download Image",
                    data=f,
                    file_name=selected_filename,
                    mime="image/png"
                )


def render_tasks_table(tasks_df: pd.DataFrame):
    """Render the tasks data table with improved styling."""
    st.subheader("📋 Task Execution Details", divider="blue")
    
    if tasks_df is None or tasks_df.empty:
        st.info("No task data available.")
        return
    
    display_df = tasks_df.copy()
    if "completed" in display_df.columns:
        display_df["completed"] = display_df["completed"].map({True: "✅", False: "❌"})
    if "on_time" in display_df.columns:
        display_df["on_time"] = display_df["on_time"].map(
            {True: "✅", False: "⏰", "True": "✅", "False": "⏰"}
        ).fillna("N/A")
    
    # 添加表格样式
    st.dataframe(
        display_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("Task ID", width="small"),
            "priority": st.column_config.NumberColumn("Priority", width="small"),
            "start_point": st.column_config.Column("Start", width="medium"),
            "end_point": st.column_config.Column("End", width="medium"),
            "completed": st.column_config.Column("Completed", width="small"),
            "on_time": st.column_config.Column("On Time", width="small"),
        }
    )
    
    with st.expander("📄 Show Raw Data"):
        st.dataframe(tasks_df, use_container_width=True, hide_index=True)


def render_steps_chart(steps_df: pd.DataFrame):
    """Render the steps data as a chart."""
    st.subheader("📈 Execution Timeline", divider="blue")
    
    if steps_df is None or steps_df.empty:
        st.info("No step data available.")
        return
    
    # 创建时间线图表
    if "total_energy_cumulative" in steps_df.columns:
        st.line_chart(
            steps_df.set_index("step")["total_energy_cumulative"], 
            height=250,
            color="#2d5a87"
        )
    else:
        st.info("Energy cumulative data not available for charting.")
    
    # 添加统计信息
    st.markdown("### 📊 Timeline Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Steps", len(steps_df))
    col2.metric("Avg Energy/Step", steps_df.get("energy_consumed", pd.Series([0])).mean())
    col3.metric("Max Energy/Step", steps_df.get("energy_consumed", pd.Series([0])).max())


def render_comparison_view():
    """Render comparison view with comprehensive analysis."""
    st.header("🤝 Strategy Comparison", divider="blue")
    
    comparison_dirs = scan_comparison_dirs(COMPARISONS_DIR)
    
    # 使用模拟数据或真实数据
    if not comparison_dirs:
        st.info("⚠️ No comparison results found. Showing sample data for demonstration.")
        metrics = generate_sample_comparison_data()
        selected_dir = Path("sample_data")
        show_content = True
    else:
        comparison_options = [str(p.relative_to(COMPARISONS_DIR)) for p in comparison_dirs]
        selected = st.selectbox("Select comparison experiment", comparison_options)
        selected_dir = COMPARISONS_DIR / selected
        metrics = load_comparison_metrics(selected_dir)
        show_content = selected is not None
    
    if show_content and metrics:
        # 策略颜色映射
        strategy_colors = {
            "baseline_direct": "#FF6B6B",
            "relay_coop": "#4ECDC4",
            "energy_priority": "#45B7D1",
        }
        
        if metrics:
            # 1. 策略对比概览卡片
            st.subheader("📊 Strategy Comparison Overview")
            
            if isinstance(metrics, dict) and "strategies" in metrics:
                strategies = metrics["strategies"]
                col1, col2, col3 = st.columns(3)
                
                for i, (strategy_key, strategy_data) in enumerate(strategies.items()):
                    with [col1, col2, col3][i % 3]:
                        st.markdown(f"""
                            <div style="background: linear-gradient(135deg, {strategy_colors.get(strategy_key, '#1e3a5f')}40 0%, {strategy_colors.get(strategy_key, '#2d5a87')}80 100%);
                                        border-radius: 12px;
                                        padding: 16px;
                                        border-left: 4px solid {strategy_colors.get(strategy_key, '#2d5a87')};">
                                <h4 style="color: white; margin: 0 0 8px 0;">{strategy_key.replace('_', ' ').title()}</h4>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                                    <div style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 8px; text-align: center;">
                                        <div style="color: #FFFFFF; font-size: 18px; font-weight: bold;">{strategy_data.get('completion_rate', 0) * 100:.1f}%</div>
                                        <div style="color: #b8d4e3; font-size: 10px;">Completion</div>
                                    </div>
                                    <div style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 8px; text-align: center;">
                                        <div style="color: #6BCB77; font-size: 18px; font-weight: bold;">{strategy_data.get('total_energy', 0):.1f}</div>
                                        <div style="color: #b8d4e3; font-size: 10px;">Energy</div>
                                    </div>
                                    <div style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 8px; text-align: center;">
                                        <div style="color: #4D96FF; font-size: 18px; font-weight: bold;">{strategy_data.get('avg_delivery_time', 0):.1f}</div>
                                        <div style="color: #b8d4e3; font-size: 10px;">Time</div>
                                    </div>
                                    <div style="background: rgba(255,255,255,0.1); padding: 8px; border-radius: 8px; text-align: center;">
                                        <div style="color: #FF6B6B; font-size: 18px; font-weight: bold;">{strategy_data.get('charging_count', 0)}</div>
                                        <div style="color: #b8d4e3; font-size: 10px;">Charges</div>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            
            # 2. 对比指标详情
            st.subheader("📈 Detailed Metrics Comparison")
            
            # 创建对比表格数据
            if isinstance(metrics, dict) and "strategies" in metrics:
                comparison_data = []
                for strategy_key, strategy_data in metrics["strategies"].items():
                    comparison_data.append({
                        "Strategy": strategy_key.replace('_', ' ').title(),
                        "Completion Rate": f"{strategy_data.get('completion_rate', 0) * 100:.2f}%",
                        "On-Time Rate": f"{strategy_data.get('on_time_rate', 0) * 100:.2f}%",
                        "Total Energy": f"{strategy_data.get('total_energy', 0):.2f}",
                        "Avg Energy/Task": f"{strategy_data.get('avg_energy_per_task', 0):.2f}",
                        "Charging Count": strategy_data.get('charging_count', 0),
                        "Energy Saving": f"{strategy_data.get('energy_saving_rate_vs_baseline', 0) * 100:.2f}%" if strategy_data.get('energy_saving_rate_vs_baseline') else "N/A",
                    })
                
                st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
            
            # 3. 原始数据查看
            with st.expander("📄 Raw Comparison Data"):
                st.json(metrics, expanded=False)
        
        # 4. 对比图表
        plots_dir = selected_dir / "plots"
        if plots_dir.exists():
            st.subheader("🎯 Comparison Charts")
            
            comparison_plots = [
                ("total_energy_compare.png", "⚡ Total Energy Comparison"),
                ("completion_rate_compare.png", "✅ Completion Rate Comparison"),
                ("on_time_rate_compare.png", "⏱️ On-Time Rate Comparison"),
                ("avg_energy_per_task_compare.png", "📊 Avg Energy per Task"),
                ("energy_saving_rate_compare.png", "💰 Energy Saving Rate"),
            ]
            
            # 视图模式选择
            view_mode = st.radio("Chart View", ["Grid", "Single"], horizontal=True, index=0)
            
            if view_mode == "Grid":
                cols = st.columns(2)
                for i, (plot_file, title) in enumerate(comparison_plots):
                    with cols[i % 2]:
                        plot_path = plots_dir / plot_file
                        if plot_path.exists():
                            st.markdown(f"**{title}**")
                            st.image(str(plot_path), use_container_width=True)
            else:
                plot_titles = [title for _, title in comparison_plots if (plots_dir / _).exists()]
                if plot_titles:
                    selected_plot = st.selectbox("Select Chart", plot_titles)
                    for plot_file, title in comparison_plots:
                        if title == selected_plot:
                            plot_path = plots_dir / plot_file
                            if plot_path.exists():
                                st.image(str(plot_path), use_column_width="always")
                                with open(plot_path, "rb") as f:
                                    st.download_button("📥 Download", f, file_name=plot_file)


def aggregate_robustness_data(campaign_dir: Path) -> dict:
    """Aggregate metrics from all runs in a robustness campaign."""
    runs_data = []
    
    # 递归查找所有包含 metrics.json 的目录
    for run_dir in campaign_dir.rglob("*"):
        if run_dir.is_dir():
            metrics_file = run_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r", encoding="utf-8") as f:
                    run_metrics = json.load(f)
                    runs_data.append({
                        "completion_rate": run_metrics.get("completion_rate", 0),
                        "total_energy": run_metrics.get("total_energy", 0),
                        "charging_count": run_metrics.get("charging_count", 0),
                        "avg_delivery_time": run_metrics.get("avg_delivery_time", 0),
                    })
    
    if not runs_data:
        return None
    
    completion_rates = [r["completion_rate"] for r in runs_data]
    total_energies = [r["total_energy"] for r in runs_data]
    
    return {
        "experiment_name": campaign_dir.name,
        "timestamp": "",
        "total_runs": len(runs_data),
        "avg_completion_rate": sum(completion_rates) / len(completion_rates),
        "std_completion_rate": (sum((x - sum(completion_rates)/len(completion_rates))**2 for x in completion_rates) / len(completion_rates))**0.5,
        "avg_total_energy": sum(total_energies) / len(total_energies),
        "runs": runs_data,
    }


def scan_robustness_campaigns(base_dir: Path) -> list[Path]:
    """Scan for robustness campaign directories."""
    if not base_dir.exists():
        return []
    
    campaigns = []
    for campaign_dir in base_dir.iterdir():
        if campaign_dir.is_dir() and not campaign_dir.name.startswith("."):
            # 检查是否包含子目录
            if any(campaign_dir.iterdir()):
                campaigns.append(campaign_dir)
    return sorted(campaigns, key=lambda p: p.stat().st_mtime, reverse=True)


def render_robustness_view():
    """Render robustness view with comprehensive analysis."""
    st.header("🔬 Robustness Analysis", divider="blue")
    
    robustness_campaigns = scan_robustness_campaigns(ROBUSTNESS_DIR)
    
    # 使用模拟数据或真实数据
    if not robustness_campaigns:
        st.info("⚠️ No robustness results found. Showing sample data for demonstration.")
        metrics = generate_sample_robustness_data()
        show_content = True
    else:
        robustness_options = [str(p.relative_to(ROBUSTNESS_DIR)) for p in robustness_campaigns]
        selected = st.selectbox("Select robustness experiment", robustness_options)
        selected_dir = ROBUSTNESS_DIR / selected
        metrics = aggregate_robustness_data(selected_dir)
        show_content = selected is not None and metrics is not None
    
    if show_content and metrics:
            # 1. 鲁棒性概览卡片
            st.subheader("📊 Robustness Overview")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
                                border-radius: 12px; padding: 16px; text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 8px;">📊</div>
                        <div style="color: white; font-size: 20px; font-weight: bold;">{metrics.get('total_runs', 'N/A')}</div>
                        <div style="color: #b8d4e3; font-size: 12px;">Total Runs</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                avg_completion = metrics.get('avg_completion_rate', 0)
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #2d5a87 0%, #3d7ab7 100%);
                                border-radius: 12px; padding: 16px; text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 8px;">✅</div>
                        <div style="color: white; font-size: 20px; font-weight: bold;">{avg_completion * 100:.1f}%</div>
                        <div style="color: #b8d4e3; font-size: 12px;">Avg Completion</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #3d7ab7 0%, #4d8ac7 100%);
                                border-radius: 12px; padding: 16px; text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 8px;">⚡</div>
                        <div style="color: white; font-size: 20px; font-weight: bold;">{metrics.get('avg_total_energy', 0):.1f}</div>
                        <div style="color: #b8d4e3; font-size: 12px;">Avg Energy</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col4:
                std_completion = metrics.get('std_completion_rate', 0)
                st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #4d8ac7 0%, #5d9ad7 100%);
                                border-radius: 12px; padding: 16px; text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 8px;">📈</div>
                        <div style="color: white; font-size: 20px; font-weight: bold;">{std_completion * 100:.2f}%</div>
                        <div style="color: #b8d4e3; font-size: 12px;">Std Deviation</div>
                    </div>
                """, unsafe_allow_html=True)
            
            # 2. 详细运行数据
            st.subheader("📈 Run Details")
            
            if "runs" in metrics and isinstance(metrics["runs"], list):
                run_data = []
                for i, run in enumerate(metrics["runs"]):
                    completion_rate = run.get('completion_rate', 0)
                    run_data.append({
                        "Run #": i + 1,
                        "Completion Rate": f"{completion_rate * 100:.2f}%",
                        "Total Energy": f"{run.get('total_energy', 0):.2f}",
                        "Charging Count": run.get('charging_count', 0),
                        "Avg Time": f"{run.get('avg_delivery_time', 0):.1f}",
                        "Status": "✅ Good" if completion_rate >= 0.7 else ("⚠️ Medium" if completion_rate >= 0.5 else "🔴 Low"),
                    })
                
                st.dataframe(pd.DataFrame(run_data), use_container_width=True, hide_index=True)
            
            # 3. 鲁棒性评估
            st.subheader("🔍 Robustness Assessment")
            
            avg_completion = metrics.get('avg_completion_rate', 0)
            std_completion = metrics.get('std_completion_rate', 0)
            
            if avg_completion >= 0.8 and std_completion < 0.1:
                st.success("✅ **High Robustness**: The strategy shows stable and consistent performance across all runs.")
            elif avg_completion >= 0.6 and std_completion < 0.2:
                st.info("⚠️ **Moderate Robustness**: The strategy performs adequately but with some variability.")
            else:
                st.warning("🔴 **Low Robustness**: The strategy performance varies significantly. Consider parameter tuning.")
            
            # 4. 原始数据
            with st.expander("📄 Raw Data"):
                st.json(metrics, expanded=False)
    else:
        st.info("No metrics data found for this experiment.")


def main():
    """Main function to render the dashboard."""
    # 页面配置
    st.set_page_config(
        page_title="UAV-AGV Logistics Dashboard",
        page_icon="🚁",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # 添加自定义CSS样式
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 50%, #f1f5f9 100%);
            min-height: 100vh;
        }
        h1, h2, h3 {
            color: #1e293b;
        }
        h4 {
            color: #334155;
        }
        p {
            color: #475569;
        }
        .stMetric {
            background: rgba(30, 41, 59, 0.05);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(30, 41, 59, 0.1);
        }
        .css-1d391kg {
            background: rgba(248, 250, 252, 0.95);
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 页面头部
    st.markdown("""
        <div style="background: linear-gradient(90deg, #1e3a5f 0%, #2d5a87 50%, #1e3a5f 100%); 
                    padding: 30px; border-radius: 16px; margin-bottom: 20px; text-align: center;">
            <div style="font-size: 48px; margin-bottom: 10px;">🚁🤖</div>
            <h1 style="color: white; font-size: 36px; margin-bottom: 8px;">UAV-AGV Green Logistics Optimizer</h1>
            <p style="color: #e2e8f0; font-size: 16px;">Advanced Simulation & Optimization Dashboard</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 40px; margin-bottom: 10px;">📡</div>
                <h3 style="color: #1e293b;">Control Panel</h3>
            </div>
        """, unsafe_allow_html=True)
        
        view_mode = st.radio(
            "Select View Mode",
            ["Single Experiment", "Comparisons", "Robustness"],
            index=0,
        )
    
    # 主内容区域
    if view_mode == "Single Experiment":
        st.header("🔍 Single Experiment Analysis", divider="gray")
        
        # 定义三种策略
        STRATEGIES = {
            "baseline_direct": {"name": "📦 Baseline Direct", "description": "直接配送策略"},
            "relay_coop": {"name": "🤝 Relay Cooperation", "description": "中继协作策略"},
            "energy_priority": {"name": "⚡ Energy Priority", "description": "能耗优先策略"},
        }
        
        # 获取所有可用的策略实验
        available_strategies = []
        for strategy_key, strategy_info in STRATEGIES.items():
            strategy_dir = RUNS_DIR / strategy_key
            if strategy_dir.exists() and any(strategy_dir.iterdir()):
                available_strategies.append(strategy_key)
        
        if not available_strategies:
            st.error("⚠️ No experiment results found. Please run some experiments first.")
            return
        
        # 策略选择
        st.subheader("🎯 Strategy Selection")
        col1, col2, col3 = st.columns(3)
        selected_strategy = None
        
        for i, (strategy_key, strategy_info) in enumerate(STRATEGIES.items()):
            with [col1, col2, col3][i]:
                if st.button(
                    f"{strategy_info['name']}",
                    key=strategy_key,
                    help=strategy_info['description'],
                    use_container_width=True,
                ):
                    selected_strategy = strategy_key
        
        # 默认选择第一个可用策略
        if selected_strategy is None:
            selected_strategy = available_strategies[0]
        
        # 获取该策略的最新实验
        strategy_dir = RUNS_DIR / selected_strategy
        experiment_dirs = sorted(
            [d for d in strategy_dir.iterdir() if d.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not experiment_dirs:
            st.error(f"⚠️ No experiments found for {STRATEGIES[selected_strategy]['name']}")
            return
        
        selected_experiment = experiment_dirs[0]
        
        # 显示策略信息
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); 
                        padding: 16px; 
                        border-radius: 12px;
                        margin: 10px 0;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <h3 style="color: white; margin: 0;">{STRATEGIES[selected_strategy]['name']}</h3>
                        <p style="color: #b8d4e3; font-size: 14px; margin: 4px 0 0 0;">
                            {STRATEGIES[selected_strategy]['description']}
                        </p>
                    </div>
                    <div style="font-size: 36px;">
                        {STRATEGIES[selected_strategy]['name'].split()[0]}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 显示实验时间
        import datetime
        exp_time = datetime.datetime.fromtimestamp(selected_experiment.stat().st_mtime)
        st.markdown(f"**Experiment Time:** `{exp_time.strftime('%Y-%m-%d %H:%M:%S')}`")
        
        selected_dir = selected_experiment
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
                metrics = load_metrics(selected_dir)
                metadata = load_metadata(selected_dir)
                
                if metrics:
                    render_kpi_section(metrics)
                    
                    if metadata:
                        with st.expander("Experiment Metadata"):
                            st.json(metadata)
                    
                    if metrics.get("baseline_total_energy"):
                        st.markdown("**vs Baseline**")
                        baseline_col1, baseline_col2 = st.columns(2)
                        baseline_col1.metric(
                            "Baseline Energy",
                            f"{metrics.get('baseline_total_energy', 0):.2f}",
                        )
                        baseline_col2.metric(
                            "Energy Saving",
                            f"{metrics.get('energy_saving_rate_vs_baseline', 0) * 100:.2f}%"
                            if metrics.get("energy_saving_rate_vs_baseline")
                            else "N/A",
                        )
                else:
                    st.error("Metrics not found for selected experiment.")
        
        with col2:
                tab1, tab2, tab3 = st.tabs(["🎯 Visualizations", "📋 Tasks", "📈 Timeline"])
                
                with tab1:
                    render_plots_section(selected_dir)
                
                with tab2:
                    tasks_df = load_tasks_csv(selected_dir)
                    render_tasks_table(tasks_df)
                
                with tab3:
                    steps_df = load_steps_csv(selected_dir)
                    render_steps_chart(steps_df)
    
    elif view_mode == "Comparisons":
        render_comparison_view()
    
    elif view_mode == "Robustness":
        render_robustness_view()


if __name__ == "__main__":
    main()