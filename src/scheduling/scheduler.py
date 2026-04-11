import logging
import heapq
from src.utils.math_utils import calculate_distance
from src.planning.path_planner import PathPlanner
from config.config import (
    UAV_CHARGE_THRESHOLD, ALPHA, BETA, GAMMA, DELTA,
    MAP_SIZE, UAV_SPEED, AGV_SPEED, AGV_CHARGING_CAPACITY,
    BASE_ENERGY_CONSUMPTION, PAYLOAD_ENERGY_FACTOR
)


class Scheduler:
    """调度器类

    负责任务分配和调度，包含三种策略:
    - baseline_direct: 基线直送策略
    - relay_coop: 中继合作策略
    - energy_priority: 能耗优先策略

    策略切换通过 strategy_type 参数控制，默认为 baseline_direct
    """

    # 策略类型常量
    STRATEGY_BASELINE_DIRECT = "baseline_direct"
    STRATEGY_RELAY_COOP = "relay_coop"
    STRATEGY_ENERGY_PRIORITY = "energy_priority"
    STRATEGY_GA_OPTIMIZED = "ga_optimized"  # 遗传算法优化策略

    # 支持的策略列表
    SUPPORTED_STRATEGIES = [
        STRATEGY_BASELINE_DIRECT,
        STRATEGY_RELAY_COOP,
        STRATEGY_ENERGY_PRIORITY,
        STRATEGY_GA_OPTIMIZED
    ]

    def __init__(self, strategy_type: str = "baseline_direct"):
        """初始化调度器

        Args:
            strategy_type: 策略类型，可选值为:
                - baseline_direct: 基线直送策略
                - relay_coop: 中继合作策略
                - energy_priority: 能耗优先策略
        """
        # 验证策略类型
        if strategy_type not in self.SUPPORTED_STRATEGIES:
            raise ValueError(
                f"Unsupported strategy: {strategy_type}. "
                f"Supported strategies: {self.SUPPORTED_STRATEGIES}"
            )

        self.strategy_type = strategy_type

        # 创建统一的路径规划器
        self.path_planner = PathPlanner()

        # 计算地图对角线最大距离
        self.max_distance = (MAP_SIZE[0] ** 2 + MAP_SIZE[1] ** 2) ** 0.5

        # 配置日志记录器
        self.logger = logging.getLogger(f"scheduler.{strategy_type}")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)

        # ==================== 性能优化缓存 ====================
        # A* 路径缓存: (start, end) -> distance
        self._astar_cache = {}
        self._astar_cache_max_size = 1000  # 缓存上限

        # 能耗计算缓存: (uav_id, task_id) -> energy
        self._energy_cache = {}
        self._energy_cache_max_size = 500

        # 时间计算缓存: (uav_id, task_id) -> time
        self._time_cache = {}
        self._time_cache_max_size = 500

    # ==================== 路径规划算法 ====================

    def calculate_astar_distance(self, start, end, obstacles=None):
        """使用A*算法计算带障碍物的路径距离

        Args:
            start: 起点位置 (x, y)
            end: 终点位置 (x, y)
            obstacles: 障碍物列表

        Returns:
            float: 路径距离，如果无法找到路径返回inf
        """
        # 构建缓存键（使用tuple和round避免浮点数精度问题）
        cache_key = (
            (round(start[0], 1), round(start[1], 1)),
            (round(end[0], 1), round(end[1], 1))
        )

        # 检查缓存
        if cache_key in self._astar_cache:
            return self._astar_cache[cache_key]

        # 使用PathPlanner的A*算法规划路径
        path = self.path_planner.a_star(start, end, obstacles)
        if not path:
            # 如果A*失败，返回欧几里得距离作为后备
            distance = calculate_distance(start, end)
        else:
            # 计算路径总长度
            distance = 0.0
            for i in range(len(path) - 1):
                distance += calculate_distance(path[i], path[i+1])

        # 更新缓存（带上限控制）
        if len(self._astar_cache) < self._astar_cache_max_size:
            self._astar_cache[cache_key] = distance

        return distance

    def _get_agv_nearby(self, task_point, agvs, search_radius=300.0):
        """空间索引过滤：获取任务点周边一定范围内的AGV

        Args:
            task_point: 任务点位置 (x, y)
            agvs: AGV列表
            search_radius: 搜索半径

        Returns:
            list: 范围内的空闲AGV列表
        """
        nearby_agvs = []
        for agv in agvs:
            if agv.status != "idle":
                continue
            # 快速欧几里得距离过滤
            dist = calculate_distance(agv.position, task_point)
            if dist <= search_radius:
                nearby_agvs.append(agv)

        # 如果没有找到附近的AGV，返回所有空闲AGV作为后备
        if not nearby_agvs:
            nearby_agvs = [agv for agv in agvs if agv.status == "idle"]

        return nearby_agvs

    def dijkstra_agv_selection(self, uav, agvs, task, obstacles=None):
        """使用Dijkstra算法选择最优AGV

        考虑多节点（无人机 -> 任务点 -> AGV）的全局最短路径

        Args:
            uav: 无人机对象
            agvs: AGV列表
            task: 任务对象
            obstacles: 障碍物列表

        Returns:
            AGV: 最优AGV对象
        """
        if not agvs:
            return None

        # 空间索引过滤：先筛选任务点周边的AGV，减少计算量
        nearby_agvs = self._get_agv_nearby(task.start_point, agvs, search_radius=300.0)

        if not nearby_agvs:
            return None

        agv_costs = []

        for agv in nearby_agvs:
            # 计算路径代价：UAV -> 任务起点 -> 任务终点 -> AGV
            # 使用A*算法计算带障碍物的路径（已缓存）
            uav_to_start = self.calculate_astar_distance(
                uav.position, task.start_point, obstacles
            )
            start_to_end = self.calculate_astar_distance(
                task.start_point, task.end_point, obstacles
            )
            end_to_agv = self.calculate_astar_distance(
                task.end_point, agv.position, obstacles
            )

            total_cost = uav_to_start + start_to_end + end_to_agv
            agv_costs.append((agv, total_cost))

        if not agv_costs:
            return None

        # 选择代价最小的AGV
        agv_costs.sort(key=lambda x: x[1])
        return agv_costs[0][0]

    def genetic_algorithm_task_assignment(self, tasks, uavs, agvs=None, population_size=20, generations=50):
        """使用遗传算法进行多目标优化任务分配

        优化目标：能耗 + 时间 + 任务完成率

        Args:
            tasks: 任务列表
            uavs: 无人机列表
            agvs: AGV列表
            population_size: 种群大小
            generations: 迭代代数

        Returns:
            list: 分配结果列表 [(task, uav), ...]
        """
        if not tasks or not uavs:
            return []

        if agvs is None:
            agvs = []

        import random

        # ==================== 预计算缓存初始化 ====================
        # 预计算所有任务-无人机组合的能耗和时间
        task_uav_energy = {}  # (task_id, uav_id) -> energy
        task_uav_time = {}   # (task_id, uav_id) -> time
        task_uav_feasible = {}  # (task_id, uav_id) -> bool

        for task in tasks:
            for uav in uavs:
                cache_key = (task.id, uav.id)
                # 能耗计算（使用缓存）
                energy = self.calculate_energy_consumption(uav, task)
                task_uav_energy[cache_key] = energy

                # 时间计算
                distance = calculate_distance(uav.position, task.start_point)
                distance += calculate_distance(task.start_point, task.end_point)
                task_uav_time[cache_key] = distance / UAV_SPEED

                # 可行性检查
                task_uav_feasible[cache_key] = self.can_complete_task(uav, task)

        # 个体编码：任务->无人机的映射
        # 每个基因是一个任务，值为分配的无人机索引

        def create_individual():
            """创建随机个体"""
            individual = []
            for _ in range(len(tasks)):
                # -1 表示未分配
                gene = random.randint(-1, len(uavs) - 1)
                individual.append(gene)
            return individual

        def decode_individual(individual):
            """解码个体为分配结果"""
            assignments = []
            for i, gene in enumerate(individual):
                if gene >= 0 and gene < len(uavs):
                    task = tasks[i]
                    uav = uavs[gene]
                    assignments.append((task, uav))
            return assignments

        # 适应度缓存
        fitness_cache = {}

        def get_fitness_key(individual):
            """生成个体的唯一键（用于缓存）"""
            return tuple(individual)

        def calculate_fitness(individual):
            """计算适应度 - 多目标优化（带缓存）"""
            # 检查缓存
            fitness_key = get_fitness_key(individual)
            if fitness_key in fitness_cache:
                return fitness_cache[fitness_key]

            if agvs is None:
                agvs = []

            assignments = decode_individual(individual)

            if not assignments:
                fitness_cache[fitness_key] = 0.0
                return 0.0

            # 目标1: 最小化总能耗（使用预计算缓存）
            total_energy = 0.0
            for task, uav in assignments:
                cache_key = (task.id, uav.id)
                total_energy += task_uav_energy.get(cache_key, 0)
            energy_score = max(0, 100 - total_energy)

            # 目标2: 最小化总飞行时间（使用预计算缓存）
            total_time = 0.0
            for task, uav in assignments:
                cache_key = (task.id, uav.id)
                total_time += task_uav_time.get(cache_key, 0)
            time_score = max(0, 100 - total_time / 10)

            # 目标3: 最大化任务完成率
            completion_score = len(assignments) / len(tasks) * 100

            # 综合适应度
            fitness = 0.4 * energy_score + 0.3 * time_score + 0.3 * completion_score

            # 惩罚不可行的分配（电量不足）（使用预计算缓存）
            penalty = 0
            for task, uav in assignments:
                cache_key = (task.id, uav.id)
                if not task_uav_feasible.get(cache_key, False):
                    penalty += 20
            fitness -= penalty

            result = max(0, fitness)
            fitness_cache[fitness_key] = result
            return result

        def selection(population, fitnesses):
            """锦标赛选择"""
            selected = []
            for _ in range(len(population)):
                # 随机选择3个个体
                indices = random.sample(range(len(population)), min(3, len(population)))
                best_idx = max(indices, key=lambda i: fitnesses[i])
                selected.append(population[best_idx].copy())
            return selected

        def crossover(parent1, parent2):
            """单点交叉"""
            crossover_point = random.randint(1, len(parent1) - 1)
            child1 = parent1[:crossover_point] + parent2[crossover_point:]
            child2 = parent2[:crossover_point] + parent1[crossover_point:]
            return child1, child2

        def mutate(individual, mutation_rate):
            """变异（使用动态变异率）"""
            for i in range(len(individual)):
                if random.random() < mutation_rate:
                    individual[i] = random.randint(-1, len(uavs) - 1)
            return individual

        # 初始化种群
        population = [create_individual() for _ in range(population_size)]

        # 迭代进化
        best_solution = None
        best_fitness = 0

        # 自适应变异率参数
        initial_mutation_rate = 0.3  # 初期高变异率
        final_mutation_rate = 0.05   # 后期低变异率

        for generation in range(generations):
            # 计算适应度（使用缓存）
            fitnesses = [calculate_fitness(ind) for ind in population]

            # 记录最优解
            max_fit_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
            if fitnesses[max_fit_idx] > best_fitness:
                best_fitness = fitnesses[max_fit_idx]
                best_solution = population[max_fit_idx].copy()

            # 自适应变异率：线性递减
            mutation_rate = initial_mutation_rate - (initial_mutation_rate - final_mutation_rate) * generation / generations

            # 选择
            selected = selection(population, fitnesses)

            # 交叉和变异
            new_population = []
            for i in range(0, len(selected), 2):
                if i + 1 < len(selected):
                    child1, child2 = crossover(selected[i], selected[i+1])
                    new_population.append(mutate(child1, mutation_rate))
                    new_population.append(mutate(child2, mutation_rate))
                else:
                    new_population.append(mutate(selected[i], mutation_rate))

            # 精英保留
            if best_solution:
                new_population[0] = best_solution.copy()

            population = new_population

        # 清除缓存
        fitness_cache.clear()

        # 返回最优解
        return decode_individual(best_solution) if best_solution else []

    def calculate_energy_consumption(self, uav, task, obstacles=None):
        """计算无人机执行任务的预估能耗

        Args:
            uav: 无人机对象
            task: 任务对象
            obstacles: 障碍物列表（可选）

        Returns:
            float: 预估能耗
        """
        # 使用 PathPlanner 计算实际路径距离
        # 从 UAV 当前位置到任务起点
        path_to_start = self.path_planner.plan_path(
            uav.position, task.start_point, obstacles, algorithm='straight'
        )
        distance_to_start = self.path_planner._calculate_distance(
            uav.position, task.start_point
        )

        # 从任务起点到终点
        task_distance = self.path_planner._calculate_distance(
            task.start_point, task.end_point
        )

        # 从任务终点返回 UAV 当前位置
        return_distance = self.path_planner._calculate_distance(
            task.end_point, uav.position
        )

        total_distance = distance_to_start + task_distance + return_distance

        # 能耗 = 距离 / 速度 * 基础能耗
        distance_energy = total_distance / UAV_SPEED * BASE_ENERGY_CONSUMPTION
        # 负载能耗
        payload_energy = task_distance * PAYLOAD_ENERGY_FACTOR if task.payload > 0 else 0

        return distance_energy + payload_energy

    def can_complete_task(self, uav, task):
        """检查无人机是否有足够电量完成任务

        Args:
            uav: 无人机对象
            task: 任务对象

        Returns:
            bool: 是否可以完成任务的bool值
        """
        if task is None:
            return False
        energy_needed = self.calculate_energy_consumption(uav, task)
        # 保留10%的电量作为安全余量
        safe_battery = uav.battery * 0.9
        return safe_battery >= energy_needed

    def score_task(self, task, uav, alpha=0.25, beta=0.25, gamma=0.25, delta=0.25):
        """任务评分函数

        基于距离、电量、负载、优先级和任务可行性五个维度计算任务与无人机的匹配度评分。
        评分越高，无人机越适合执行该任务。

        Args:
            task: 任务对象
            uav: 无人机对象
            alpha: 距离权重
            beta: 电量权重
            gamma: 负载权重
            delta: 优先级权重

        Returns:
            float: 评分值 (0-1之间，越高越适合)
        """
        # 任务可行性检查：如果电量不足，返回最低分
        if not self.can_complete_task(uav, task):
            return 0.0

        # 1. 距离评分：无人机当前位置到任务起点的距离
        distance = calculate_distance(uav.position, task.start_point)
        distance_score = 1 - min(distance / self.max_distance, 1.0)

        # 2. 电量评分：电量越高的无人机越适合
        battery_score = uav.battery / 100.0

        # 3. 负载评分：无人机负载能力满足任务需求得高分
        # UAV类没有payload_capacity属性，简化处理
        load_score = 1.0

        # 4. 优先级评分：优先级越高，任务越紧急
        max_priority = 5  # 假设最大优先级为5
        priority_score = min(task.priority / max_priority, 1.0)

        # 5. 能效评分：执行任务后的剩余电量比例
        energy_needed = self.calculate_energy_consumption(uav, task)
        remaining_battery = uav.battery - energy_needed
        efficiency_score = max(remaining_battery / 100.0, 0)

        # 加权计算总分
        total_score = (alpha * distance_score +
                       beta * battery_score +
                       gamma * load_score +
                       delta * priority_score +
                       0.1 * efficiency_score)

        return total_score

    # ==================== 三种策略的具体实现 ====================

    def _assign_tasks_baseline_direct(self, tasks, uavs, agvs):
        """基线直送策略 (baseline_direct)

        使用贪心算法，简单的FIFO顺序分配任务给空闲的无人机。
        优先选择距离任务起点最近的无人机。
        """
        # 过滤出待分配的任务和空闲的无人机
        pending_tasks = [t for t in tasks if t.status == "pending" and t.assigned_uav is None]
        idle_uavs = [u for u in uavs if u.is_idle()]

        # 按优先级降序排序
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)

        assignments = []

        for task in pending_tasks:
            if not idle_uavs:
                break

            # 选择距离任务起点最近的无人机
            best_uav = min(
                idle_uavs,
                key=lambda uav: calculate_distance(uav.position, task.start_point)
            )

            # 检查任务可行性
            if not self.can_complete_task(best_uav, task):
                self.logger.warning(
                    f"Task {task.id} cannot be completed by UAV {best_uav.id} "
                    f"(battery: {best_uav.battery}, energy needed: "
                    f"{self.calculate_energy_consumption(best_uav, task):.2f})"
                )
                continue

            # 分配任务
            best_uav.assign_task(task)
            task.assign_to_uav(best_uav)
            task.status = "in_progress"
            assignments.append((task, best_uav))

            # 记录决策日志
            energy = self.calculate_energy_consumption(best_uav, task)
            dist = calculate_distance(best_uav.position, task.start_point)
            self.logger.info(
                f"[BASELINE_DIRECT] Task={task.id} | UAV={best_uav.id} | "
                f"Distance={dist:.2f} | Battery={best_uav.battery}% | "
                f"Energy={energy:.2f}"
            )

            idle_uavs.remove(best_uav)

        self.logger.info(
            f"[BASELINE_DIRECT] Result: total={len(tasks)}, "
            f"assigned={len(assignments)}, unassigned={len(tasks) - len(assignments)}"
        )

        return assignments

    def _assign_tasks_relay_coop(self, tasks, uavs, agvs):
        """中继合作策略 (relay_coop)

        为任务分配最近的中继点，利用AGV作为中继站进行协同配送。
        优先选择与AGV位置更近的任务点。
        """
        pending_tasks = [t for t in tasks if t.status == "pending" and t.assigned_uav is None]
        idle_uavs = [u for u in uavs if u.is_idle()]

        # 按优先级降序排序
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)

        assignments = []
        relay_distance = 200.0  # 中继距离阈值

        for task in pending_tasks:
            if not idle_uavs or not agvs:
                break

            # 使用Dijkstra算法选择最优AGV（考虑带障碍物的路径）
            nearest_agv = self.dijkstra_agv_selection(
                idle_uavs[0], agvs, task
            )

            if not nearest_agv:
                # 如果Dijkstra失败，回退到贪心选择
                nearest_agv = min(
                    agvs,
                    key=lambda agv: calculate_distance(agv.position, task.start_point)
                )

            # 计算方向向量
            dx = task.start_point[0] - nearest_agv.position[0]
            dy = task.start_point[1] - nearest_agv.position[1]
            dist = (dx**2 + dy**2) ** 0.5
            if dist > 0:
                direction = (dx / dist, dy / dist)
            else:
                direction = (0.0, 0.0)

            # 计算中继点
            relay_point = (
                nearest_agv.position[0] + direction[0] * relay_distance,
                nearest_agv.position[1] + direction[1] * relay_distance,
            )

            # 选择最近的UAV
            best_uav = min(
                idle_uavs,
                key=lambda uav: calculate_distance(uav.position, task.start_point)
            )

            # 检查任务可行性
            if not self.can_complete_task(best_uav, task):
                self.logger.warning(
                    f"Task {task.id} cannot be completed by UAV {best_uav.id}"
                )
                continue

            # 分配任务
            best_uav.assign_task(task)
            task.assign_to_uav(best_uav)
            task.status = "in_progress"
            task.relay_point = relay_point
            task.assigned_agv = nearest_agv
            assignments.append((task, best_uav))

            # 记录决策日志
            agv_dist = calculate_distance(nearest_agv.position, task.start_point)
            energy = self.calculate_energy_consumption(best_uav, task)
            self.logger.info(
                f"[RELAY_COOP] Task={task.id} | UAV={best_uav.id} | "
                f"AGV={nearest_agv.id} | RelayPoint=({relay_point[0]:.1f},{relay_point[1]:.1f}) | "
                f"AGV_Dist={agv_dist:.2f} | Energy={energy:.2f}"
            )

            idle_uavs.remove(best_uav)

        self.logger.info(
            f"[RELAY_COOP] Result: total={len(tasks)}, "
            f"assigned={len(assignments)}, unassigned={len(tasks) - len(assignments)}"
        )

        return assignments

    def _assign_tasks_energy_priority(self, tasks, uavs, agvs):
        """能耗优先策略 (energy_priority)

        基于估算的能量消耗分配任务，优先选择能耗最低的UAV。
        考虑电池电量和任务距离的综合影响。
        """
        pending_tasks = [t for t in tasks if t.status == "pending" and t.assigned_uav is None]
        idle_uavs = [u for u in uavs if u.is_idle()]

        # 按优先级降序排序
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)

        assignments = []
        total_estimated_energy = 0.0

        for task in pending_tasks:
            if not idle_uavs:
                break

            # 计算每个UAV执行任务的预估能耗
            uav_energy_costs = []
            for uav in idle_uavs:
                distance = calculate_distance(uav.position, task.start_point)
                distance += calculate_distance(task.start_point, task.end_point)

                # 能耗因子：电量越低，能耗越高
                battery_factor = 1.0 + max(0.0, (100.0 - uav.battery) / 100.0 * 0.3)
                payload = float(getattr(task, 'payload', 1.0))
                payload_factor = 1.0 + payload * 0.1

                estimated_energy = distance * battery_factor * payload_factor
                uav_energy_costs.append((uav, estimated_energy))

            # 选择能耗最低的UAV
            uav_energy_costs.sort(key=lambda item: item[1])
            best_uav, min_energy = uav_energy_costs[0]

            # 检查任务可行性
            if not self.can_complete_task(best_uav, task):
                self.logger.warning(
                    f"Task {task.id} cannot be completed by UAV {best_uav.id}"
                )
                continue

            # 分配任务
            best_uav.assign_task(task)
            task.assign_to_uav(best_uav)
            task.status = "in_progress"
            assignments.append((task, best_uav))
            total_estimated_energy += min_energy

            # 记录决策日志
            dist = calculate_distance(best_uav.position, task.start_point)
            self.logger.info(
                f"[ENERGY_PRIORITY] Task={task.id} | UAV={best_uav.id} | "
                f"Distance={dist:.2f} | Battery={best_uav.battery}% | "
                f"EstEnergy={min_energy:.2f}"
            )

            idle_uavs.remove(best_uav)

        self.logger.info(
            f"[ENERGY_PRIORITY] Result: total={len(tasks)}, "
            f"assigned={len(assignments)}, unassigned={len(tasks) - len(assignments)}, "
            f"total_energy={total_estimated_energy:.2f}"
        )

        return assignments

    def _assign_tasks_ga_optimized(self, tasks, uavs, agvs):
        """遗传算法优化策略 (ga_optimized)

        使用遗传算法进行多目标优化任务分配。
        优化目标：能耗 + 时间 + 任务完成率
        """
        self.logger.info(f"[GA_OPTIMIZED] Starting genetic algorithm optimization...")

        # 使用遗传算法进行任务分配
        assignments = self.genetic_algorithm_task_assignment(
            tasks, uavs, agvs,
            population_size=20,
            generations=50
        )

        # 更新任务状态
        for task, uav in assignments:
            task.status = "in_progress"
            uav.assign_task(task)
            task.assign_to_uav(uav)

        self.logger.info(
            f"[GA_OPTIMIZED] Result: total={len(tasks)}, "
            f"assigned={len(assignments)}, unassigned={len(tasks) - len(assignments)}"
        )

        return assignments

    def assign_tasks(self, tasks, uavs, agvs=None):
        """分配任务给无人机

        使用指定策略进行任务分配。

        Args:
            tasks: 任务列表
            uavs: 无人机列表
            agvs: AGV列表（用于relay_coop策略）

        Returns:
            list: 分配结果列表，每个元素为 (task, uav) 元组
        """
        if agvs is None:
            agvs = []

        # 根据策略类型选择对应的分配方法
        if self.strategy_type == self.STRATEGY_BASELINE_DIRECT:
            return self._assign_tasks_baseline_direct(tasks, uavs, agvs)
        elif self.strategy_type == self.STRATEGY_RELAY_COOP:
            return self._assign_tasks_relay_coop(tasks, uavs, agvs)
        elif self.strategy_type == self.STRATEGY_ENERGY_PRIORITY:
            return self._assign_tasks_energy_priority(tasks, uavs, agvs)
        elif self.strategy_type == self.STRATEGY_GA_OPTIMIZED:
            return self._assign_tasks_ga_optimized(tasks, uavs, agvs)
        else:
            # 默认使用基线直送策略
            return self._assign_tasks_baseline_direct(tasks, uavs, agvs)

    # ==================== AGV选择策略 ====================

    def _select_agv_baseline_direct(self, uav, agvs):
        """基线直送策略的AGV选择

        选择第一个可用的AGV。
        """
        available_agvs = [a for a in agvs if a.status == "idle"]
        if not available_agvs:
            self.logger.warning(f"[BASELINE_DIRECT] No available AGV for UAV {uav.id}")
            return None

        selected = available_agvs[0]
        self.logger.info(
            f"[BASELINE_DIRECT] Select AGV {selected.id} for UAV {uav.id}, "
            f"uav_battery={uav.battery}%"
        )
        return selected

    def _select_agv_relay_coop(self, uav, agvs):
        """中继合作策略的AGV选择

        优先选择与当前任务关联的AGV，否则选择最近的AGV。
        """
        current_task = uav.task

        # 优先使用任务关联的AGV
        if current_task and getattr(current_task, "assigned_agv", None):
            if current_task.assigned_agv.status == "idle":
                self.logger.info(
                    f"[RELAY_COOP] Select paired AGV {current_task.assigned_agv.id} "
                    f"for UAV {uav.id}"
                )
                return current_task.assigned_agv

        # 选择最近的可用AGV
        available_agvs = [a for a in agvs if a.status == "idle"]
        if not available_agvs:
            self.logger.warning(f"[RELAY_COOP] No available AGV for UAV {uav.id}")
            return None

        selected = min(
            available_agvs,
            key=lambda agv: calculate_distance(agv.position, uav.position)
        )
        self.logger.info(
            f"[RELAY_COOP] Select nearest AGV {selected.id} for UAV {uav.id}, "
            f"uav_battery={uav.battery}%"
        )
        return selected

    def _select_agv_energy_priority(self, uav, agvs):
        """能耗优先策略的AGV选择

        综合评分选择最佳AGV（距离60% + 充电功率40%）。
        """
        available_agvs = [a for a in agvs if a.status == "idle"]
        if not available_agvs:
            self.logger.warning(f"[ENERGY_PRIORITY] No available AGV for UAV {uav.id}")
            return None

        scored = []
        for agv in available_agvs:
            distance = calculate_distance(agv.position, uav.position)
            # 距离评分：距离越近分数越高
            distance_score = 1.0 / (1.0 + distance / 100.0)
            # 功率评分：充电功率越高分数越高
            charging_power = float(getattr(agv, "charging_power", 200.0))
            power_score = charging_power / 200.0
            # 综合评分
            total_score = distance_score * 0.6 + power_score * 0.4
            scored.append((agv, total_score, distance, charging_power))

        scored.sort(key=lambda item: item[1], reverse=True)
        best_agv, best_score, distance, power = scored[0]

        self.logger.info(
            f"[ENERGY_PRIORITY] Select AGV {best_agv.id} for UAV {uav.id}, "
            f"distance={distance:.2f}, charging_power={power}, score={best_score:.4f}"
        )
        return best_agv

    def select_agv(self, uav, agvs):
        """选择AGV为无人机充电

        Args:
            uav: 无人机对象
            agvs: AGV列表

        Returns:
            AGV: 选择的AGV对象，如果没有可用AGV则返回None
        """
        if not agvs:
            return None

        # 根据策略类型选择对应的AGV选择方法
        if self.strategy_type == self.STRATEGY_BASELINE_DIRECT:
            return self._select_agv_baseline_direct(uav, agvs)
        elif self.strategy_type == self.STRATEGY_RELAY_COOP:
            return self._select_agv_relay_coop(uav, agvs)
        elif self.strategy_type == self.STRATEGY_ENERGY_PRIORITY:
            return self._select_agv_energy_priority(uav, agvs)
        else:
            return self._select_agv_baseline_direct(uav, agvs)

    def run_scenario(self, tasks, uavs, agvs=None):
        """运行场景并返回结果

        Args:
            tasks: 任务列表
            uavs: 无人机列表
            agvs: AGV列表

        Returns:
            dict: 场景运行结果，包含策略信息、任务分配统计、能耗等
        """
        if agvs is None:
            agvs = []

        # 执行任务分配
        assignments = self.assign_tasks(tasks, uavs, agvs)

        # 计算总预估能耗
        total_energy = 0.0
        for task, uav in assignments:
            energy = self.calculate_energy_consumption(uav, task)
            total_energy += energy

        # 统计已分配和未分配任务
        assigned_task_ids = set()
        for task, _ in assignments:
            assigned_task_ids.add(task.id)

        unassigned_count = sum(1 for t in tasks if t.id not in assigned_task_ids)

        # 返回结果字典
        return {
            "strategy": self.strategy_type,
            "total_tasks": len(tasks),
            "assigned_count": len(assignments),
            "unassigned_count": unassigned_count,
            "total_energy": total_energy,
            "assignments": assignments
        }

    def plan_uav_path(self, uav, start_point, end_point, obstacles=None, algorithm='straight'):
        """使用统一的PathPlanner规划无人机路径

        Args:
            uav: 无人机对象
            start_point: 起点位置
            end_point: 终点位置
            obstacles: 障碍物列表
            algorithm: 路径规划算法 ('a_star', 'rrt', 'straight')

        Returns:
            list: 路径点列表
        """
        return self.path_planner.plan_path(start_point, end_point, obstacles, algorithm)

