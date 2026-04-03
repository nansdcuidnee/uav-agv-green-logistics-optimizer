import random

from src.core.task import Task


class Environment:
    """Simulation environment that stores entities and tasks."""

    def __init__(self, map_size=(1000, 1000)):
        self.map_size = map_size
        self.tasks = []
        self.uavs = []
        self.agvs = []
        self.delivery_points = []

    def generate_tasks(self, num_tasks, seed=None):
        """Generate deterministic tasks when seed is provided."""
        rng = random.Random(seed) if seed is not None else random

        self.tasks = []
        for i in range(num_tasks):
            start_x = rng.randint(0, self.map_size[0])
            start_y = rng.randint(0, self.map_size[1])
            end_x = rng.randint(0, self.map_size[0])
            end_y = rng.randint(0, self.map_size[1])

            task = Task(
                task_id=i + 1,
                start_point=(start_x, start_y),
                end_point=(end_x, end_y),
                payload=1,
                priority=1,
            )
            self.tasks.append(task)

        self.delivery_points = [task.end_point for task in self.tasks]
        return self.tasks

    def reset(self):
        self.tasks = []
        self.uavs = []
        self.agvs = []
        self.delivery_points = []

    def add_delivery_point(self, point):
        self.delivery_points.append(point)

    def is_valid_position(self, position):
        x, y = position
        return 0 <= x <= self.map_size[0] and 0 <= y <= self.map_size[1]
