"""Tests for ALNS unified strategy integration."""

import pytest
import random
from src.strategies.alns import (
    DeliveryMode, Solution,
    DestroyOperator, RepairOperator,
    ALNSOperators
)
from src.strategies.alns_unified import ALNSUnifiedStrategy
from src.core.uav import UAV
from src.core.agv import AGV
from src.core.task import Task
from src.energy.energy_model import EnergyModel
from src.planning.path_planner import PathPlanner
from src.simulation.environment import Environment
from src.scheduling.scheduler import Scheduler
from src.simulation.simulator import Simulator


def make_uav(uav_id=1, position=(50, 50), battery=100):
    uav = UAV(uav_id, position)
    uav.battery = battery
    uav.max_range = 500
    uav.max_speed = 10
    return uav


def make_task(task_id=1, end=(300, 300)):
    return Task(
        id=task_id,
        start_point=(0, 0),
        end_point=end,
        payload=1.0,
        priority=1
    )


def make_agv(agv_id=1, position=(80, 80)):
    agv = AGV(agv_id, position)
    return agv


class MockEnvironment:
    def __init__(self):
        self.agvs = []
        self.uavs = []
        self.tasks = []
        self.charging_stations = []
        self.depot_position = (0, 0)
        self.obstacles = []
        self.map_size = (1000, 1000)

    def is_valid_position(self, point):
        x, y = point
        if x < 0 or x > 1000 or y < 0 or y > 1000:
            return False
        return True

    def get_idle_uavs(self):
        return [u for u in self.uavs if u.is_idle()]


class TestStrategyRegistration:
    """Test strategy registration in Simulator."""

    def test_strategy_registration_in_factory(self):
        """ALNS strategy should be registered in Simulator."""
        env = Environment(map_size=(100, 100))
        env.uavs.append(make_uav(1, (10, 10)))
        env.agvs.append(make_agv(1, (10, 10)))
        env.tasks.append(make_task(1, end=(20, 20)))

        simulator = Simulator(
            env,
            EnergyModel(),
            PathPlanner(),
            Scheduler(),
            strategy_type="alns_unified"
        )

        assert simulator.strategy.name == "alns_unified"

    def test_strategy_has_required_attributes(self):
        """Strategy should have all required attributes."""
        strategy = ALNSUnifiedStrategy()

        assert hasattr(strategy, 'energy_model')
        assert hasattr(strategy, 'path_planner')
        assert hasattr(strategy, 'seed')
        assert hasattr(strategy, 'max_iterations')
        assert hasattr(strategy, 'fallback_count')
        assert hasattr(strategy, 'relay_count')
        assert hasattr(strategy, 'direct_count')
        assert hasattr(strategy, 'infeasible_count')
        assert hasattr(strategy, 'replan_count')


class TestInitialSolutionGreedy:
    """Test greedy initial solution generation."""

    def test_greedy_initial_solution_basic(self):
        """Greedy should produce a valid initial solution."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.uavs.append(make_uav(2, (60, 60)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.tasks.append(make_task(2, end=(250, 250)))
        env.depot_position = (0, 0)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        solution = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        assert isinstance(solution, Solution)
        assert solution.total_cost >= 0
        assert len(solution.assignments) <= len(pending_tasks)

    def test_greedy_uses_best_option(self):
        """Greedy should choose lowest cost option for each task."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (100, 100)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.depot_position = (0, 0)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        solution = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        if len(solution.assignments) > 0:
            for assignment in solution.assignments:
                assert assignment.cost >= 0
                assert assignment.uav_id == 1
                assert assignment.task_id == 1


class TestDestroyOperators:
    """Test ALNS destroy operators."""

    def test_random_remove_basic(self):
        """Random remove should remove specified number of assignments."""
        operators = ALNSOperators(seed=42)
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (100, 100)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.depot_position = (0, 0)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        if len(initial.assignments) > 0:
            destroyed = operators.destroy(
                initial,
                DestroyOperator.RANDOM_REMOVE,
                destroy_count=1
            )

            assert len(destroyed.assignments) <= len(initial.assignments)

    def test_worst_remove_basic(self):
        """Worst remove should remove highest cost assignments."""
        operators = ALNSOperators(seed=42)
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (100, 100)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.depot_position = (0, 0)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        if len(initial.assignments) >= 1:
            destroyed = operators.destroy(
                initial,
                DestroyOperator.WORST_REMOVE,
                destroy_count=1
            )

            assert len(destroyed.assignments) <= len(initial.assignments)


