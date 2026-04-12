#!/usr/bin/env python3
"""
Run relay_coop strategy and save results.
"""

import os
import sys
from src.simulation.simulator import Simulator
from src.simulation.environment import Environment
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler
from src.core.task import Task
from src.core.uav import UAV
from src.core.agv import AGV

# Create environment
env = Environment()

# Add a task with long distance
task = Task(
    id=1,
    start_point=(0, 0),
    end_point=(200, 200),  # Long distance to ensure relay is needed
    payload=1.0,
    priority=1
)
env.tasks.append(task)

# Add a UAV with low battery
uav = UAV(id=1, position=(0, 0), battery=30.0)  # Low battery to force relay
env.uavs.append(uav)

# Add an AGV far from the task
agv = AGV(id=1, position=(500, 500))  # Very far away to ensure movement
env.agvs.append(agv)

# Create simulator
simulator = Simulator(
    environment=env,
    energy_model=EnergyModel(),
    path_planner=PathPlanner(),
    scheduler=Scheduler(),
    strategy_type="relay_coop"
)

# Run simulation and save results
print("Running relay_coop strategy...")
run_dir = simulator.run(max_steps=100, experiment_name="test_relay_coop", result_type="runs")

print(f"\nRun completed. Results saved to: {run_dir}")

# Check coordination_events.csv
csv_path = os.path.join(run_dir, "coordination_events.csv")
if os.path.exists(csv_path):
    print("\n=== coordination_events.csv content (first 20 lines) ===")
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:20]):
            print(f"{i+1}: {line.strip()}")
    
    # Extract event types
    print("\n=== Event Types ===")
    event_types = set()
    for line in lines[1:]:  # Skip header
        if line.strip():
            parts = line.strip().split(',')
            if len(parts) >= 3:
                event_type = parts[2]
                event_types.add(event_type)
    print(sorted(event_types))
else:
    print("coordination_events.csv not found!")

# Check coordination_events.png
png_path = os.path.join(run_dir, "coordination_events.png")
if os.path.exists(png_path):
    print(f"\ncoordination_events.png generated at: {png_path}")
else:
    print("coordination_events.png not found!")
