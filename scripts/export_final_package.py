#!/usr/bin/env python3
"""Export final package for competition."""

import sys
import argparse
import shutil
import json
import os
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.utils.result_layout import create_result_layout

def export_final_package(run_dir, comparison_dir, package_name):
    """Export final package."""
    # Create finals layout
    layout = create_result_layout(
        experiment_name=package_name,
        result_type="finals"
    )
    
    # Copy metrics.json
    metrics_file = Path(run_dir) / "metrics.json"
    if metrics_file.exists():
        shutil.copy2(metrics_file, layout.artifact_path("metrics.json"))
        print("Copied metrics.json")
    else:
        print("metrics.json not found")
    
    # Copy communication_log.csv
    communication_log_file = Path(run_dir) / "communication_log.csv"
    if communication_log_file.exists():
        shutil.copy2(communication_log_file, layout.artifact_path("communication_log.csv"))
        print("Copied communication_log.csv")
    else:
        print("communication_log.csv not found")
    
    # Copy event_timeline.txt
    event_timeline_file = Path(run_dir) / "event_timeline.txt"
    if event_timeline_file.exists():
        shutil.copy2(event_timeline_file, layout.artifact_path("event_timeline.txt"))
        print("Copied event_timeline.txt")
    else:
        print("event_timeline.txt not found")
    
    # Copy chart.png as trajectory.png
    trajectory_file = Path(run_dir) / "plots" / "chart.png"
    if trajectory_file.exists():
        shutil.copy2(trajectory_file, layout.plot_path("trajectory.png"))
        print("Copied trajectory.png")
    else:
        print("chart.png not found")
    
    # Copy records directory
    records_dir = Path(run_dir) / "records"
    if records_dir.exists():
        for record_file in records_dir.iterdir():
            if record_file.is_file():
                shutil.copy2(record_file, layout.record_path(record_file.name))
                print(f"Copied {record_file.name}")
    else:
        print("records directory not found")
    
    # Read comparison_summary.json to get baseline information
    comparison_summary_file = Path(comparison_dir) / "comparison_summary.json"
    if comparison_summary_file.exists():
        with open(comparison_summary_file, "r", encoding="utf-8") as f:
            comparison_summary = json.load(f)
        print(f"Read comparison_summary.json, baseline strategy: {comparison_summary.get('baseline_strategy_name')}")
    else:
        print("comparison_summary.json not found")
        raise FileNotFoundError("comparison_summary.json not found in specified comparison directory")
    
    # Copy all comparison plots
    plots_dir = Path(comparison_dir) / "plots"
    if plots_dir.exists():
        comparison_plots = [
            "total_energy_compare.png",
            "completion_rate_compare.png",
            "on_time_rate_compare.png",
            "avg_delivery_time_compare.png",
            "energy_saving_rate_compare.png"
        ]
        
        for plot_file in comparison_plots:
            source_file = plots_dir / plot_file
            if source_file.exists():
                shutil.copy2(source_file, layout.plot_path(plot_file))
                print(f"Copied {plot_file} from {source_file}")
            else:
                print(f"{plot_file} not found in comparison directory")
    else:
        print("plots directory not found in comparison directory")
        raise FileNotFoundError("plots directory not found in comparison directory")
    
    # Generate and copy network_topology.png
    network_topology_file = layout.plot_path("network_topology.png")
    generate_network_topology_script = Path(__file__).parent / "generate_network_topology.py"
    if generate_network_topology_script.exists():
        try:
            subprocess.run(
                [sys.executable, str(generate_network_topology_script), "--output", str(network_topology_file)],
                check=True
            )
            print(f"Generated network_topology.png")
        except subprocess.CalledProcessError as e:
            print(f"Error generating network_topology.png: {e}")
    else:
        print("generate_network_topology.py not found")
    
    print(f"\nFinal package exported to: {layout.run_dir}")
    return str(layout.run_dir)

def main():
    """Export final package."""
    parser = argparse.ArgumentParser(description="Export final package for competition")
    parser.add_argument("--run-dir", type=str, required=True, help="Run directory to export from")
    parser.add_argument("--comparison-dir", type=str, required=True, help="Comparison directory to export from")
    parser.add_argument("--package-name", type=str, default="qualification_demo", help="Package name")
    
    args = parser.parse_args()
    
    # Verify run directory exists
    if not Path(args.run_dir).exists():
        print(f"Run directory not found: {args.run_dir}")
        sys.exit(1)
    
    # Verify comparison directory exists
    if not Path(args.comparison_dir).exists():
        print(f"Comparison directory not found: {args.comparison_dir}")
        sys.exit(1)
    
    export_final_package(args.run_dir, args.comparison_dir, args.package_name)

if __name__ == "__main__":
    main()
