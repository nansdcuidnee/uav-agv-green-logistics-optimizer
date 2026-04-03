import pytest
import os
from src.visualization.visualizer import Visualizer
from src.simulation.environment import Environment
from src.core.uav import UAV
from src.core.agv import AGV


def test_visualizer_initialization():
    """测试可视化器初始化"""
    visualizer = Visualizer()
    assert visualizer is not None


def test_visualizer_plot_system():
    """测试系统状态可视化"""
    visualizer = Visualizer()
    environment = Environment()

    # 添加 UAV
    uav1 = UAV(uav_id=1, position=(0, 0))
    uav2 = UAV(uav_id=2, position=(100, 100))
    environment.uavs = [uav1, uav2]

    # 添加 AGV
    agv1 = AGV(agv_id=1, position=(50, 50))
    agvs = [agv1]

    # 添加任务
    tasks = [{
        'id': 1,
        'start': (0, 0),
        'end': (100, 100),
        'status': 'pending'
    }]

    # 测试系统状态可视化
    visualizer.plot_system(environment, [uav1, uav2], agvs, tasks)
    visualizer.show()