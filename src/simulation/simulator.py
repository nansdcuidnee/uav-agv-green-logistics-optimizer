import csv
import json
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np

from src.strategies.baseline_direct import BaselineDirectStrategy
from src.strategies.energy_priority import EnergyPriorityStrategy
from src.strategies.relay_coop import RelayCoopStrategy


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
        print(f"开始模拟，总步数: {max_steps}")

        for _ in range(max_steps):
            self.total_energy += self.step()
            if self.completed_tasks >= self.initial_task_count:
                print("所有任务已完成，提前结束模拟")
                break

        self.print_results()
        return self.save_results(experiment_name)

    def step(self):
        total_energy = 0.0

        # Assign tasks according to selected strategy.
        self.strategy.assign_tasks(self.environment)

        current_battery = [uav.battery for uav in self.environment.uavs]

        for uav in self.environment.uavs:
            if uav.task and not uav.path:
                uav.path = self.path_planner.plan_path(uav.position, uav.task.end_point)
                print(f"为 UAV {uav.id} 规划路径")

            if uav.path:
                next_point = uav.path[0]
                distance = ((uav.position[0] - next_point[0]) ** 2 + (uav.position[1] - next_point[1]) ** 2) ** 0.5
                self.total_distance += distance

                uav.update_position(next_point)
                uav.path.pop(0)

                cost = self.energy_model.compute(uav)
                uav.update_battery(-cost)
                total_energy += cost
                print(f"UAV {uav.id} 电量: {uav.battery}")

                if not uav.path and uav.task:
<<<<<<< HEAD
                    task_id = uav.task['id']
                    uav.task['status'] = 'completed'
=======
                    task = uav.task
                    task.status = "completed"
                    task_id = task.id
                    uav.complete_task()
>>>>>>> dev
                    self.completed_tasks += 1
                    uav.complete_task()
                    print(f"UAV {uav.id} 完成任务 {task_id}")
<<<<<<< HEAD
            
            # 8. 判断电量是否低于阈值
=======

>>>>>>> dev
            if uav.needs_charging():
                print(f"UAV {uav.id} 触发充电！")
                agv = self.strategy.select_charging_station(uav, self.environment)
                if agv:
                    agv.charge(uav)
                    self.charging_count += 1
                    print(f"UAV {uav.id} 充电后电量: {uav.battery}")

        self.energy_history.append(total_energy)
        self.task_history.append(self.completed_tasks)
        self.battery_history.append(current_battery)

        self.time_step += 1
        return total_energy

    def print_results(self):
        task_completion_rate = (self.completed_tasks / self.initial_task_count) * 100 if self.initial_task_count > 0 else 0

        print("\n=== 实验结果 ===")
        print(f"总能耗: {self.total_energy}")
        print(f"总时间: {self.time_step}")
        print(f"任务完成率: {task_completion_rate:.2f}%")
        print(f"完成任务数: {self.completed_tasks}/{self.initial_task_count}")
        print(f"充电次数: {self.charging_count}")
        print("===============")

    def calculate_metrics(self):
        task_completion_rate = (self.completed_tasks / self.initial_task_count) * 100 if self.initial_task_count > 0 else 0
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
            "total_energy": self.total_energy,
            "avg_energy_per_task": avg_energy_per_task,
            "energy_per_km": energy_per_km,
            "energy_saving_rate_vs_baseline": energy_saving_rate_vs_baseline,
            "emission_reduction_rate_vs_baseline": emission_reduction_rate_vs_baseline,
            "task_completion_rate": task_completion_rate,
            "completed_tasks": self.completed_tasks,
            "total_time": self.time_step,
            "charging_count": self.charging_count,
            "total_distance_km": total_distance_km,
            "baseline_energy": baseline_energy,
        }

    def save_results(self, experiment_name="default"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join("results", experiment_name, timestamp)
        os.makedirs(output_dir, exist_ok=True)

        metrics = self.calculate_metrics()

        metrics_file = os.path.join(output_dir, "metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"指标已保存到: {metrics_file}")

        records_file = os.path.join(output_dir, "records.csv")
        with open(records_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step", "energy", "completed_tasks", "battery_status"])
            for i, (energy, tasks, battery) in enumerate(
                zip(self.energy_history, self.task_history, self.battery_history)
            ):
                writer.writerow([i, energy, tasks, str(battery)])
        print(f"记录已保存到: {records_file}")

        self._generate_plots(output_dir)
        return output_dir

    def _generate_plots(self, output_dir):
        # legacy artifacts kept for compatibility
        plt.figure(figsize=(10, 6))
        plt.plot(self.energy_history)
        plt.xlabel("Step")
        plt.ylabel("Energy")
        plt.title("Energy Consumption Over Time")
        plt.grid(True)
        energy_plot = os.path.join(output_dir, "energy_plot.png")
        plt.savefig(energy_plot)
        plt.close()

        plt.figure(figsize=(10, 6))
        plt.plot(self.task_history)
        plt.xlabel("Step")
        plt.ylabel("Completed Tasks")
        plt.title("Task Completion Over Time")
        plt.grid(True)
        task_plot = os.path.join(output_dir, "task_plot.png")
        plt.savefig(task_plot)
        plt.close()

        battery_plot = None
        if self.battery_history:
            battery_data = np.array(self.battery_history)
            plt.figure(figsize=(10, 6))
            for i in range(battery_data.shape[1]):
                plt.plot(battery_data[:, i], label=f"UAV {i+1}")
            plt.xlabel("Step")
            plt.ylabel("Battery")
            plt.title("Battery Status Over Time")
            plt.legend()
            plt.grid(True)
            battery_plot = os.path.join(output_dir, "battery_plot.png")
            plt.savefig(battery_plot)
            plt.close()

        # required artifact
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
        chart_path = os.path.join(output_dir, "chart.png")
        fig.savefig(chart_path)
        plt.close(fig)

        print(f"图表已保存到: {output_dir}")
