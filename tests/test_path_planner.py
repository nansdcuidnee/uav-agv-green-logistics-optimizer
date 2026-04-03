import pytest
from src.planning.path_planner import PathPlanner


def test_path_planner_plan_path():
    """测试路径规划"""
    path_planner = PathPlanner()
    start = (0, 0)
    end = (100, 100)

    path = path_planner.plan_path(start, end)
    assert isinstance(path, list)
    assert len(path) > 0
    assert path[-1] == end  # 检查路径的终点

def test_path_planner_plan():
    """测试批量路径规划"""
    path_planner = PathPlanner()
    delivery_points = [(100, 100), (200, 200), (300, 300)]

    path = path_planner.plan(delivery_points)
    assert isinstance(path, list)
    assert len(path) > 0