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
        shutil.copy2(trajectory_file, layout.artifact_path("trajectory.png"))
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
    
    # Copy strategy_compare.png from specified comparison directory
    if comparison_dir:
        strategy_compare_file = Path(comparison_dir) / "plots" / "strategy_compare.png"
        if strategy_compare_file.exists():
            shutil.copy2(strategy_compare_file, layout.artifact_path("strategy_compare.png"))
            print(f"Copied strategy_compare.png from {strategy_compare_file}")
        else:
            print("strategy_compare.png not found in specified comparison directory")
            raise FileNotFoundError("strategy_compare.png not found in specified comparison directory")
    else:
        # Fallback to latest comparison if none specified
        comparisons_dir = Path("results/comparisons")
        if comparisons_dir.exists():
            # Get all comparison directories
            compare_dirs = []
            for compare_name_dir in comparisons_dir.iterdir():
                if compare_name_dir.is_dir():
                    for timestamp_dir in compare_name_dir.iterdir():
                        if timestamp_dir.is_dir():
                            compare_dirs.append(timestamp_dir)
            
            if compare_dirs:
                # Sort by modification time
                compare_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_compare_dir = compare_dirs[0]
                
                strategy_compare_file = latest_compare_dir / "plots" / "strategy_compare.png"
                if strategy_compare_file.exists():
                    shutil.copy2(strategy_compare_file, layout.artifact_path("strategy_compare.png"))
                    print(f"Copied strategy_compare.png from {strategy_compare_file}")
                else:
                    print("strategy_compare.png not found in latest comparison directory")
                    raise FileNotFoundError("strategy_compare.png not found in latest comparison directory")
            else:
                print("No comparison directories found")
                raise FileNotFoundError("No comparison directories found")
        else:
            print("results/comparisons directory not found")
            raise FileNotFoundError("results/comparisons directory not found")
    
    # Generate and copy network_topology.png
    network_topology_file = layout.artifact_path("network_topology.png")
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
    parser.add_argument("--run-dir", type=str, help="Run directory to export from")
    parser.add_argument("--comparison-dir", type=str, help="Comparison directory to export from")
    parser.add_argument("--package-name", type=str, default="qualification_demo", help="Package name")
    
    args = parser.parse_args()
    
    if not args.run_dir:
        # Use the most recent run directory
        runs_dir = Path("results/runs")
        if runs_dir.exists():
            # Get all run directories
            run_dirs = []
            for scene_dir in runs_dir.iterdir():
                if scene_dir.is_dir():
                    for timestamp_dir in scene_dir.iterdir():
                        if timestamp_dir.is_dir():
                            run_dirs.append(timestamp_dir)
            
            if run_dirs:
                # Sort by modification time
                run_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                args.run_dir = str(run_dirs[0])
                print(f"Using most recent run: {args.run_dir}")
            else:
                print("No run directories found")
                sys.exit(1)
        else:
            print("results/runs directory not found")
            sys.exit(1)
    
    export_final_package(args.run_dir, args.comparison_dir, args.package_name)

if __name__ == "__main__":
    main()
