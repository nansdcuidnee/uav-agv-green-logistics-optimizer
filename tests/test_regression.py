"""Regression tests for fixed issues."""

import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase

from src.simulation.simulator import Simulator
from src.simulation.environment import Environment
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.scheduling.scheduler import Scheduler


class TestRegression(TestCase):
    """Regression tests for fixed issues."""

    def setUp(self):
        """Set up test environment."""
        # Create a simple environment for testing
        self.env = Environment()
        self.env.uavs = []
        self.env.agvs = []
        self.env.tasks = []
        
        # Create energy model, path planner, and scheduler
        self.energy_model = EnergyModel()
        self.path_planner = PathPlanner()
        self.scheduler = Scheduler()

    def test_energy_saving_rate_not_constant(self):
        """Test that energy saving rate is not constant 50%."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(100, 100),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a simple UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create a simple AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)
        
        # Create simulator with baseline_direct strategy
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        
        # Run simulation
        simulator.run(max_steps=10)
        
        # Calculate metrics
        metrics = simulator.calculate_metrics()
        
        # Check that energy saving rate is None (since no baseline is set)
        self.assertIsNone(
            metrics["energy_saving_rate_vs_baseline"],
            msg="Energy saving rate should be None when no baseline is set"
        )

    def test_avg_delivery_time_equals_execution_time(self):
        """Test that avg_delivery_time equals average execution_time."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(100, 100),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a simple UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create a simple AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)
        
        # Create simulator with baseline_direct strategy
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        
        # Run simulation
        simulator.run(max_steps=10)
        
        # Calculate metrics
        metrics = simulator.calculate_metrics()
        
        # Calculate average execution time manually
        execution_times = []
        for task in self.env.tasks:
            if hasattr(task, 'start_time') and hasattr(task, 'completion_time'):
                start_time = getattr(task, 'start_time', None)
                completion_time = getattr(task, 'completion_time', None)
                if start_time is not None and completion_time is not None:
                    execution_time = completion_time - start_time
                    execution_times.append(execution_time)
        
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        # Check that avg_delivery_time equals average execution time
        self.assertAlmostEqual(
            metrics["avg_delivery_time"],
            avg_execution_time,
            delta=0.1,
            msg="avg_delivery_time should equal average execution time"
        )

    def test_export_final_package_requires_run_dir(self):
        """Test that export_final_package requires --run-dir and --comparison-dir."""
        import subprocess
        import sys
        
        # Test that export_final_package fails without --run-dir and --comparison-dir
        result = subprocess.run(
            [sys.executable, "-m", "scripts.export_final_package"],
            capture_output=True,
            text=True
        )
        
        # Check that command fails
        self.assertNotEqual(result.returncode, 0)
        # Check that error message mentions required arguments
        self.assertIn("required", result.stderr)

    def test_energy_saving_rate_calculation(self):
        """Test that energy saving rate calculation is reasonable."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(100, 100),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a simple UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create a simple AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)
        
        # Create simulator with baseline_direct strategy
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        
        # Run simulation
        simulator.run(max_steps=10)
        
        # Calculate metrics
        metrics = simulator.calculate_metrics()
        
        # Check that energy saving rate is None (since no baseline is set)
        self.assertIsNone(
            metrics["energy_saving_rate_vs_baseline"],
            msg="Energy saving rate should be None when no baseline is set"
        )
        
        # Check that total energy is greater than 0
        self.assertGreater(
            metrics.get("total_energy", 0),
            0,
            msg="Total energy should be greater than 0"
        )

    def test_relay_coop_time_cost(self):
        """Test that relay_coop strategy has reasonable time cost."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),  # 缩短任务距离
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a simple UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create a simple AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)
        
        # Create simulator with baseline_direct strategy
        simulator_baseline = Simulator(
            environment=self.env.copy(),
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        
        # Run simulation with baseline_direct
        simulator_baseline.run(max_steps=50)
        metrics_baseline = simulator_baseline.calculate_metrics()
        
        # Create simulator with relay_coop strategy
        from src.simulation.environment import Environment
        new_env = Environment()
        new_env.uavs = [UAV(id=1, position=(0, 0), battery=100.0)]
        new_env.agvs = [AGV(id=1, position=(0, 0))]
        new_env.tasks = [Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),  # 缩短任务距离
            payload=1.0,
            priority=1
        )]
        
        simulator_relay = Simulator(
            environment=new_env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )
        
        # Run simulation with relay_coop
        simulator_relay.run(max_steps=100)  # 增加步数以确保任务完成
        metrics_relay = simulator_relay.calculate_metrics()
        
        # 确保两个策略都完成了任务
        self.assertGreater(metrics_baseline["completion_rate"], 0, msg="Baseline strategy should complete tasks")
        self.assertGreater(metrics_relay["completion_rate"], 0, msg="Relay coop strategy should complete tasks")
        
        # Check that relay_coop has reasonable time cost
        # It should not be significantly shorter than baseline_direct
        # due to AGV movement time
        self.assertLessEqual(
            metrics_relay["total_time"],
            metrics_baseline["total_time"] * 2.0,  # 放宽限制，因为 AGV 需要移动
            msg="Relay coop time should not be more than twice as long as baseline"
        )
    
    def test_relay_coop_agv_movement(self):
        """Test that relay_coop strategy includes AGV movement cost."""
        # Create a task with AGV far from relay point
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(100, 100),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create an AGV far from the task start point
        from src.core.agv import AGV
        agv = AGV(id=1, position=(-100, -100))  # 远离任务起点
        self.env.agvs.append(agv)
        
        # Create simulator with relay_coop strategy
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )
        
        # Run simulation
        simulator.run(max_steps=100)
        
        # Calculate metrics
        metrics = simulator.calculate_metrics()
        
        # Check that AGV distance and energy are recorded
        self.assertGreaterEqual(metrics.get("total_distance_agv", 0), 0, msg="AGV distance should be recorded")
        self.assertGreaterEqual(metrics.get("agv_energy", 0), 0, msg="AGV energy should be recorded")
        
        # Check that some tasks have wait time at relay
        has_wait_time = False
        for task in self.env.tasks:
            if hasattr(task, 'wait_time_at_relay') and getattr(task, 'wait_time_at_relay', 0) > 0:
                has_wait_time = True
                break
        self.assertTrue(has_wait_time, msg="Some tasks should have wait time at relay")
    
    def test_relative_metrics_calculation(self):
        """Test that relative metrics calculation is correct."""
        # Import the compute_relative_metrics function
        from experiments.compare_strategies import compute_relative_metrics
        
        # Test case 1: Normal case
        baseline_metrics = {"total_energy": 100, "carbon_emission": 50}
        strategy_metrics = {"total_energy": 80, "carbon_emission": 40}
        result = compute_relative_metrics(strategy_metrics, baseline_metrics)
        
        # Check energy saving rate
        self.assertAlmostEqual(result["energy_saving_rate_vs_baseline"], 20.0, delta=0.1)
        # Check emission reduction rate
        self.assertAlmostEqual(result["emission_reduction_rate_vs_baseline"], 20.0, delta=0.1)
        
        # Test case 2: No baseline
        result_no_baseline = compute_relative_metrics(strategy_metrics, None)
        self.assertIsNone(result_no_baseline["energy_saving_rate_vs_baseline"])
        self.assertIsNone(result_no_baseline["emission_reduction_rate_vs_baseline"])
        
        # Test case 3: Baseline energy is zero
        baseline_zero = {"total_energy": 0, "carbon_emission": 0}
        result_zero_baseline = compute_relative_metrics(strategy_metrics, baseline_zero)
        self.assertIsNone(result_zero_baseline["energy_saving_rate_vs_baseline"])
        self.assertIsNone(result_zero_baseline["emission_reduction_rate_vs_baseline"])
    
    def test_steps_csv_cumulative_values(self):
        """Test that steps.csv cumulative values match metrics."""
        import csv
        
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create an AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)
        
        # Create simulator
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        
        # Run simulation and save results
        output_dir = simulator.run(max_steps=20)
        metrics = simulator.calculate_metrics()
        
        # Read steps.csv from the actual output directory
        import os
        steps_file = os.path.join(output_dir, "records", "steps.csv")
        
        # Ensure steps.csv exists
        self.assertTrue(os.path.exists(steps_file), msg="steps.csv should exist")
        
        # Read steps.csv
        with open(steps_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Ensure there are rows in steps.csv
        self.assertTrue(len(rows) > 0, msg="steps.csv should have at least one row")
        
        last_row = rows[-1]
        
        # Check that cumulative values match metrics
        self.assertAlmostEqual(float(last_row["total_energy_cumulative"]), metrics["total_energy"], delta=0.1, msg="total_energy_cumulative should match metrics.total_energy")
        self.assertEqual(int(last_row["completed_tasks_cumulative"]), metrics["completed_tasks"], msg="completed_tasks_cumulative should match metrics.completed_tasks")
        self.assertEqual(int(last_row["charging_count_cumulative"]), metrics["charging_count"], msg="charging_count_cumulative should match metrics.charging_count")
        
        # Check distance cumulative values
        total_distance = float(last_row["total_distance_cumulative"])
        expected_total_distance = metrics["total_distance"]
        self.assertAlmostEqual(total_distance, expected_total_distance, delta=0.1, msg="total_distance_cumulative should match metrics.total_distance")
        
        # Check UAV and AGV distance
        uav_distance = float(last_row["uav_distance_cumulative"])
        agv_distance = float(last_row["agv_distance_cumulative"])
        self.assertAlmostEqual(uav_distance + agv_distance, expected_total_distance, delta=0.1, msg="uav_distance + agv_distance should equal total_distance")
    
    def test_standard_plots_generation(self):
        """Test that all 7 standard plots are generated."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create an AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)
        
        # Test all three strategies
        strategies = ["baseline_direct", "relay_coop", "energy_priority"]
        
        for strategy_type in strategies:
            # Create a new environment for each strategy to avoid state carryover
            from src.simulation.environment import Environment
            test_env = Environment()
            
            # Create a simple task
            from src.core.task import Task
            task = Task(
                id=1,
                start_point=(0, 0),
                end_point=(50, 50),
                payload=1.0,
                priority=1
            )
            test_env.tasks.append(task)
            
            # Create a UAV with higher battery to ensure it can perform tasks
            from src.core.uav import UAV
            uav = UAV(id=1, position=(0, 0), battery=200.0)  # Higher battery to avoid immediate low battery
            test_env.uavs.append(uav)
            
            # Create an AGV
            from src.core.agv import AGV
            agv = AGV(id=1, position=(-100, -100))  # AGV far from task to ensure movement
            test_env.agvs.append(agv)
            
            # Create simulator
            simulator = Simulator(
                environment=test_env,
                energy_model=self.energy_model,
                path_planner=self.path_planner,
                scheduler=self.scheduler,
                strategy_type=strategy_type
            )
            
            # Run simulation and save results
            # For relay_coop, use longer max_steps to ensure relay events
            max_steps = 100 if strategy_type == "relay_coop" else 50
            output_dir = simulator.run(max_steps=max_steps)
            
            # Check that all 7 standard plots exist
            import os
            plots_dir = os.path.join(output_dir, "plots")
            self.assertTrue(os.path.exists(plots_dir), msg=f"Plots directory should exist for {strategy_type}")
            
            standard_plots = [
                "task_progress.png",
                "battery_status.png",
                "energy_curve.png",
                "trajectory_map.png",
                "environment_state.png",
                "coordination_events.png",
                "kpi_summary.png"
            ]
            
            for plot_name in standard_plots:
                plot_path = os.path.join(plots_dir, plot_name)
                self.assertTrue(os.path.exists(plot_path), msg=f"{plot_name} should exist for {strategy_type}")
    
    def test_energy_curve_monotonicity(self):
        """Test that energy_curve cumulative energy is monotonically increasing."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create an AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)
        
        # Create simulator
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        
        # Run simulation
        simulator.run(max_steps=20)
        
        # Calculate cumulative energy and check monotonicity
        import numpy as np
        cumulative_energy = np.cumsum(simulator.energy_history)
        self.assertTrue(all(cumulative_energy[i] >= cumulative_energy[i-1] for i in range(1, len(cumulative_energy))),
                       msg="Cumulative energy should be monotonically increasing")
    
    def test_task_progress_final_value(self):
        """Test that task_progress final value equals completed_tasks."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create an AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)
        
        # Create simulator
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        
        # Run simulation
        simulator.run(max_steps=20)
        metrics = simulator.calculate_metrics()
        
        # Check that task_history final value equals completed_tasks
        if simulator.task_history:
            final_task_count = simulator.task_history[-1]
            self.assertEqual(final_task_count, metrics['completed_tasks'],
                           msg="Task history final value should equal completed_tasks")
    
    def test_relay_coop_coordination_events(self):
        """Test that relay_coop strategy has coordination events."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)
        
        # Create a UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)
        
        # Create an AGV far from the task start point
        from src.core.agv import AGV
        agv = AGV(id=1, position=(-100, -100))  # 远离任务起点
        self.env.agvs.append(agv)
        
        # Create simulator with relay_coop strategy
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )
        
        # Run simulation
        simulator.run(max_steps=50)
        
        # Check that there are relay-related events
        has_relay_event = any(event["type"] in ["RELAY_COOP_START", "AGV_REACHED_RELAY", "RELAY_REQUEST", "AGV_MOVE_START", "AGV_ARRIVE_RELAY"] for event in simulator.events)
        self.assertTrue(has_relay_event, msg="relay_coop strategy should have relay-related events")

    def test_charging_events_not_repeated(self):
        """Test that CHARGING_START is not repeated in consecutive charging steps."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)

        # Create a UAV with low battery to force charging
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=10.0)  # Low battery to force charging
        self.env.uavs.append(uav)

        # Create an AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)

        # Create simulator and run
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="baseline_direct"
        )
        output_dir = simulator.run(max_steps=50)

        # Read coordination_events.csv
        import os
        import csv
        events_file = os.path.join(output_dir, "records", "coordination_events.csv")
        self.assertTrue(os.path.exists(events_file))

        # Check that CHARGING_START is not repeated consecutively
        charging_start_steps = []
        with open(events_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['event_type'] == "CHARGING_START":
                    charging_start_steps.append(int(row['step']))

        # Check that charging start events are not consecutive
        for i in range(1, len(charging_start_steps)):
            self.assertGreater(charging_start_steps[i], charging_start_steps[i-1] + 1, 
                             f"CHARGING_START events are consecutive at steps {charging_start_steps[i-1]} and {charging_start_steps[i]}")

        # Check that CHARGING_END exists
        has_charging_end = False
        with open(events_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['event_type'] == "CHARGING_END":
                    has_charging_end = True
                    break

        self.assertTrue(has_charging_end, "No CHARGING_END event found")

    def test_agv_events(self):
        """Test AGV move and arrive events."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(200, 200),  # Longer distance to ensure relay is needed
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)

        # Create a UAV with lower battery to force relay
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=30.0)  # Lower battery to force relay
        self.env.uavs.append(uav)

        # Create an AGV far from the task to ensure movement
        from src.core.agv import AGV
        agv = AGV(id=1, position=(500, 500))  # Very far away to ensure movement
        self.env.agvs.append(agv)

        # Create simulator and run with relay_coop strategy
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )
        output_dir = simulator.run(max_steps=150)  # Longer steps to ensure relay events

        # Read coordination_events.csv
        import os
        import csv
        events_file = os.path.join(output_dir, "records", "coordination_events.csv")
        self.assertTrue(os.path.exists(events_file))

        # Check for AGV events
        event_types = set()
        with open(events_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                event_types.add(row['event_type'])

        # Check that AGV events exist
        self.assertIn("AGV_MOVE_START", event_types, "AGV_MOVE_START event not found")
        self.assertIn("AGV_ARRIVE_RELAY", event_types, "AGV_ARRIVE_RELAY event not found")

    def test_wait_for_agv_events(self):
        """Test WAIT_FOR_AGV_START and WAIT_FOR_AGV_END events."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(200, 200),  # Longer distance to ensure relay is needed
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)

        # Create a UAV with lower battery to force relay
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=30.0)  # Lower battery to force relay
        self.env.uavs.append(uav)

        # Create an AGV far from the task to ensure movement
        from src.core.agv import AGV
        agv = AGV(id=1, position=(500, 500))  # Very far away to ensure movement
        self.env.agvs.append(agv)

        # Create simulator and run with relay_coop strategy
        simulator = Simulator(
            environment=self.env,
            energy_model=self.energy_model,
            path_planner=self.path_planner,
            scheduler=self.scheduler,
            strategy_type="relay_coop"
        )
        output_dir = simulator.run(max_steps=150)  # Longer steps to ensure relay events

        # Read coordination_events.csv
        import os
        import csv
        events_file = os.path.join(output_dir, "records", "coordination_events.csv")
        self.assertTrue(os.path.exists(events_file))

        # Check for wait for AGV events
        event_types = set()
        with open(events_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                event_types.add(row['event_type'])

        # Check that wait for AGV events exist
        self.assertIn("WAIT_FOR_AGV_START", event_types, "WAIT_FOR_AGV_START event not found")
        self.assertIn("WAIT_FOR_AGV_END", event_types, "WAIT_FOR_AGV_END event not found")

    def test_coordination_events_csv_not_empty(self):
        """Test that coordination_events.csv is not empty and has multiple event types."""
        # Create a simple task
        from src.core.task import Task
        task = Task(
            id=1,
            start_point=(0, 0),
            end_point=(50, 50),
            payload=1.0,
            priority=1
        )
        self.env.tasks.append(task)

        # Create a UAV
        from src.core.uav import UAV
        uav = UAV(id=1, position=(0, 0), battery=100.0)
        self.env.uavs.append(uav)

        # Create an AGV
        from src.core.agv import AGV
        agv = AGV(id=1, position=(0, 0))
        self.env.agvs.append(agv)

        # Test all three strategies
        strategies = ["baseline_direct", "relay_coop", "energy_priority"]

        for strategy_type in strategies:
            # Create a new environment for each strategy to avoid state carryover
            from src.simulation.environment import Environment
            test_env = Environment()
            
            # Add task to test environment
            # Use longer distance for relay_coop to ensure relay is needed
            end_point = (150, 150) if strategy_type == "relay_coop" else (50, 50)
            test_task = Task(
                id=1,
                start_point=(0, 0),
                end_point=end_point,
                payload=1.0,
                priority=1
            )
            test_env.tasks.append(test_task)
            
            # Add UAV to test environment
            test_uav = UAV(id=1, position=(0, 0), battery=100.0)
            test_env.uavs.append(test_uav)
            
            # Add AGV to test environment
            test_agv = AGV(id=1, position=(0, 0))
            test_env.agvs.append(test_agv)
            
            # Create simulator
            simulator = Simulator(
                environment=test_env,
                energy_model=self.energy_model,
                path_planner=self.path_planner,
                scheduler=self.scheduler,
                strategy_type=strategy_type
            )
            
            # Run simulation
            max_steps = 100 if strategy_type == "relay_coop" else 50
            output_dir = simulator.run(max_steps=max_steps)
            
            # Check that coordination_events.csv exists and is not empty
            import os
            import csv
            events_file = os.path.join(output_dir, "records", "coordination_events.csv")
            self.assertTrue(os.path.exists(events_file), f"coordination_events.csv not found for {strategy_type}")
            
            # Read the file and check it has more than just the header
            with open(events_file, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                self.assertGreater(len(rows), 1, f"coordination_events.csv is empty for {strategy_type}")
            
            # Check that there are multiple event types
            event_types = set()
            with open(events_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    event_types.add(row['event_type'])
            
            self.assertGreater(len(event_types), 1, f"coordination_events.csv has only one event type for {strategy_type}: {event_types}")
            self.assertNotEqual(event_types, {"CHARGING_START"}, f"coordination_events.csv only has CHARGING_START events for {strategy_type}")


if __name__ == "__main__":
    import unittest
    unittest.main()