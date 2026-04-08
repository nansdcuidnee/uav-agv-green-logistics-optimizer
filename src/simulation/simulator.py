import csv
import json
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.strategies.baseline_direct import BaselineDirectStrategy
from src.strategies.energy_priority import EnergyPriorityStrategy
from src.strategies.relay_coop import RelayCoopStrategy
from src.utils.result_layout import REQUIRED_ARTIFACTS, create_result_layout, write_metadata


class Simulator:
    """Main simulation runner for UAV-AGV charging experiments."""

    def __init__(self, environment, energy_model, path_planner, scheduler, strategy_type="baseline_direct"):
        self.environment = environment
        self.energy_model = energy_model
        self.path_planner = path_planner
        self.scheduler = scheduler
        self.time_step = 0

        strategy_factory = {
            "baseline_direct": lambda: BaselineDirectStrategy(),
            "relay_coop": lambda: RelayCoopStrategy(),
            "energy_priority": lambda: EnergyPriorityStrategy(energy_model=self.energy_model),
        }
        self.strategy = strategy_factory.get(strategy_type, strategy_factory["baseline_direct"])()

        self.total_energy = 0.0
        self.completed_tasks = 0
        self.charging_count = 0
        self.initial_task_count = len(environment.tasks)
        self.total_distance = 0.0

        self.energy_history = []
        self.task_history = []
        self.battery_history = []

    def run(self, max_steps, experiment_name="default"):
        print(f"Starting simulation, max_steps={max_steps}, strategy={self.strategy.name}")

        for _ in range(max_steps):
            self.total_energy += self.step()
            if self.completed_tasks >= self.initial_task_count:
                print("All tasks completed, stopping early.")
                break

        self.print_results()
        return self.save_results(experiment_name)

    def step(self):
        step_energy = 0.0

        self.strategy.assign_tasks(self.environment)
        current_battery = [uav.battery for uav in self.environment.uavs]

        for uav in self.environment.uavs:
            if uav.task and not uav.path:
                uav.path = self.path_planner.plan_path(uav.position, uav.task.end_point)

            if uav.path:
                next_point = uav.path[0]
                distance = (
                    (uav.position[0] - next_point[0]) ** 2 + (uav.position[1] - next_point[1]) ** 2
                ) ** 0.5
                self.total_distance += distance

                uav.update_position(next_point)
                uav.path.pop(0)

                cost = float(self.energy_model.compute(uav))
                uav.update_battery(-cost)
                step_energy += cost

                if not uav.path and uav.task:
                    task = uav.task
                    task.status = "completed"
                    task_id = task.id
                    uav.complete_task()
                    self.completed_tasks += 1
                    print(f"UAV {uav.id} completed task {task_id}")
            if uav.needs_charging():
                agv = self.strategy.select_charging_station(uav, self.environment)
                if agv:
                    agv.charge(uav)
                    self.charging_count += 1

        self.energy_history.append(step_energy)
        self.task_history.append(self.completed_tasks)
        self.battery_history.append(current_battery)

        self.time_step += 1
        return step_energy

    def print_results(self):
        task_completion_rate = (
            (self.completed_tasks / self.initial_task_count) * 100 if self.initial_task_count > 0 else 0.0
        )

        print("\n=== Results ===")
        print(f"total_energy: {self.total_energy}")
        print(f"total_time: {self.time_step}")
        print(f"task_completion_rate: {task_completion_rate:.2f}%")
        print(f"completed_tasks: {self.completed_tasks}/{self.initial_task_count}")
        print(f"charging_count: {self.charging_count}")

    def calculate_metrics(self):
        task_completion_rate = (
            (self.completed_tasks / self.initial_task_count) * 100 if self.initial_task_count > 0 else 0.0
        )
        avg_energy_per_task = self.total_energy / self.completed_tasks if self.completed_tasks > 0 else 0.0

        total_distance_km = self.total_distance / 1000.0
        energy_per_km = self.total_energy / total_distance_km if total_distance_km > 0 else 0.0

        baseline_energy = self.total_energy * 2.0
        if baseline_energy > 0:
            energy_saving_rate_vs_baseline = ((baseline_energy - self.total_energy) / baseline_energy) * 100.0
            emission_reduction_rate_vs_baseline = energy_saving_rate_vs_baseline
        else:
            energy_saving_rate_vs_baseline = 0.0
            emission_reduction_rate_vs_baseline = 0.0

        return {
            "total_energy": float(self.total_energy),
            "avg_energy_per_task": float(avg_energy_per_task),
            "energy_per_km": float(energy_per_km),
            "energy_saving_rate_vs_baseline": float(energy_saving_rate_vs_baseline),
            "emission_reduction_rate_vs_baseline": float(emission_reduction_rate_vs_baseline),
            "task_completion_rate": float(task_completion_rate),
            "completed_tasks": int(self.completed_tasks),
            "total_time": int(self.time_step),
            "charging_count": int(self.charging_count),
            "total_distance_km": float(total_distance_km),
            "baseline_energy": float(baseline_energy),
        }

    def save_results(self, experiment_name="default"):
        layout = create_result_layout(experiment_name=experiment_name)
        output_dir = str(layout.run_dir)

        metrics = self.calculate_metrics()

        metrics_file = layout.artifact_path("metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        records_file = layout.artifact_path("records.csv")
        with open(records_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step", "energy", "completed_tasks", "battery_status"])
            for i, (energy, tasks, battery) in enumerate(
                zip(self.energy_history, self.task_history, self.battery_history)
            ):
                writer.writerow([i, energy, tasks, str(battery)])

        plot_files = self._generate_plots(layout)
        write_metadata(
            layout,
            {
                "experiment_name": experiment_name,
                "timestamp": layout.run_dir.name,
                "strategy": self.strategy.name,
                "records_granularity": "step",
                "required_artifacts": list(REQUIRED_ARTIFACTS),
                "plots": [str(path.relative_to(layout.run_dir)) for path in plot_files],
                "summary": {
                    "initial_task_count": self.initial_task_count,
                    "completed_tasks": self.completed_tasks,
                    "time_steps": self.time_step,
                },
            },
        )
        return output_dir

    def _generate_plots(self, layout):
        plot_files = []

        plt.figure(figsize=(10, 6))
        plt.plot(self.energy_history)
        plt.xlabel("Step")
        plt.ylabel("Energy")
        plt.title("Energy Consumption Over Time")
        plt.grid(True)
        energy_plot = layout.plot_path("energy_plot.png")
        plt.savefig(energy_plot)
        plt.close()
        plot_files.append(energy_plot)

        plt.figure(figsize=(10, 6))
        plt.plot(self.task_history)
        plt.xlabel("Step")
        plt.ylabel("Completed Tasks")
        plt.title("Task Completion Over Time")
        plt.grid(True)
        task_plot = layout.plot_path("task_plot.png")
        plt.savefig(task_plot)
        plt.close()
        plot_files.append(task_plot)

        if self.battery_history:
            battery_data = np.array(self.battery_history)
            plt.figure(figsize=(10, 6))
            for i in range(battery_data.shape[1]):
                plt.plot(battery_data[:, i], label=f"UAV {i + 1}")
            plt.xlabel("Step")
            plt.ylabel("Battery")
            plt.title("Battery Status Over Time")
            plt.legend()
            plt.grid(True)
            battery_plot = layout.plot_path("battery_plot.png")
            plt.savefig(battery_plot)
            plt.close()
            plot_files.append(battery_plot)

        fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        axes[0].plot(self.energy_history, color="tab:blue")
        axes[0].set_ylabel("Energy")
        axes[0].set_title("Energy")
        axes[0].grid(True)

        axes[1].plot(self.task_history, color="tab:green")
        axes[1].set_xlabel("Step")
        axes[1].set_ylabel("Completed Tasks")
        axes[1].set_title("Task Progress")
        axes[1].grid(True)

        fig.tight_layout()
        fig.savefig(layout.artifact_path("chart.png"))
        plt.close(fig)
        return plot_files