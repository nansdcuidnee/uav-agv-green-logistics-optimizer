import random

class Environment:
    """环境类
    
    包含地图信息、任务点、UAV和AGV的初始位置
    """
    
    def __init__(self):
        """初始化环境"""
        self.map_size = (1000, 1000)  # 地图大小
        self.tasks = []  # 配送任务列表
        self.uavs = []  # UAV列表
        self.agvs = []  # AGV列表
    
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
            task = {
                'id': i + 1,
                'start': (start_x, start_y),
                'end': (end_x, end_y),
                'status': 'pending'  # pending, in_progress, completed
            }
            self.tasks.append(task)
        
        return self.tasks
    
    def reset(self):
        """重置环境"""
        self.tasks = []
        self.uavs = []
        self.agvs = []