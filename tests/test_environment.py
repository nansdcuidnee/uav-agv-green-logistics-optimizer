import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.simulation.environment import Environment


def test_environment_seed_stable():
    """验证环境seed稳定性"""
    # 创建两个环境实例，使用相同的种子
    env1 = Environment()
    env2 = Environment()
    
    # 生成任务
    tasks1 = env1.generate_tasks(10, seed=42)
    tasks2 = env2.generate_tasks(10, seed=42)
    
    # 验证任务数量相同
    assert len(tasks1) == len(tasks2)
    
    # 验证任务属性相同
    for task1, task2 in zip(tasks1, tasks2):
        assert task1.id == task2.id
        assert task1.start_point == task2.start_point
        assert task1.end_point == task2.end_point
        assert abs(task1.payload - task2.payload) < 1e-6
        assert abs(task1.volume - task2.volume) < 1e-6
        assert task1.task_type == task2.task_type
        assert task1.priority == task2.priority
        assert abs(task1.time_window[0] - task2.time_window[0]) < 1e-6
        assert abs(task1.time_window[1] - task2.time_window[1]) < 1e-6


def test_task_schema_consistent():
    """验证任务结构一致性"""
    env = Environment()
    tasks = env.generate_tasks(5)
    
    # 验证所有任务都有相同的结构
    for task in tasks:
        # 验证任务属性存在
        assert hasattr(task, 'id')
        assert hasattr(task, 'start_point')
        assert hasattr(task, 'end_point')
        assert hasattr(task, 'payload')
        assert hasattr(task, 'volume')
        assert hasattr(task, 'task_type')
        assert hasattr(task, 'priority')
        assert hasattr(task, 'time_window')
        assert hasattr(task, 'status')
        assert hasattr(task, 'assigned_uav')
        assert hasattr(task, 'assigned_agv')
        assert hasattr(task, 'start_time')
        assert hasattr(task, 'completion_time')
        
        # 验证属性类型
        assert isinstance(task.id, int)
        assert isinstance(task.start_point, tuple)
        assert isinstance(task.end_point, tuple)
        assert isinstance(task.payload, float)
        assert isinstance(task.volume, float)
        assert isinstance(task.task_type, str)
        assert isinstance(task.priority, int)
        assert isinstance(task.time_window, tuple)
        assert isinstance(task.status, str)
        
        # 验证属性范围
        assert 1 <= task.priority <= 5
        assert task.time_window[0] < task.time_window[1]
        assert task.status in ['pending', 'in_progress', 'completed']