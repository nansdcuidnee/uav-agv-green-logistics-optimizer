#!/usr/bin/env python3
"""
Test script to verify coordination events state machine.
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

# Run simulation for 50 steps
print("Running simulation...")
max_steps = 50
for i in range(max_steps):
    print(f"\nStep {i}:")
    step_energy = simulator.step()
    simulator.total_energy += step_energy
    
    # Print events for this step
    step_events = [e for e in simulator.events if e['step'] == i]
    if step_events:
        print(f"  Events: {step_events}")
    
    if simulator.completed_tasks >= simulator.initial_task_count:
        print(f"All tasks completed at step {i}, stopping early.")
        break

# Print all events
print("\n=== All Events Recorded ===")
event_types = set()
for i, event in enumerate(simulator.events):
    print(f"{i+1}: {event}")
    event_types.add(event['type'])

# Print event types
print("\n=== Event Types ===")
print(sorted(event_types))

# Check for specific events
print("\n=== Event Validation ===")
has_relay_request = any(e['type'] == 'RELAY_REQUEST' for e in simulator.events)
has_agv_move_start = any(e['type'] == 'AGV_MOVE_START' for e in simulator.events)
has_agv_arrive_relay = any(e['type'] == 'AGV_ARRIVE_RELAY' for e in simulator.events)
has_wait_for_agv_start = any(e['type'] == 'WAIT_FOR_AGV_START' for e in simulator.events)
has_wait_for_agv_end = any(e['type'] == 'WAIT_FOR_AGV_END' for e in simulator.events)
has_charging_start = any(e['type'] == 'CHARGING_START' for e in simulator.events)
has_charging_end = any(e['type'] == 'CHARGING_END' for e in simulator.events)

print(f"RELAY_REQUEST: {has_relay_request}")
print(f"AGV_MOVE_START: {has_agv_move_start}")
print(f"AGV_ARRIVE_RELAY: {has_agv_arrive_relay}")
print(f"WAIT_FOR_AGV_START: {has_wait_for_agv_start}")
print(f"WAIT_FOR_AGV_END: {has_wait_for_agv_end}")
print(f"CHARGING_START: {has_charging_start}")
print(f"CHARGING_END: {has_charging_end}")

# Check for duplicate CHARGING_START events
charging_start_steps = [e['step'] for e in simulator.events if e['type'] == 'CHARGING_START']
print(f"\nCHARGING_START steps: {charging_start_steps}")
for i in range(1, len(charging_start_steps)):
    if charging_start_steps[i] == charging_start_steps[i-1] + 1:
        print(f"WARNING: Consecutive CHARGING_START events at steps {charging_start_steps[i-1]} and {charging_start_steps[i]}")

print("\nTest completed.")
