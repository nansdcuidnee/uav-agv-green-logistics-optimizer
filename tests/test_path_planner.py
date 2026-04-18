import pytest
from src.planning.path_planner import PathPlanner

class TestPathPlanner:
    """测试路径规划器功能"""

    def setup_method(self):
        """设置测试环境"""
        self.path_planner = PathPlanner()

    def test_path_length_without_obstacles(self):
        """测试无障碍时路径长度≈直线距离"""
        start_point = (0, 0)
        end_point = (10, 0)
        
        # 规划路径
        path = self.path_planner.plan_path(start_point, end_point)
        
        # 计算路径长度
        def calculate_path_length(path):
            length = 0.0
            for i in range(len(path) - 1):
                length += self.path_planner._calculate_distance(path[i], path[i+1])
            return length
        
        path_length = calculate_path_length(path)
        straight_distance = self.path_planner._calculate_distance(start_point, end_point)
        
        # 验证路径长度不大于直线距离的1.5倍（允许A*算法生成的路径略有曲折）
        assert path_length <= straight_distance * 1.5
        # 验证路径长度不小于直线距离
        assert path_length >= straight_distance

    def test_path_length_with_obstacles(self):
        """测试有障碍时路径长度 > 直线距离"""
        start_point = (0, 0)
        end_point = (10, 0)
        
        # 创建障碍物（位于起点和终点之间）
        obstacles = [(5, 0, 2)]  # (x, y, radius)
        
        # 规划路径
        path = self.path_planner.plan_path(start_point, end_point, obstacles)
        
        # 计算路径长度
        def calculate_path_length(path):
            length = 0.0
            for i in range(len(path) - 1):
                length += self.path_planner._calculate_distance(path[i], path[i+1])
            return length
        
        path_length = calculate_path_length(path)
        straight_distance = self.path_planner._calculate_distance(start_point, end_point)
        
        # 验证路径长度大于直线距离
        assert path_length > straight_distance
        
        # 验证路径点不落入障碍物半径
        for point in path:
            for obstacle in obstacles:
                distance = self.path_planner._calculate_distance(point, (obstacle[0], obstacle[1]))
                assert distance >= obstacle[2]

    def test_a_star_fallback_to_straight(self):
        """测试A*算法失败时回退到直线算法"""
        start_point = (0, 0)
        end_point = (10, 0)
        
        # 创建无法绕过的障碍物（完全阻挡路径）
        obstacles = [(5, 0, 6)]  # 半径足够大，完全阻挡路径
        
        # 规划路径
        path = self.path_planner.plan_path(start_point, end_point, obstacles)
        
        # 验证返回直线路径
        assert len(path) == 2
        assert path[0] == start_point
        assert path[1] == end_point

    def test_plan_multi_stop_path(self):
        """测试多停靠点路径规划"""
        start_point = (0, 0)
        stops = [(5, 0), (15, 0)]
        end_point = (20, 0)
        
        # 规划路径
        path = self.path_planner.plan_multi_stop_path(start_point, stops, end_point)
        
        # 验证路径包含所有点
        assert path[0] == start_point
        assert (5, 0) in path
        assert (15, 0) in path
        assert path[-1] == end_point
