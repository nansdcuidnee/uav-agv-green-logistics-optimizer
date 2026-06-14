import math
import heapq
import random
import time
class Node:
    """节点类，用于A*算法和RRT算法
    
    Attributes:
        position: 节点位置
        parent: 父节点
        g: 从起点到当前节点的代价
        h: 从当前节点到终点的启发式代价
        f: 总代价 (g + h)
    """
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g = 0  # 从起点到当前节点的代价
        self.h = 0  # 从当前节点到终点的启发式代价
        self.f = 0  # 总代价
    
    def __eq__(self, other):
        return self.position == other.position
    
    def __lt__(self, other):
        return self.f < other.f

class PathPlanner:
    """路径规划类
    
    实现多种路径规划算法，包括：
    - 最近邻算法：用于优化多目标点的访问顺序
    - A*算法：用于在有障碍物的环境中找到最优路径
    - RRT算法：用于在复杂环境中快速找到可行路径
    
    支持路径平滑和路径简化，提高路径质量和效率
    """
    
    def __init__(self):
        """初始化路径规划器
        
        初始化路径规划器的参数和数据结构
        """
        pass
    
    def _calculate_distance(self, point1, point2):
        """计算两点之间的欧几里得距离
        
        Args:
            point1: 第一个点的坐标
            point2: 第二个点的坐标
            
        Returns:
            float: 两点之间的距离
        
        Raises:
            ValueError: 如果点的维度不同
            TypeError: 如果点不是可迭代对象
        """
        try:
            if len(point1) != len(point2):
                raise ValueError("Points must have the same dimension")
            
            if point1 is None or point2 is None or len(point1)!=len(point2):
                return float('inf')
            squared_distance = sum((float(p1) - float(p2)) ** 2 for p1, p2 in zip(point1, point2))
            return math.sqrt(squared_distance)
        except (TypeError, AttributeError):
            raise TypeError("Points must be iterable objects with numeric coordinates")
    
    def _is_collision(self, point, obstacles, collision_radius=0.5):
        """检测点是否与障碍物碰撞
        
        Args:
            point: 检测点
            obstacles: 障碍物列表，每个障碍物为 (x, y, radius)
            collision_radius: 碰撞半径
            
        Returns:
            bool: 是否碰撞
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        if not obstacles:
            return False
        
        for obstacle in obstacles:
            if len(obstacle) < 3:
                continue  # 跳过格式不正确的障碍物
            obstacle_pos = (obstacle[0], obstacle[1])
            obstacle_radius = obstacle[2]
            distance = self._calculate_distance(point, obstacle_pos)
            if distance < (obstacle_radius + collision_radius):
                return True
        
        return False
    
    def _is_segment_collision(self, start_point, end_point, obstacles, collision_radius=0.5):
        """检测线段是否与障碍物碰撞
        
        Args:
            start_point: 线段起点
            end_point: 线段终点
            obstacles: 障碍物列表，每个障碍物为 (x, y, radius)
            collision_radius: 碰撞半径
            
        Returns:
            bool: 是否碰撞
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        if not obstacles:
            return False
        
        for obstacle in obstacles:
            if len(obstacle) < 3:
                continue  # 跳过格式不正确的障碍物
            obstacle_pos = (obstacle[0], obstacle[1])
            obstacle_radius = obstacle[2]
            
            # 计算线段到障碍物中心的最短距离
            distance = self._distance_segment_to_point(start_point, end_point, obstacle_pos)
            if distance < (obstacle_radius + collision_radius):
                return True
        
        return False
    
    def _distance_segment_to_point(self, start_point, end_point, point):
        """计算线段到点的最短距离
        
        Args:
            start_point: 线段起点
            end_point: 线段终点
            point: 目标点
            
        Returns:
            float: 最短距离
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        # 计算向量
        a = (point[0] - start_point[0], point[1] - start_point[1])
        b = (end_point[0] - start_point[0], end_point[1] - start_point[1])
        
        # 计算点积
        dot_product = a[0] * b[0] + a[1] * b[1]
        
        # 计算线段长度的平方
        b_length_squared = b[0] ** 2 + b[1] ** 2
        
        # 如果线段长度为0，返回点到起点的距离
        if b_length_squared == 0:
            return self._calculate_distance(start_point, point)
        
        # 计算参数t
        t = max(0, min(1, dot_product / b_length_squared))
        
        # 计算投影点
        projection = (start_point[0] + t * b[0], start_point[1] + t * b[1])
        
        # 返回投影点到目标点的距离
        return self._calculate_distance(projection, point)
    
    def _get_neighbors(self, current, end, obstacles, step_size=1.0):
        """获取当前节点的邻居节点
        
        Args:
            current: 当前节点
            end: 终点
            obstacles: 障碍物列表
            step_size: 步长
            
        Returns:
            list: 邻居节点列表
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        neighbors = []
        # 8个方向的移动
        directions = [(step_size, 0), (-step_size, 0), (0, step_size), (0, -step_size),
                      (step_size, step_size), (step_size, -step_size), (-step_size, step_size), (-step_size, -step_size)]
        
        for dx, dy in directions:
            new_x = current.position[0] + dx
            new_y = current.position[1] + dy
            new_position = (new_x, new_y)
            
            # 检查是否与障碍物碰撞
            if not self._is_collision(new_position, obstacles):
                neighbor = Node(new_position, current)
                # 计算g值（从起点到当前节点的代价）
                neighbor.g = current.g + self._calculate_distance(current.position, new_position)
                # 计算h值（从当前节点到终点的启发式代价）
                neighbor.h = self._calculate_distance(new_position, end)
                # 计算f值（总代价）
                neighbor.f = neighbor.g + neighbor.h
                neighbors.append(neighbor)
        
        return neighbors
    
    def _reconstruct_path(self, current):
        """重构路径
        
        Args:
            current: 终点节点
            
        Returns:
            list: 路径点列表
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        try:
            path = []
            while current:
                path.append(current.position)
                current = current.parent
            return path[::-1]  # 反转路径，从起点到终点
        except (TypeError, AttributeError):
            raise TypeError("Invalid node structure")
    
    def _smooth_path(self, path, alpha=0.5, beta=0.5, iterations=10):
        """平滑路径
        
        使用样条曲线平滑路径，减少路径的抖动
        
        Args:
            path: 原始路径
            alpha: 平滑因子，控制平滑程度
            beta: 张力因子，控制路径的弯曲程度
            iterations: 迭代次数
            
        Returns:
            list: 平滑后的路径
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        try:
            if len(path) < 3:
                return path
            
            smoothed_path = path.copy()
            for _ in range(iterations):
                # 前向传递
                for i in range(1, len(smoothed_path) - 1):
                    for j in range(len(smoothed_path[i])):
                        smoothed_path[i] = list(smoothed_path[i])
                        smoothed_path[i][j] += alpha * (smoothed_path[i-1][j] + smoothed_path[i+1][j] - 2 * smoothed_path[i][j])
                        if i > 1:
                            smoothed_path[i][j] += beta * (smoothed_path[i][j] - smoothed_path[i-2][j])
                        if i < len(smoothed_path) - 2:
                            smoothed_path[i][j] += beta * (smoothed_path[i+2][j] - smoothed_path[i][j])
                        smoothed_path[i] = tuple(smoothed_path[i])
                
                # 后向传递
                for i in range(len(smoothed_path) - 2, 0, -1):
                    for j in range(len(smoothed_path[i])):
                        smoothed_path[i] = list(smoothed_path[i])
                        smoothed_path[i][j] += alpha * (smoothed_path[i-1][j] + smoothed_path[i+1][j] - 2 * smoothed_path[i][j])
                        if i > 1:
                            smoothed_path[i][j] += beta * (smoothed_path[i][j] - smoothed_path[i-2][j])
                        if i < len(smoothed_path) - 2:
                            smoothed_path[i][j] += beta * (smoothed_path[i+2][j] - smoothed_path[i][j])
                        smoothed_path[i] = tuple(smoothed_path[i])
            
            return smoothed_path
        except (TypeError, AttributeError):
            raise TypeError("Invalid path format")
    
    def _simplify_path(self, path, epsilon=0.1):
        """简化路径，减少路径点数量
        
        使用Ramer-Douglas-Peucker算法简化路径，减少路径点数量
        同时保持路径的形状
        
        Args:
            path: 原始路径
            epsilon: 容差，控制简化程度
            
        Returns:
            list: 简化后的路径
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        try:
            if len(path) < 3:
                return path
            
            # 使用Ramer-Douglas-Peucker算法简化路径
            def rdp(points, epsilon):
                if len(points) < 3:
                    return points
                
                # 找到距离最远的点
                start = points[0]
                end = points[-1]
                max_distance = 0
                max_index = 0
                
                for i in range(1, len(points) - 1):
                    distance = self._distance_segment_to_point(start, end, points[i])
                    if distance > max_distance:
                        max_distance = distance
                        max_index = i
                
                # 如果最大距离大于容差，递归简化
                if max_distance > epsilon:
                    left = rdp(points[:max_index+1], epsilon)
                    right = rdp(points[max_index:], epsilon)
                    return left[:-1] + right
                else:
                    return [start, end]
            
            return rdp(path, epsilon)
        except (TypeError, AttributeError):
            raise TypeError("Invalid path format")
    
    def a_star(self, start_point, end_point, obstacles=None):
        """A*路径规划算法
        
        使用A*算法在有障碍物的环境中找到从起点到终点的最优路径
        
        Args:
            start_point: 起点位置
            end_point: 终点位置
            obstacles: 障碍物列表，每个障碍物为 (x, y, radius)
            
        Returns:
            list: 规划后的路径点列表
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        # 检查起点和终点是否有效
        if not start_point or not end_point:
            return []
        
        # 检查起点或终点是否与障碍物碰撞
        if self._is_collision(start_point, obstacles) or self._is_collision(end_point, obstacles):
            return []
        
        # Fast path: if no obstacles, return direct line
        if obstacles is None or len(obstacles) == 0:
            return [start_point, end_point]
        
        # Fast path: if direct line has no collision, return direct line
        if not self._is_segment_collision(start_point, end_point, obstacles):
            return [start_point, end_point]
        
        # 初始化开放列表和关闭列表
        open_list = []
        closed_set = set()  # 使用集合提高查询效率
        open_dict = {}  # 使用字典存储开放列表中的节点，提高查询效率
        
        # 创建起点节点
        start_node = Node(start_point)
        end_node = Node(end_point)
        
        # 将起点加入开放列表
        rounded_start = (round(start_point[0], 1), round(start_point[1], 1))
        heapq.heappush(open_list, start_node)
        open_dict[rounded_start] = start_node

        # 添加超时保护
        start_time = time.time()
        max_iterations = 220000
        time_limit = 5.0  # 5秒超时
        iteration = 0
        step_size = 1.0  # 步长