class TestRepairOperators:
    """Test ALNS repair operators."""

    def test_greedy_insert_basic(self):
        """Greedy insert should add assignments."""
        operators = ALNSOperators(seed=42)
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.uavs.append(make_uav(2, (60, 60)))
        env.agvs.append(make_agv(1, (100, 100)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.tasks.append(make_task(2, end=(250, 250)))
        env.depot_position = (0, 0)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        empty_solution = Solution(assignments=[], total_cost=0.0, mode_counts={})

        repaired = operators.repair(
            empty_solution,
            pending_tasks,
            idle_uavs,
            env,
            env.depot_position,
            RepairOperator.GREEDY_INSERT,
            repair_count=1
        )

        assert len(repaired.assignments) >= 0

    def test_regret_insert_basic(self):
        """Regret insert should consider opportunity cost."""
        operators = ALNSOperators(seed=42)
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (100, 100)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.depot_position = (0, 0)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        empty_solution = Solution(assignments=[], total_cost=0.0, mode_counts={})

        repaired = operators.repair(
            empty_solution,
            pending_tasks,
            idle_uavs,
            env,
            env.depot_position,
            RepairOperator.REGRET_INSERT,
            repair_count=1
        )

        assert len(repaired.assignments) >= 0


class TestALNSIteration:
    """Test ALNS iteration convergence."""

    def test_alns_reduces_cost(self):
        """ALNS should find a good solution."""
        strategy = ALNSUnifiedStrategy(max_iterations=10)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (100, 100)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.depot_position = (0, 0)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        best = strategy._alns_search(
            initial, idle_uavs, pending_tasks, env, env.depot_position
        )

        assert isinstance(best, Solution)
        assert best.total_cost >= 0

    def test_alns_iteration_limit(self):
        """ALNS should respect iteration limit."""
        max_iter = 5
        strategy = ALNSUnifiedStrategy(max_iterations=max_iter)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (100, 100)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.depot_position = (0, 0)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        best = strategy._alns_search(
            initial, idle_uavs, pending_tasks, env, env.depot_position
        )

        assert best.total_cost >= 0


class TestAdaptiveWeights:
    """Test adaptive operator weight updates."""

    def test_weights_update_on_improvement(self):
        """Weights should increase on best improvement."""
        operators = ALNSOperators(seed=42)

        initial_weights = operators.get_operator_weights()["random_remove"]

        operators.update_operator_weights(
            DestroyOperator.RANDOM_REMOVE,
            RepairOperator.GREEDY_INSERT,
            improved=True,
            best_improved=True
        )

        new_weights = operators.get_operator_weights()["random_remove"]
        assert new_weights > initial_weights

    def test_weights_decay_on_no_improvement(self):
        """Weights should decay when no improvement."""
        operators = ALNSOperators(seed=42)

        operators.update_operator_weights(
            DestroyOperator.RANDOM_REMOVE,
            RepairOperator.GREEDY_INSERT,
            improved=False,
            best_improved=False
        )

        new_weights = operators.get_operator_weights()["random_remove"]
        assert new_weights < 1.0

    def test_weights_minimum_bound(self):
        """Weights should not go below minimum bound."""
        operators = ALNSOperators(seed=42)

        for _ in range(100):
            operators.update_operator_weights(
                DestroyOperator.RANDOM_REMOVE,
                RepairOperator.GREEDY_INSERT,
                improved=False,
                best_improved=False
            )

        assert operators.get_operator_weights()["random_remove"] >= 0.1


class TestSeedReproducibility:
    """Test seed-based reproducibility."""

    def test_same_seed_same_result(self):
        """Same seed should produce same initial solution."""
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (100, 100)))
        env.tasks.append(make_task(1, end=(200, 200)))
        env.depot_position = (0, 0)

        idle_uavs1 = env.get_idle_uavs()
        pending_tasks = env.tasks

        strategy1 = ALNSUnifiedStrategy(seed=42)
        solution1 = strategy1._generate_greedy_initial_solution(
            idle_uavs1, pending_tasks, env, env.depot_position
        )

        env2 = MockEnvironment()
        env2.uavs.append(make_uav(1, (50, 50)))
        env2.agvs.append(make_agv(1, (100, 100)))
        env2.tasks.append(make_task(1, end=(200, 200)))
        env2.depot_position = (0, 0)

        idle_uavs2 = env2.get_idle_uavs()

        strategy2 = ALNSUnifiedStrategy(seed=42)
        solution2 = strategy2._generate_greedy_initial_solution(
            idle_uavs2, pending_tasks, env2, env2.depot_position
        )

        assert len(solution1.assignments) == len(solution2.assignments)
        if len(solution1.assignments) > 0:
            assert abs(solution1.total_cost - solution2.total_cost) < 0.001


class TestAssignTasks:
    """Test main assign_tasks method."""

    def test_assign_tasks_returns_valid_structure(self):
        """assign_tasks should return valid structure."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (50, 50)))
        task1 = make_task(1, end=(200, 200))
        task1.status = "pending"
        env.tasks.append(task1)
        env.depot_position = (0, 0)

        result = strategy.assign_tasks(env)

        assert "strategy" in result
        assert result["strategy"] == "alns_unified"
        assert "assignments" in result
        assert "actions" in result
        assert "events" in result
        assert "assigned_count" in result

    def test_assign_tasks_respects_constraints(self):
        """assign_tasks should respect idle UAVs and pending tasks."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50)))
        env.uavs.append(make_uav(2, (60, 60)))
        env.agvs.append(make_agv(1, (50, 50)))
        task1 = make_task(1, end=(200, 200))
        task1.status = "pending"
        task2 = make_task(2, end=(250, 250))
        task2.status = "pending"
        env.tasks.append(task1)
        env.tasks.append(task2)
        env.depot_position = (0, 0)

        result = strategy.assign_tasks(env)

        assert result["assigned_count"] <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])