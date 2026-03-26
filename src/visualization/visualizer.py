import matplotlib.pyplot as plt

class Visualizer:
    """可视化类
    
    使用 matplotlib 绘制系统状态
    """
    
    def __init__(self):
        """初始化可视化器"""
        self.fig, self.ax = plt.subplots()
    
    def plot_system(self, environment, uavs, agvs, tasks):
        """绘制系统状态
        
        Args:
            environment: 环境对象
            uavs: 无人机列表
            agvs: AGV列表
            tasks: 任务列表
        """
        # 清空当前图
        self.ax.clear()
        
        # 绘制地图边界
        map_width, map_height = environment.map_size
        self.ax.set_xlim(0, map_width)
        self.ax.set_ylim(0, map_height)
        
        # 绘制配送点
        # 子类实现具体的配送点绘制逻辑
        
        # 绘制障碍物
        # 子类实现具体的障碍物绘制逻辑
        
        # 绘制无人机
        for uav in uavs:
            self.ax.plot(uav.position[0], uav.position[1], 'b^', markersize=10)
            # 标注无人机ID和电量
            self.ax.text(uav.position[0], uav.position[1] + 1, 
                        f'UAV {uav.id}\nBattery: {uav.battery}%', 
                        fontsize=8, ha='center')
        
        # 绘制AGV
        for agv in agvs:
            self.ax.plot(agv.position[0], agv.position[1], 'gs', markersize=10)
            # 标注AGV ID和状态
            self.ax.text(agv.position[0], agv.position[1] + 1, 
                        f'AGV {agv.id}\nStatus: {agv.status}', 
                        fontsize=8, ha='center')
        
        # 绘制任务
        for task in tasks:
            if task['status'] == 'pending':
                color = 'y'
            elif task['status'] == 'in_progress':
                color = 'c'
            else:
                color = 'g'
            
            # 绘制任务起点和终点
            self.ax.plot(task['start'][0], task['start'][1], f'{color}o', markersize=6)
            self.ax.plot(task['end'][0], task['end'][1], f'{color}x', markersize=6)
            # 绘制任务路径
            self.ax.plot([task['start'][0], task['end'][0]], 
                        [task['start'][1], task['end'][1]], 
                        f'{color}--', linewidth=1)
        
        # 设置标题和标签
        self.ax.set_title('UAV-AGV System Visualization')
        self.ax.set_xlabel('X Position')
        self.ax.set_ylabel('Y Position')
        
        # 显示网格
        self.ax.grid(True)
        
        # 暂停以更新显示
        plt.pause(0.1)
    
    def show(self):
        """显示可视化结果"""
        plt.show()