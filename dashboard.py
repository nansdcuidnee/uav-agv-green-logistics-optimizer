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
                if timestamp_dir.is_dir() and (timestamp_dir / "metrics.json").exists():
                    experiment_dirs.append(timestamp_dir)
    return sorted(experiment_dirs, key=lambda p: p.stat().st_mtime, reverse=True)


def scan_comparison_dirs(base_dir: Path) -> list[Path]:
    """Scan for all comparison directories."""
    if not base_dir.exists():
        return []
    
    comparison_dirs = []
    for sub_dir in base_dir.iterdir():
        if sub_dir.is_dir() and not sub_dir.name.startswith("."):
            for timestamp_dir in sub_dir.iterdir():
                if timestamp_dir.is_dir() and (timestamp_dir / "metrics.json").exists():
                    comparison_dirs.append(timestamp_dir)
    return sorted(comparison_dirs, key=lambda p: p.stat().st_mtime, reverse=True)


def load_metrics(run_dir: Path) -> Optional[dict]:
    """Load metrics.json from a run directory."""
    metrics_file = run_dir / "metrics.json"
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


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
    """Render the KPI metrics section."""
    st.subheader("Core KPIs")
    
    col1, col2, col3 = st.columns(3)
    
    kpis_col1 = [
        ("Completion Rate", metrics.get("completion_rate")),
        ("On-Time Rate", metrics.get("on_time_rate")),
        ("Total Tasks", metrics.get("total_tasks")),
    ]
    
    kpis_col2 = [
        ("Total Energy", metrics.get("total_energy")),
        ("Avg Energy per Task", metrics.get("avg_energy_per_task")),
        ("Energy per km", metrics.get("energy_per_km")),
    ]
    
    kpis_col3 = [
        ("Charging Count", metrics.get("charging_count")),
        ("Avg Delivery Time", metrics.get("avg_delivery_time")),
        ("Total Time (steps)", metrics.get("total_time")),
    ]
    
    for col, kpis in zip([col1, col2, col3], [kpis_col1, kpis_col2, kpis_col3]):
        for metric_name, value in kpis:
            col.metric(label=metric_name, value=format_metric(value, metric_name))


def render_plots_section(run_dir: Path):
    """Render the plots section."""
    st.subheader("Visualizations")
    
    plots_dir = run_dir / "plots"
    if not plots_dir.exists():
        st.info("No plots directory found.")
        return
    
    plot_files = {
        "trajectory_map.png": "Trajectory Map",
        "energy_curve.png": "Energy Curve",
        "battery_status.png": "Battery Status",
        "task_progress.png": "Task Progress",
        "kpi_summary.png": "KPI Summary",
        "coordination_events.png": "Coordination Events",
        "environment_state.png": "Environment State",
    }
    
    tabs = st.tabs(list(plot_files.values()))
    
    for tab, (filename, title) in zip(tabs, plot_files.items()):
        with tab:
            plot_path = plots_dir / filename
            if plot_path.exists():
                st.image(str(plot_path), caption=title, use_container_width=True)
            else:
                st.info(f"{title} not available in this experiment.")


def render_tasks_table(tasks_df: pd.DataFrame):
    """Render the tasks data table."""
    st.subheader("Task Details")
    
    if tasks_df is None or tasks_df.empty:
        st.info("No task data available.")
        return
    
    display_df = tasks_df.copy()
    if "completed" in display_df.columns:
        display_df["completed"] = display_df["completed"].map({True: "Yes", False: "No"})
    if "on_time" in display_df.columns:
        display_df["on_time"] = display_df["on_time"].map(
            {True: "Yes", False: "No", "True": "Yes", "False": "No"}
        ).fillna("N/A")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with st.expander("Show raw data"):
        st.dataframe(tasks_df, use_container_width=True, hide_index=True)


def render_steps_chart(steps_df: pd.DataFrame):
    """Render the steps data as a chart."""
    st.subheader("Execution Timeline")
    
    if steps_df is None or steps_df.empty:
        st.info("No step data available.")
        return
    
    if "total_energy_cumulative" in steps_df.columns:
        st.line_chart(steps_df.set_index("step")["total_energy_cumulative"], height=200)
    else:
        st.info("Energy cumulative data not available for charting.")


def render_comparison_view():
    """Render comparison view."""
    st.header("Comparison Results")
    
    comparison_dirs = scan_comparison_dirs(COMPARISONS_DIR)
    
    if not comparison_dirs:
        st.info("No comparison results found.")
        return
    
    comparison_options = [str(p.relative_to(COMPARISONS_DIR)) for p in comparison_dirs]
    selected = st.selectbox("Select comparison", comparison_options)
    
    if selected:
        selected_dir = COMPARISONS_DIR / selected
        metrics = load_metrics(selected_dir)
        
        if metrics:
            st.json(metrics)
        
        plots_dir = selected_dir / "plots"
        if plots_dir.exists():
            st.subheader("Comparison Charts")
            
            comparison_plots = [
                "total_energy_compare.png",
                "completion_rate_compare.png",
                "on_time_rate_compare.png",
                "avg_energy_per_task_compare.png",
                "energy_saving_rate_compare.png",
            ]
            
            for plot_file in comparison_plots:
                plot_path = plots_dir / plot_file
                if plot_path.exists():
                    st.image(str(plot_path), use_container_width=True)


def render_robustness_view():
    """Render robustness view."""
    st.header("Robustness Results")
    
    robustness_dirs = scan_experiment_dirs(ROBUSTNESS_DIR)
    
    if not robustness_dirs:
        st.info("No robustness results found.")
        return
    
    robustness_options = [str(p.relative_to(ROBUSTNESS_DIR)) for p in robustness_dirs]
    selected = st.selectbox("Select robustness experiment", robustness_options)
    
    if selected:
        selected_dir = ROBUSTNESS_DIR / selected
        metrics = load_metrics(selected_dir)
        
        if metrics:
            render_kpi_section(metrics)


def main():
    """Main function to render the dashboard."""
    st.set_page_config(
        page_title="UAV-AGV Logistics Dashboard",
        page_icon="📊",
        layout="wide",
    )
    
    st.title("📊 UAV-AGV Green Logistics Optimizer")
    st.markdown("Visualization dashboard for simulation results")
    
    view_mode = st.sidebar.radio(
        "View Mode",
        ["Single Experiment", "Comparisons", "Robustness"],
        index=0,
    )
    
    if view_mode == "Single Experiment":
        st.header("Single Experiment Results")
        
        all_experiment_dirs = scan_experiment_dirs(RUNS_DIR)
        
        if not all_experiment_dirs:
            st.error("No experiment results found. Please run some experiments first.")
            return
        
        experiment_options = [str(p.relative_to(RUNS_DIR)) for p in all_experiment_dirs]
        
        selected = st.sidebar.selectbox(
            "Select experiment",
            experiment_options,
            index=0,
        )
        
        if selected:
            selected_dir = RUNS_DIR / selected
            
            st.markdown(f"**Selected:** `{selected}`")
            
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
                tab1, tab2, tab3 = st.tabs(["Plots", "Tasks", "Timeline"])
                
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