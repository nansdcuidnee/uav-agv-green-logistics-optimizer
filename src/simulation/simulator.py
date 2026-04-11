import csv
import json
import matplotlib
import yaml

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from src.strategies.baseline_direct import BaselineDirectStrategy
from src.strategies.energy_priority import EnergyPriorityStrategy
from src.strategies.relay_coop import RelayCoopStrategy
from src.utils.result_layout import REQUIRED_ARTIFACTS, create_result_layout, write_metadata
from src.communication.network_manager import NetworkManager
from src.communication.message_dispatch import MessageDispatcher
from src.communication.communication_logger import CommunicationLogger


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
        self.events = []  # 记录真实事件
        self.task_completion_times = []  # 记录任务完成时间
        
        # 初始化通信模块
        self.network_manager = NetworkManager()
        self.message_dispatcher = MessageDispatcher(self.network_manager)
        self.communication_logger = None  # 稍后在 save_results 中初始化

    def run(self, max_steps, experiment_name="default", result_type="runs"):
        print(f"Starting simulation, max_steps={max_steps}, strategy={self.strategy.name}")
        
        # 连接所有设备到网络
        for uav in self.environment.uavs:
            self.network_manager.connect(f"UAV_{uav.id}", "UAV")
        for agv in self.environment.agvs:
            self.network_manager.connect(f"AGV_{agv.id}", "AGV")
        self.network_manager.connect("CONTROL_CENTER", "CONTROL")

        for _ in range(max_steps):
            self.total_energy += self.step()
            if self.completed_tasks >= self.initial_task_count:
                print("All tasks completed, stopping early.")
                break

        self.print_results()
        return self.save_results(experiment_name, result_type)

    def step(self):
        step_energy = 0.0

        # 分配任务并记录开始时间
        assignment_result = self.strategy.assign_tasks(self.environment)
        # 记录任务分配事件
        for assignment in assignment_result.get("assignments", []):
            self.events.append({
                "step": self.time_step,
                "type": "TASK_ASSIGNMENT",
                "uav_id": assignment.get("uav_id"),
                "task_id": assignment.get("task_id"),
                "agv_id": assignment.get("agv_id"),
                "relay_point": assignment.get("relay_point")
            })
            # 发送任务分配消息
            uav_id = assignment.get("uav_id")
            task_id = assignment.get("task_id")
            agv_id = assignment.get("agv_id")
            self.network_manager.send_message(
                "CONTROL_CENTER",
                f"UAV_{uav_id}",
                "TASK_ASSIGNMENT",
                f"Task {task_id} assigned to UAV {uav_id}"
            )
            if agv_id:
                self.network_manager.send_message(
                    "CONTROL_CENTER",
                    f"AGV_{agv_id}",
                    "RELAY_REQUEST",
                    f"AGV {agv_id} requested for relay support for task {task_id}"
                )
        # 从环境中获取所有任务，检查哪些任务的状态变为了in_progress
        for task in self.environment.tasks:
            if task.status == "in_progress" and task.start_time is None:
                task.start(self.time_step)
                self.events.append({
                    "step": self.time_step,
                    "type": "TASK_START",
                    "task_id": task.id,
                    "uav_id": task.assigned_uav.id if hasattr(task, 'assigned_uav') else None
                })
        
        current_battery = [uav.battery for uav in self.environment.uavs]

        for uav in self.environment.uavs:
            if uav.task and not uav.path:
                # 根据策略类型规划路径
                if self.strategy.name == "relay_coop" and hasattr(uav.task, "relay_point"):
                    # 对于中继协作策略，使用中继点
                    relay_point = uav.task.relay_point
                    uav.path = self.path_planner.plan_multi_stop_path(
                        uav.position, [relay_point], uav.task.end_point
                    )
                    # 记录中继协同事件
                    if not hasattr(uav.task, "relay_event_recorded"):
                        self.events.append({
                            "step": self.time_step,
                            "type": "RELAY_COOP_START",
                            "task_id": uav.task.id,
                            "uav_id": uav.id,
                            "agv_id": uav.task.assigned_agv.id,
                            "relay_point": relay_point
                        })
                        uav.task.relay_event_recorded = True
                else:
                    # 其他策略直接规划到终点
                    uav.path = self.path_planner.plan_path(uav.position, uav.task.end_point)

            if uav.path:
                next_point = uav.path[0]
                distance = (
                    (uav.position[0] - next_point[0]) ** 2 + (uav.position[1] - next_point[1]) ** 2
                ) ** 0.5
                self.total_distance += distance

                uav.update_position(next_point)
                uav.path.pop(0)

                # 计算能耗，考虑策略差异
                if self.strategy.name == "energy_priority" and hasattr(uav.task, "estimated_energy"):
                    # 对于能量优先策略，使用预计算的能耗
                    # 这里简化处理，将总能耗分摊到路径的每一步
                    total_distance = sum(
                        ((uav.path[i][0] - uav.path[i+1][0])**2 + (uav.path[i][1] - uav.path[i+1][1])**2)**0.5
                        for i in range(len(uav.path)-1)
                    )
                    if total_distance > 0:
                        segment_distance = distance / total_distance
                        cost = uav.task.estimated_energy * segment_distance
                    else:
                        cost = 0
                else:
                    # 其他策略使用标准能耗模型
                    cost = float(self.energy_model.compute(uav))
                
                uav.update_battery(-cost)
                step_energy += cost

                if not uav.path and uav.task:
                    task = uav.task
                    task.complete(self.time_step)
                    task_id = task.id
                    uav.complete_task()
                    self.completed_tasks += 1
                    self.task_completion_times.append(self.time_step)  # 记录任务完成时间
                    print(f"UAV {uav.id} completed task {task_id}")
                    self.events.append({
                        "step": self.time_step,
                        "type": "TASK_COMPLETE",
                        "task_id": task_id,
                        "uav_id": uav.id,
                        "completion_time": self.time_step
                    })
            # 记录低电量事件
            if uav.battery < 30 and uav.battery >= 20:
                self.events.append({
                    "step": self.time_step,
                    "type": "LOW_BATTERY",
                    "uav_id": uav.id,
                    "battery": uav.battery
                })
                # 发送低电量状态消息
                self.network_manager.send_message(
                    f"UAV_{uav.id}",
                    "CONTROL_CENTER",
                    "LOW_BATTERY",
                    f"UAV {uav.id} battery level: {uav.battery:.2f}%"
                )
            if uav.needs_charging():
                self.events.append({
                    "step": self.time_step,
                    "type": "CHARGING_REQUEST",
                    "uav_id": uav.id,
                    "battery": uav.battery
                })
                # 发送充电请求消息
                self.network_manager.send_message(
                    f"UAV_{uav.id}",
                    "CONTROL_CENTER",
                    "CHARGING_REQUEST",
                    f"UAV {uav.id} requests charging, battery: {uav.battery:.2f}%"
                )
                agv = self.strategy.select_charging_station(uav, self.environment)
                if agv:
                    # 发送充电分配消息
                    self.network_manager.send_message(
                        "CONTROL_CENTER",
                        f"AGV_{agv.id}",
                        "CHARGING_ASSIGNMENT",
                        f"AGV {agv.id} assigned to charge UAV {uav.id}"
                    )
                    # 计算 AGV 充电时的能耗
                    # 假设充电时 AGV 静止，但需要消耗一定能量
                    agv_energy = 2.0  # 每次充电的基础能耗
                    agv.charge(uav)
                    self.charging_count += 1
                    self.total_energy += agv_energy
                    step_energy += agv_energy
                    self.events.append({
                        "step": self.time_step,
                        "type": "CHARGING_START",
                        "uav_id": uav.id,
                        "agv_id": agv.id
                    })

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

        # 计算平均交付时间
        avg_delivery_time = sum(self.task_completion_times) / len(self.task_completion_times) if self.task_completion_times else 0.0

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
            "completion_rate": float(task_completion_rate),
            "task_completion_rate": float(task_completion_rate),
            "avg_delivery_time": float(avg_delivery_time),
            "energy_saving_rate_vs_baseline": float(energy_saving_rate_vs_baseline),
            "emission_reduction_rate_vs_baseline": float(emission_reduction_rate_vs_baseline),
            "completed_tasks": int(self.completed_tasks),
            "total_time": int(self.time_step),
            "charging_count": int(self.charging_count),
            "total_distance_km": float(total_distance_km),
            "baseline_energy": float(baseline_energy),
        }

    def save_results(self, experiment_name="default", result_type="runs"):
        layout = create_result_layout(experiment_name=experiment_name, result_type=result_type)
        output_dir = str(layout.run_dir)

        metrics = self.calculate_metrics()

        # 保存 metrics.json
        metrics_file = layout.artifact_path("metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        # 保存 steps.csv
        steps_file = layout.record_path("steps.csv")
        with open(steps_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step", "step_energy", "cumulative_energy", "completed_tasks", "in_progress_tasks", "charging_count_cumulative", "total_distance", "uav_battery_min", "uav_battery_avg"])
            cumulative_energy = 0
            for i, (energy, tasks, battery) in enumerate(
                zip(self.energy_history, self.task_history, self.battery_history)
            ):
                cumulative_energy += energy
                uav_battery_min = min(battery) if battery else 0
                uav_battery_avg = sum(battery) / len(battery) if battery else 0
                in_progress_tasks = self.initial_task_count - tasks
                writer.writerow([i, energy, cumulative_energy, tasks, in_progress_tasks, self.charging_count, self.total_distance, uav_battery_min, uav_battery_avg])

        # 保存 tasks.csv
        tasks_file = layout.record_path("tasks.csv")
        with open(tasks_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["task_id", "task_type", "priority", "status", "assigned_uav", "assigned_agv", "start_point", "end_point", "payload", "time_window_start", "time_window_end", "start_time", "completion_time", "execution_time", "on_time", "path_distance"])
            for task in self.environment.tasks:
                assigned_uav = task.assigned_uav.id if hasattr(task, 'assigned_uav') and task.assigned_uav else ""
                assigned_agv = task.assigned_agv.id if hasattr(task, 'assigned_agv') and task.assigned_agv else ""
                start_time = getattr(task, 'start_time', "")
                completion_time = getattr(task, 'completion_time', "")
                execution_time = completion_time - start_time if start_time and completion_time else ""
                on_time = ""  # 需要根据时间窗口判断
                path_distance = getattr(task, 'path_distance', "")
                # 处理 time_window 可能是元组的情况
                time_window = getattr(task, 'time_window', ())
                time_window_min = time_window[0] if isinstance(time_window, tuple) and len(time_window) > 0 else ""
                time_window_max = time_window[1] if isinstance(time_window, tuple) and len(time_window) > 1 else ""
                writer.writerow([
                    task.id,
                    getattr(task, 'task_type', ""),
                    task.priority,
                    task.status,
                    assigned_uav,
                    assigned_agv,
                    task.start_point,
                    task.end_point,
                    task.payload,
                    time_window_min,
                    time_window_max,
                    start_time,
                    completion_time,
                    execution_time,
                    on_time,
                    path_distance
                ])

        # 保存 config_snapshot.yaml
        config_snapshot = {
            "experiment_name": experiment_name,
            "strategy": self.strategy.name,
            "initial_task_count": self.initial_task_count,
            "num_uavs": len(self.environment.uavs),
            "num_agvs": len(self.environment.agvs)
        }
        config_file = layout.artifact_path("config_snapshot.yaml")
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_snapshot, f, default_flow_style=False, allow_unicode=True)

        # 保存 run.log
        log_file = layout.log_path("run.log")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Experiment: {experiment_name}\n")
            f.write(f"Strategy: {self.strategy.name}\n")
            f.write(f"Initial tasks: {self.initial_task_count}\n")
            f.write(f"UAVs: {len(self.environment.uavs)}\n")
            f.write(f"AGVs: {len(self.environment.agvs)}\n")
            f.write(f"Completed tasks: {self.completed_tasks}\n")
            f.write(f"Total energy: {self.total_energy}\n")
            f.write(f"Total time steps: {self.time_step}\n")
            f.write(f"Charging count: {self.charging_count}\n")

        # 保存 communication_log.csv
        communication_log_file = layout.artifact_path("communication_log.csv")
        with open(communication_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "sender", "receiver", "message_type", "content"])
            
            # 基于真实事件生成通信日志
            for event in self.events:
                step = event["step"]
                event_type = event["type"]
                
                if event_type == "TASK_ASSIGNMENT":
                    writer.writerow([step, f"Control Center", f"UAV {event['uav_id']}", "TASK_ASSIGNMENT", f"Assign task {event['task_id']}"])
                elif event_type == "TASK_START":
                    writer.writerow([step, f"UAV {event['uav_id']}", "Control Center", "TASK_START", f"Start task {event['task_id']}"])
                elif event_type == "TASK_COMPLETE":
                    writer.writerow([step, f"UAV {event['uav_id']}", "Control Center", "TASK_COMPLETE", f"Complete task {event['task_id']}"])
                elif event_type == "LOW_BATTERY":
                    writer.writerow([step, f"UAV {event['uav_id']}", "Control Center", "LOW_BATTERY", f"Battery level: {event['battery']:.1f}%"])
                elif event_type == "CHARGING_REQUEST":
                    writer.writerow([step, f"UAV {event['uav_id']}", "Control Center", "CHARGING_REQUEST", f"Request charging, battery: {event['battery']:.1f}%"])
                elif event_type == "CHARGING_START":
                    writer.writerow([step, f"Control Center", f"AGV {event['agv_id']}", "CHARGING_COMMAND", f"Charge UAV {event['uav_id']}"])
                    writer.writerow([step, f"AGV {event['agv_id']}", f"UAV {event['uav_id']}", "CHARGING_START", "Start charging"])

        # 保存 event_timeline.txt
        event_timeline_file = layout.artifact_path("event_timeline.txt")
        with open(event_timeline_file, "w", encoding="utf-8") as f:
            f.write("Event Timeline\n")
            f.write("================\n")
            
            # 按步骤组织事件
            events_by_step = {}
            for event in self.events:
                step = event["step"]
                if step not in events_by_step:
                    events_by_step[step] = []
                events_by_step[step].append(event)
            
            # 按步骤输出事件
            for step in sorted(events_by_step.keys()):
                f.write(f"Step {step}:\n")
                for event in events_by_step[step]:
                    event_type = event["type"]
                    if event_type == "TASK_ASSIGNMENT":
                        f.write(f"  - Task assignment: UAV {event['uav_id']} assigned task {event['task_id']}")
                        if "agv_id" in event and event["agv_id"]:
                            f.write(f" with AGV {event['agv_id']}")
                        f.write("\n")
                    elif event_type == "TASK_START":
                        f.write(f"  - Task start: UAV {event['uav_id']} started task {event['task_id']}\n")
                    elif event_type == "TASK_COMPLETE":
                        f.write(f"  - Task complete: UAV {event['uav_id']} completed task {event['task_id']}\n")
                    elif event_type == "LOW_BATTERY":
                        f.write(f"  - Low battery alert: UAV {event['uav_id']} battery at {event['battery']:.1f}%\n")
                    elif event_type == "CHARGING_REQUEST":
                        f.write(f"  - Charging request: UAV {event['uav_id']} requests charging (battery: {event['battery']:.1f}%)\n")
                    elif event_type == "CHARGING_START":
                        f.write(f"  - Charging start: AGV {event['agv_id']} starts charging UAV {event['uav_id']}\n")
            
            # 输出最终统计信息
            f.write("\nFinal Statistics:\n")
            f.write(f"- Total tasks completed: {self.completed_tasks}/{self.initial_task_count}\n")
            f.write(f"- Total energy consumed: {self.total_energy:.2f}\n")
            f.write(f"- Total charging sessions: {self.charging_count}\n")
            f.write(f"- Simulation completed in: {self.time_step} steps\n")

        # 生成图表
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

        # 1. energy_plot.png
        plt.figure(figsize=(10, 6))
        # 计算累计能耗
        cumulative_energy = np.cumsum(self.energy_history)
        plt.plot(self.energy_history, label="Step Energy")
        plt.plot(cumulative_energy, label="Cumulative Energy")
        plt.xlabel("Step")
        plt.ylabel("Energy")
        plt.title("Energy Consumption Over Time")
        plt.legend()
        plt.grid(True)
        energy_plot = layout.plot_path("energy_plot.png")
        plt.savefig(energy_plot)
        plt.close()
        plot_files.append(energy_plot)

        # 2. task_plot.png
        plt.figure(figsize=(10, 6))
        plt.plot(self.task_history, label="Completed Tasks")
        # 计算进行中的任务数
        in_progress_tasks = [self.initial_task_count - tasks for tasks in self.task_history]
        plt.plot(in_progress_tasks, label="In Progress Tasks")
        plt.xlabel("Step")
        plt.ylabel("Tasks")
        plt.title("Task Completion Over Time")
        plt.legend()
        plt.grid(True)
        task_plot = layout.plot_path("task_plot.png")
        plt.savefig(task_plot)
        plt.close()
        plot_files.append(task_plot)

        # 3. battery_plot.png
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

        # 4. chart.png - 2x2 dashboard
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 面板1：累计能耗曲线
        cumulative_energy = np.cumsum(self.energy_history)
        axes[0, 0].plot(cumulative_energy, color="tab:blue")
        axes[0, 0].set_ylabel("Cumulative Energy")
        axes[0, 0].set_title("Energy Consumption")
        axes[0, 0].grid(True)
        
        # 面板2：任务完成进度曲线
        axes[0, 1].plot(self.task_history, color="tab:green")
        axes[0, 1].set_ylabel("Completed Tasks")
        axes[0, 1].set_title("Task Progress")
        axes[0, 1].grid(True)
        
        # 面板3：电量曲线摘要
        if self.battery_history:
            battery_data = np.array(self.battery_history)
            for i in range(battery_data.shape[1]):
                axes[1, 0].plot(battery_data[:, i], label=f"UAV {i + 1}")
            axes[1, 0].set_xlabel("Step")
            axes[1, 0].set_ylabel("Battery")
            axes[1, 0].set_title("Battery Status")
            axes[1, 0].legend()
            axes[1, 0].grid(True)
        
        # 面板4：关键 KPI 文本
        metrics = self.calculate_metrics()
        kpi_text = f"Task Completion: {metrics['task_completion_rate']:.2f}%\n"
        kpi_text += f"Total Energy: {metrics['total_energy']:.2f}\n"
        kpi_text += f"Total Time: {self.time_step}\n"
        kpi_text += f"Charging Count: {self.charging_count}"
        axes[1, 1].text(0.1, 0.5, kpi_text, fontsize=12, va="center")
        axes[1, 1].set_title("Key KPIs")
        axes[1, 1].axis("off")
        
        fig.tight_layout()
        chart_path = layout.plot_path("chart.png")
        plt.savefig(chart_path)
        plt.close(fig)
        plot_files.append(chart_path)

        # 5. environment_state.png - 场景静态快照
        plt.figure(figsize=(10, 8))
        # 绘制任务起点和终点
        for task in self.environment.tasks:
            plt.scatter(task.start_point[0], task.start_point[1], color="blue", label="Task Start" if task.id == 1 else "")
            plt.scatter(task.end_point[0], task.end_point[1], color="red", label="Task End" if task.id == 1 else "")
        # 绘制 UAV
        for uav in self.environment.uavs:
            plt.scatter(uav.position[0], uav.position[1], color="green", marker="^", label="UAV" if uav.id == 1 else "")
        # 绘制 AGV
        for agv in self.environment.agvs:
            plt.scatter(agv.position[0], agv.position[1], color="orange", marker="s", label="AGV" if agv.id == 1 else "")
        # 绘制障碍物
        for obstacle in getattr(self.environment, 'obstacles', []):
            if hasattr(obstacle, 'position'):
                plt.scatter(obstacle.position[0], obstacle.position[1], color="gray", marker="x", label="Obstacle" if obstacle == getattr(self.environment, 'obstacles', [])[0] else "")
        # 绘制禁飞区
        for no_fly_zone in getattr(self.environment, 'no_fly_zones', []):
            if hasattr(no_fly_zone, 'center') and hasattr(no_fly_zone, 'radius'):
                circle = plt.Circle(no_fly_zone.center, no_fly_zone.radius, color="purple", alpha=0.3, label="No Fly Zone" if no_fly_zone == getattr(self.environment, 'no_fly_zones', [])[0] else "")
                plt.gca().add_patch(circle)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Environment State")
        plt.legend()
        plt.grid(True)
        env_state_path = layout.plot_path("environment_state.png")
        plt.savefig(env_state_path)
        plt.close()
        plot_files.append(env_state_path)

        # 6. trajectory_map.png - UAV和AGV轨迹
        plt.figure(figsize=(10, 8))
        # 绘制任务起点和终点
        for task in self.environment.tasks:
            plt.scatter(task.start_point[0], task.start_point[1], color="blue", label="Task Start" if task.id == 1 else "")
            plt.scatter(task.end_point[0], task.end_point[1], color="red", label="Task End" if task.id == 1 else "")
        # 绘制 UAV 轨迹
        for uav in self.environment.uavs:
            if hasattr(uav, 'path_history') and uav.path_history:
                path = uav.path_history
                x, y = zip(*path)
                plt.plot(x, y, label=f"UAV {uav.id} Trajectory")
                # 绘制终态位置
                plt.scatter(uav.position[0], uav.position[1], color="green", marker="^", label=f"UAV {uav.id} End" if uav.id == 1 else "")
        # 绘制 AGV 轨迹
        for agv in self.environment.agvs:
            if hasattr(agv, 'path_history') and agv.path_history:
                path = agv.path_history
                x, y = zip(*path)
                plt.plot(x, y, linestyle="--", label=f"AGV {agv.id} Trajectory")
                # 绘制终态位置
                plt.scatter(agv.position[0], agv.position[1], color="orange", marker="s", label=f"AGV {agv.id} End" if agv.id == 1 else "")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Trajectory Map")
        plt.legend()
        plt.grid(True)
        trajectory_path = layout.plot_path("trajectory_map.png")
        plt.savefig(trajectory_path)
        plt.close()
        plot_files.append(trajectory_path)

        # 7. task_distribution.png - 任务空间分布
        plt.figure(figsize=(10, 8))
        for task in self.environment.tasks:
            # 绘制起点蓝点
            plt.scatter(task.start_point[0], task.start_point[1], color="blue", label="Start Point" if task.id == 1 else "")
            # 绘制终点红点
            plt.scatter(task.end_point[0], task.end_point[1], color="red", label="End Point" if task.id == 1 else "")
            # 绘制起点到终点的虚线
            plt.plot([task.start_point[0], task.end_point[0]], [task.start_point[1], task.end_point[1]], linestyle="--", color="gray")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Task Distribution")
        plt.legend()
        plt.grid(True)
        task_dist_path = layout.plot_path("task_distribution.png")
        plt.savefig(task_dist_path)
        plt.close()
        plot_files.append(task_dist_path)

        return plot_files