# 主循环
        while open_list and iteration < max_iterations:
    # 检查超时
            if time.time() - start_time > time_limit:
                print(f"A*算法超时({time_limit}秒)")
                # Only return direct line if it has no collision
                if not self._is_segment_collision(start_point, end_point, obstacles):
                    return [start_point, end_point]
                else:
                    return []
  
            iteration += 1
            # 从开放列表中取出f值最小的节点
            current_node = heapq.heappop(open_list)
            current_pos = current_node.position
            
            # 从开放字典中移除当前节点
            rounded_pos = (round(current_pos[0], 1), round(current_pos[1], 1))
            if rounded_pos in open_dict:
                del open_dict[rounded_pos]
            
            # 检查是否到达终点（使用合理的容差，一个步长大小）
            distance_to_end = self._calculate_distance(current_pos, end_point)
            if distance_to_end < step_size:
                # 到达终点附近，将终点添加到路径中
                path = self._reconstruct_path(current_node)
                if path[-1] != end_point:
                    path.append(end_point)
                return path
            
            # 将当前节点加入关闭集合，对位置进行四舍五入以减少集合大小
            rounded_pos = (round(current_pos[0], 1), round(current_pos[1], 1))
            closed_set.add(rounded_pos)
            
            # 获取邻居节点
            neighbors = self._get_neighbors(current_node, end_point, obstacles)
            
            for neighbor in neighbors:
                neighbor_pos = neighbor.position
                
                # 检查邻居节点是否在关闭集合中，使用四舍五入后的位置
                rounded_neighbor_pos = (round(neighbor_pos[0], 1), round(neighbor_pos[1], 1))
                if rounded_neighbor_pos in closed_set:
                    continue
                
                # 检查邻居节点是否在开放列表中，使用四舍五入后的位置
                if rounded_neighbor_pos in open_dict:
                    # 如果当前路径更优，更新节点信息
                    existing_node = open_dict[rounded_neighbor_pos]
                    if neighbor.g < existing_node.g:
                        # 更新节点信息
                        existing_node.g = neighbor.g
                        existing_node.h = neighbor.h
                        existing_node.f = neighbor.f
                        existing_node.parent = neighbor.parent
                        # 由于堆的特性，我们需要重新插入节点以更新堆
                        heapq.heappush(open_list, existing_node)
                else:
                    # 如果邻居节点不在开放列表中，加入开放列表
                    heapq.heappush(open_list, neighbor)
                    open_dict[rounded_neighbor_pos] = neighbor
        
        # 如果没有找到路径
        if iteration >= max_iterations:
            print(f"A*算法达到最大迭代次数({max_iterations})")
            # Only return direct line if it has no collision
            if not self._is_segment_collision(start_point, end_point, obstacles):
                return [start_point, end_point]
            else:
                return []

        # 如果没有找到路径
        print(f"A*算法未找到路径")
        # Only return direct line if it has no collision
        if not self._is_segment_collision(start_point, end_point, obstacles):
            return [start_point, end_point]
        else:
            return []
    
    def rrt(self, start_point, end_point, obstacles=None, max_iterations=1000, step_size=1.0, goal_radius=1.0):
        """RRT路径规划算法
        
        使用快速随机树(RRT)算法在复杂环境中快速找到可行路径
        
        Args:
            start_point: 起点位置
            end_point: 终点位置
            obstacles: 障碍物列表，每个障碍物为 (x, y, radius)
            max_iterations: 最大迭代次数
            step_size: 步长
            goal_radius: 目标半径
            
        Returns:
            list: 规划后的路径点列表
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        # 检查起点和终点是否有效
        if not start_point or not end_point:
            return []
        
        # 检查起点或终点是否与障碍物碰撞
        if self._is_collision(start_point, obstacles) or self._is_collision(end_point, obstacles):
            return []
        
        # 初始化树和位置列表
        tree = [Node(start_point)]
        positions = [start_point]  # 存储所有节点的位置，用于快速最近邻查找
        
        # 主循环
        for _ in range(max_iterations):
            # 随机采样一个点
            if random.random() < 0.1:  # 10%的概率直接采样终点
                random_point = end_point
            else:
                # 在合理范围内随机采样
                # 使用更大的范围以适应实际地图大小
                random_point = (random.uniform(0, 1000), random.uniform(0, 1000))
            
            # 找到树中距离随机点最近的节点
            # 优化：使用预计算的位置列表和索引，提高查找效率
            nearest_index = min(range(len(positions)), 
                              key=lambda i: self._calculate_distance(positions[i], random_point))
            nearest_node = tree[nearest_index]
            
            # 计算从最近节点到随机点的方向
            dx = random_point[0] - nearest_node.position[0]
            dy = random_point[1] - nearest_node.position[1]
            distance = math.sqrt(dx**2 + dy**2)
            
            # 如果距离大于步长，沿着方向移动步长距离
            if distance > step_size:
                new_x = nearest_node.position[0] + (dx / distance) * step_size
                new_y = nearest_node.position[1] + (dy / distance) * step_size
                new_point = (new_x, new_y)
            else:
                new_point = random_point
            
            # 检查新点是否与障碍物碰撞
            if self._is_collision(new_point, obstacles):
                continue
            
            # 检查从最近节点到新点的线段是否与障碍物碰撞
            collision = self._is_segment_collision(nearest_node.position, new_point, obstacles)
            
            if collision:
                continue
            
            # 创建新节点并添加到树中
            new_node = Node(new_point, nearest_node)
            tree.append(new_node)
            positions.append(new_point)  # 更新位置列表
            
            # 检查是否到达终点
            if self._calculate_distance(new_point, end_point) < goal_radius:
                # 创建终点节点并添加到树中
                end_node = Node(end_point, new_node)
                tree.append(end_node)
                return self._reconstruct_path(end_node)
        
        # 如果没有找到路径，返回空列表
        return []
    
    def nearest_neighbor(self, start_point, points):
        """最近邻算法
        
        Args:
            start_point: 起点位置
            points: 目标点列表
            
        Returns:
            list: 规划后的路径点列表
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        try:
            if not points:
                return [start_point]
            
            # 验证输入参数类型
            if not hasattr(points, '__iter__'):
                raise TypeError("Points must be an iterable")
            
            # 创建点的副本，避免修改原始列表
            remaining_points = list(points)
            path = [start_point]
            current_point = start_point
            
            while remaining_points:
                # 找到距离当前点最近的点
                nearest_point = min(remaining_points, key=lambda point: self._calculate_distance(current_point, point))
                # 将最近的点添加到路径中
                path.append(nearest_point)
                # 从剩余点中移除最近的点
                remaining_points.remove(nearest_point)
                # 更新当前点
                current_point = nearest_point
            
            return path
        except (TypeError, ValueError) as e:
            raise TypeError(f"Invalid input: {str(e)}")
    
    def plan_path(self, start_point, end_point, obstacles=None, algorithm='a_star', smooth=True, simplify=True):
        """规划从起点到终点的路径

        Args:
            start_point: 起点位置
            end_point: 终点位置
            obstacles: 障碍物列表
            algorithm: 路径规划算法，可选值: 'a_star', 'rrt', 'straight'
            smooth: 是否平滑路径
            simplify: 是否简化路径

        Returns:
            list: 路径点列表

        Raises:
            TypeError: 如果输入参数类型不正确
            ValueError: 如果算法名称无效
        """
        try:
            # 验证输入参数类型
            if not start_point or not end_point:
                raise TypeError("Start and end points must be provided")
            
            # 验证算法名称
            valid_algorithms = ['a_star', 'rrt', 'straight']
            if algorithm not in valid_algorithms:
                raise ValueError(f"Invalid algorithm. Must be one of: {valid_algorithms}")
            
            if algorithm == 'a_star':
                path = self.a_star(start_point, end_point, obstacles)
                if path:
                    if smooth:
                        path = self._smooth_path(path)
                    if simplify:
                        path = self._simplify_path(path)
                    return path
                # A* 算法失败，回退到直线算法
                return [start_point, end_point]
            elif algorithm == 'rrt':
                path = self.rrt(start_point, end_point, obstacles)
                if path:
                    if smooth:
                        path = self._smooth_path(path)
                    if simplify:
                        path = self._simplify_path(path)
                    return path
                # RRT 算法失败，回退到直线算法
                return [start_point, end_point]
            
            # 选择直线算法
            return [start_point, end_point]
        except (TypeError, ValueError) as e:
            raise TypeError(f"Invalid input: {str(e)}")
    
    def plan_multi_stop_path(self, start_point, stops, end_point, obstacles=None):
        """规划多 stops 的路径
        
        Args:
            start_point: 起点位置
            stops: 中间停靠点列表
            end_point: 终点位置
            obstacles: 障碍物列表
            
        Returns:
            list: 路径点列表
            
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        try:
            # 验证输入参数类型
            if not start_point or not end_point:
                raise TypeError("Start and end points must be provided")
            
            # 构建完整路径：起点 -> 停靠点 -> 终点
            path = [start_point]
            current_point = start_point
            
            # 为每个停靠点规划路径
            for stop in stops:
                segment_path = self.plan_path(current_point, stop, obstacles)
                if segment_path and len(segment_path) > 1:
                    path.extend(segment_path[1:])  # 避免重复添加起点
                    current_point = stop
            
            # 添加到终点的路径
            segment_path = self.plan_path(current_point, end_point, obstacles)
            if segment_path and len(segment_path) > 1:
                path.extend(segment_path[1:])  # 避免重复添加起点
            
            return path
        except (TypeError, ValueError) as e:
            raise TypeError(f"Invalid input: {str(e)}")
    
    def plan(self, points, obstacles=None):
        """规划路径
        
        Args:
            points: 目标点列表
            obstacles: 障碍物列表
            
        Returns:
            list: 规划后的路径点列表
        
        Raises:
            TypeError: 如果输入参数类型不正确
        """
        try:
            if not points:
                return []
            
            # 验证输入参数类型
            if not hasattr(points, '__iter__'):
                raise TypeError("Points must be an iterable")
            
            # 转换为列表，确保可索引
            points_list = list(points)
            if len(points_list) == 0:
                return []
            
            # 以第一个点为起点，使用最近邻算法规划路径
            start_point = points_list[0]
            remaining_points = points_list[1:]
            
            if not remaining_points:
                return [start_point]
            
            # 使用最近邻算法优化点的顺序
            optimized_points = self.nearest_neighbor(start_point, remaining_points)
            
            # 构建完整路径
            path = [start_point]
            current_point = start_point
            
            # 为每个点规划路径
            for point in optimized_points[1:]:
                segment_path = self.plan_path(current_point, point, obstacles)
                if segment_path:
                    path.extend(segment_path[1:])  # 避免重复添加起点
                    current_point = point
            
            return path
        except (TypeError, ValueError) as e:
            raise TypeError(f"Invalid input: {str(e)}")