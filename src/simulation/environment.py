import random
from src.core.task import Task

class Environment:
    """环境类
    
    包含地图信息、任务点、UAV和AGV的初始位置
    """
    
    def __init__(self, map_size=(1000, 1000)):
        """初始化环境
        
        Args:
            map_size: 地图尺寸 (width, height)
        """
        self.map_size = map_size  # 地图大小
        self.tasks = []  # 配送任务列表
        self.uavs = []  # UAV列表
        self.agvs = []  # AGV列表
        self.delivery_points = []  # 兼容旧接口
    
    def generate_tasks(self, num_tasks):
        """生成指定数量的配送任务
        
        Args:
            num_tasks: 任务数量
        """
        self.tasks = []
        for i in range(num_tasks):
            # 随机生成起点和终点
            start_x = random.randint(0, self.map_size[0])
            start_y = random.randint(0, self.map_size[1])
            end_x = random.randint(0, self.map_size[0])
            end_y = random.randint(0, self.map_size[1])
            
            # 创建任务对象
            task = Task(
                task_id=i + 1,
                start_point=(start_x, start_y),
                end_point=(end_x, end_y),
                payload=1,
                priority=1
            )
            self.tasks.append(task)
        
        # 同时更新配送点列表，兼容旧接口
        self.delivery_points = [task.end_point for task in self.tasks]
        
        return self.tasks
    
    def reset(self):
        """重置环境"""
        self.tasks = []
        self.uavs = []
        self.agvs = []
        self.delivery_points = []
    
    def add_delivery_point(self, point):
        """添加配送点（兼容旧接口）
        
        Args:
            point: 配送点位置 (x, y)
        """
        self.delivery_points.append(point)
    
    def is_valid_position(self, position):
        """检查位置是否有效（兼容旧接口）
        
        Args:
            position: 位置 (x, y)
            
        Returns:
            bool: 是否有效
        """
        x, y = position
        return 0 <= x <= self.map_size[0] and 0 <= y <= self.map_size[1]