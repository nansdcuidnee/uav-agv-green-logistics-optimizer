from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from src.simulation.environment import Environment
from src.utils.result_layout import REQUIRED_ARTIFACTS, create_test_layout, write_metadata


class ResultGenerator:
    """Generate structured experiment artifacts under one run directory."""

    def __init__(
        self,
        environment: Environment,
        *,
        experiment_name: str = "main",
        timestamp: str | None = None,
    ) -> None:
        self.environment = environment
        self.layout = create_test_layout(test_name=experiment_name, timestamp=timestamp)
        self.output_dir = str(self.layout.run_dir)

    def generate_metrics(self) -> str:
        metrics = dict(self.environment.get_metrics())
        metrics.update(
            {
                "uav_energy": float(sum(max(0.0, 100.0 - uav.battery) for uav in self.environment.uavs)),
                "agv_energy": float(
                    sum(self._path_distance(getattr(agv, "path_history", [])) for agv in self.environment.agvs)
                ),
                "delay_rate": float(self._delay_rate()),
            }
        )

        file_path = self.layout.artifact_path("metrics.json")
        with file_path.open("w", encoding="utf-8") as file_obj:
            json.dump(metrics, file_obj, indent=2, ensure_ascii=False)
        return str(file_path)

    def generate_records(self) -> str:
        file_path = self.layout.artifact_path("records.csv")
        with file_path.open("w", newline="", encoding="utf-8") as file_obj:
            writer = csv.writer(file_obj)
            writer.writerow(
                [
                    "task_id",
                    "task_type",
                    "start_time",
                    "completion_time",
                    "execution_time",
                    "assigned_to",
                    "start_point",
                    "end_point",
                    "payload",
                    "priority",
                    "time_window",
                    "status",
                    "path_distance",
                ]
            )

            for task in self.environment.tasks:
                start_time = task.start_time if task.start_time is not None else ""
                completion_time = task.completion_time if task.completion_time is not None else ""
                execution_time = ""
                if task.start_time is not None and task.completion_time is not None:
                    execution_time = task.completion_time - task.start_time

                writer.writerow(
                    [
                        task.id,
                        task.task_type,
                        start_time,
                        completion_time,
                        execution_time,
                        self._assigned_to(task),
                        task.start_point,
                        task.end_point,
                        task.payload,
                        task.priority,
                        task.time_window,
                        task.status,
                        self._task_path_distance(task),
                    ]
                )

        return str(file_path)

    def generate_chart(self) -> str:
        metrics = self.environment.get_metrics()
        completed_tasks = [task for task in self.environment.tasks if task.status == "completed"]
        pending_tasks = [task for task in self.environment.tasks if task.status == "pending"]
        in_progress_tasks = [task for task in self.environment.tasks if task.status == "in_progress"]

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        axes[0, 0].bar(
            ["completed", "in_progress", "pending"],
            [len(completed_tasks), len(in_progress_tasks), len(pending_tasks)],
            color=["tab:green", "tab:blue", "tab:orange"],
        )
        axes[0, 0].set_title("Task Status")
        axes[0, 0].set_ylabel("Count")

        axes[0, 1].bar(
            ["uav", "agv"],
            [metrics.get("uav_utilization", 0.0), metrics.get("agv_utilization", 0.0)],
            color=["tab:purple", "tab:brown"],
        )
        axes[0, 1].set_title("Resource Utilization")
        axes[0, 1].set_ylim(0, 1)

        axes[1, 0].bar(
            ["on_time_rate", "delay_rate"],
            [metrics.get("on_time_rate", 0.0), self._delay_rate()],
            color=["tab:cyan", "tab:red"],
        )
        axes[1, 0].set_title("Timeliness")
        axes[1, 0].set_ylim(0, 1)

        axes[1, 1].scatter(
            [task.start_point[0] for task in self.environment.tasks],
            [task.start_point[1] for task in self.environment.tasks],
            label="start",
            color="tab:blue",
            alpha=0.7,
        )
        axes[1, 1].scatter(
            [task.end_point[0] for task in self.environment.tasks],
            [task.end_point[1] for task in self.environment.tasks],
            label="end",
            color="tab:red",
            alpha=0.7,
        )
        axes[1, 1].set_title("Task Points")
        axes[1, 1].legend()
        axes[1, 1].set_xlim(0, self.environment.map_size[0])
        axes[1, 1].set_ylim(0, self.environment.map_size[1])

        for axis in axes.flat:
            axis.grid(True, alpha=0.3)

        fig.tight_layout()
        file_path = self.layout.plot_path("chart.png")
        fig.savefig(file_path)
        plt.close(fig)
        return str(file_path)

    def generate_state_plot(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.set_xlim(0, self.environment.map_size[0])
        ax.set_ylim(0, self.environment.map_size[1])
        ax.set_title("Environment Snapshot")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.grid(True, alpha=0.3)

        for task in self.environment.tasks:
            ax.scatter(*task.start_point, color="tab:blue", s=20, alpha=0.7)
            ax.scatter(*task.end_point, color="tab:red", s=20, alpha=0.7)
            ax.plot(
                [task.start_point[0], task.end_point[0]],
                [task.start_point[1], task.end_point[1]],
                color="0.8",
                linestyle="--",
                linewidth=0.8,
            )

        for uav in self.environment.uavs:
            ax.scatter(*uav.position, color="tab:green", marker="^", s=80)

        for agv in self.environment.agvs:
            ax.scatter(*agv.position, color="tab:orange", marker="s", s=70)

        for obstacle in getattr(self.environment, "obstacles", []):
            circle = plt.Circle(obstacle.position, obstacle.radius, color="0.6", alpha=0.3)
            ax.add_patch(circle)

        for no_fly_zone in getattr(self.environment, "no_fly_zones", []):
            circle = plt.Circle(no_fly_zone.center, no_fly_zone.radius, color="tab:red", alpha=0.15)
            ax.add_patch(circle)

        file_path = self.layout.plot_path("environment_state.png")
        fig.tight_layout()
        fig.savefig(file_path)
        plt.close(fig)
        return str(file_path)

    def generate_map_visualization(self, num_tasks: int = 10, seed: int = 42, map_size: tuple[int, int] = (1000, 1000)) -> str:
        env = Environment(map_size=map_size)
        env.generate_tasks(num_tasks, seed=seed)

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.scatter(
            [task.start_point[0] for task in env.tasks],
            [task.start_point[1] for task in env.tasks],
            color="tab:blue",
            label="start",
            alpha=0.7,
        )
        ax.scatter(
            [task.end_point[0] for task in env.tasks],
            [task.end_point[1] for task in env.tasks],
            color="tab:red",
            label="end",
            alpha=0.7,
        )
        ax.set_xlim(0, map_size[0])
        ax.set_ylim(0, map_size[1])
        ax.set_title(f"Task Distribution ({num_tasks} tasks, seed={seed})")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.grid(True, alpha=0.3)
        ax.legend()

        file_path = self.layout.plot_path(f"map_visualization_{num_tasks}_{seed}.png")
        fig.tight_layout()
        fig.savefig(file_path)
        plt.close(fig)
        return str(file_path)

    def generate_all(self) -> dict[str, Any]:
        metrics_path = self.generate_metrics()
        records_path = self.generate_records()
        chart_path = self.generate_chart()

        plot_paths = [self.generate_state_plot()]
        map_paths = [self.generate_map_visualization(num_tasks=num_tasks, seed=42) for num_tasks in (10, 30, 50)]
        plot_paths.extend(map_paths)

        metadata_path = write_metadata(
            self.layout,
            {
                "experiment_name": self.layout.run_dir.parent.name,
                "timestamp": self.layout.run_dir.name,
                "records_granularity": "task",
                "required_artifacts": list(REQUIRED_ARTIFACTS),
                "plots": [str(Path(path).relative_to(self.layout.run_dir)) for path in plot_paths],
                "environment_summary": {
                    "map_size": list(self.environment.map_size),
                    "tasks": len(self.environment.tasks),
                    "uavs": len(self.environment.uavs),
                    "agvs": len(self.environment.agvs),
                    "current_time": self.environment.current_time,
                },
            },
        )

        return {
            "output_dir": str(self.layout.run_dir),
            "metrics": metrics_path,
            "records": records_path,
            "chart": chart_path,
            "metadata": metadata_path,
            "plots": plot_paths,
            "maps": map_paths,
        }

    def _delay_rate(self) -> float:
        completed_tasks = [task for task in self.environment.tasks if task.status == "completed"]
        if not completed_tasks:
            return 0.0
        delayed_tasks = [task for task in completed_tasks if task.completion_time and task.completion_time > task.time_window[1]]
        return len(delayed_tasks) / len(completed_tasks)

    @staticmethod
    def _path_distance(points: list[tuple[float, float]]) -> float:
        total = 0.0
        for start, end in zip(points, points[1:]):
            total += math.dist(start, end)
        return total

    def _task_path_distance(self, task) -> float:
        if task.assigned_uav:
            history = getattr(task.assigned_uav, "path_history", [])
            if history:
                return self._path_distance(history)
            return self._path_distance(getattr(task.assigned_uav, "path", []))
        if task.assigned_agv:
            history = getattr(task.assigned_agv, "path_history", [])
            if history:
                return self._path_distance(history)
            return self._path_distance(getattr(task.assigned_agv, "path", []))
        return 0.0

    @staticmethod
    def _assigned_to(task) -> str:
        if task.assigned_uav:
            return f"UAV:{task.assigned_uav.id}"
        if task.assigned_agv:
            return f"AGV:{task.assigned_agv.id}"
        return ""
