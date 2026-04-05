import random

from src.core.task import Task


class Environment:
    """Simulation environment that stores entities and tasks."""

    def __init__(self, map_size=(1000, 1000)):
<<<<<<< HEAD
        """初始化环境
        
        Args:
<<<<<<< HEAD
            map_size: 地图大小，默认值为(1000, 1000)
=======
            map_size: 地图尺寸 (width, height)
>>>>>>> dev
        """
        self.map_size = map_size  # 地图大小
        self.tasks = []  # 配送任务列表
        self.uavs = []  # UAV列表
        self.agvs = []  # AGV列表
<<<<<<< HEAD
        self.delivery_points = []  # 配送点列表
=======
        self.delivery_points = []  # 兼容旧接口
>>>>>>> dev
    
    def generate_tasks(self, num_tasks):
        """生成指定数量的配送任务
        
        Args:
            num_tasks: 任务数量
        """
=======
        self.map_size = map_size
        self.tasks = []
        self.uavs = []
        self.agvs = []
        self.delivery_points = []

    def generate_tasks(self, num_tasks, seed=None):
        """Generate deterministic tasks when seed is provided."""
        rng = random.Random(seed) if seed is not None else random

>>>>>>> dev
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
