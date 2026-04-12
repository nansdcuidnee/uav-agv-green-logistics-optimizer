#!/usr/bin/env python3
"""
Test script to check relay_coop strategy events.
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

# Manually run steps without saving results
print("Running steps manually...")
max_steps = 50
for i in range(max_steps):
    print(f"\nStep {i}:")
    print(f"  Tasks: {[t.status for t in simulator.environment.tasks]}")
    print(f"  AGV states: {simulator.agv_states}")
    print(f"  Task states: {simulator.task_states}")
    
    step_energy = simulator.step()
    simulator.total_energy += step_energy
    
    print(f"  Events this step: {[e for e in simulator.events if e['step'] == i]}")
    
    if simulator.completed_tasks >= simulator.initial_task_count:
        print(f"All tasks completed at step {i}, stopping early.")
        break
    simulator.time_step += 1

# Print all events
print("\nAll events recorded:")
for i, event in enumerate(simulator.events):
    print(f"{i+1}: {event}")

# Print event types
print("\nEvent types:")
event_types = set()
for event in simulator.events:
    event_types.add(event['type'])
print(event_types)

print("\nTest completed.")
