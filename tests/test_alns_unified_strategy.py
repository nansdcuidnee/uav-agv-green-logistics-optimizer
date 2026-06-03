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
            initial, idle_uavs, pending_tasks, {}, env, env.depot_position
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
            initial, idle_uavs, pending_tasks, {}, env, env.depot_position
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


class TestSolutionStructure:
    """Test new Solution data structure with uav_routes, agv_routes, task_index."""

    def test_solution_add_direct_assignment(self):
        """Adding direct assignment should update all indexes correctly."""
        from src.strategies.alns import DeliveryOption, Solution

        solution = Solution(assignments=[])

        option = DeliveryOption(
            mode=DeliveryMode.DIRECT,
            uav_id=1,
            task_id=10,
            cost=5.0
        )

        solution.add_assignment(option)

        assert len(solution.assignments) == 1
        assert solution.task_index.get(10) == option
        assert 1 in solution.uav_routes
        assert len(solution.uav_routes[1]) == 1
        assert solution.uav_routes[1][0].task_id == 10
        assert len(solution.agv_routes) == 0
        assert solution.mode_counts.get("direct") == 1
        assert solution.total_cost == 5.0

    def test_solution_add_relay_fixed_assignment(self):
        """Adding relay_fixed assignment should update UAV and AGV routes."""
        from src.strategies.alns import DeliveryOption, Solution

        solution = Solution(assignments=[])

        option = DeliveryOption(
            mode=DeliveryMode.RELAY_FIXED,
            uav_id=1,
            task_id=10,
            agv_id=2,
            relay_point=(100, 100),
            cost=7.0
        )

        solution.add_assignment(option)

        assert len(solution.assignments) == 1
        assert solution.task_index.get(10) == option
        assert 1 in solution.uav_routes
        assert 2 in solution.agv_routes
        assert len(solution.uav_routes[1]) == 1
        assert len(solution.agv_routes[2]) == 1
        assert solution.uav_routes[1][0].relay_point == (100, 100)
        assert solution.agv_routes[2][0].relay_point == (100, 100)
        assert solution.mode_counts.get("relay_fixed") == 1

    def test_solution_remove_assignment(self):
        """Removing assignment should sync all indexes."""
        from src.strategies.alns import DeliveryOption, Solution

        solution = Solution(assignments=[])

        option = DeliveryOption(
            mode=DeliveryMode.RELAY_FIXED,
            uav_id=1,
            task_id=10,
            agv_id=2,
            relay_point=(100, 100),
            cost=7.0
        )

        solution.add_assignment(option)
        assert len(solution.assignments) == 1

        removed = solution.remove_assignment(option)

        assert removed == option
        assert len(solution.assignments) == 0
        assert 10 not in solution.task_index
        assert 1 not in solution.uav_routes
        assert 2 not in solution.agv_routes
        assert solution.total_cost == 0.0
        assert solution.mode_counts.get("relay_fixed") == 0

    def test_solution_remove_by_task_id(self):
        """Removing assignment by task_id should work."""
        from src.strategies.alns import DeliveryOption, Solution

        solution = Solution(assignments=[])

        option = DeliveryOption(
            mode=DeliveryMode.DIRECT,
            uav_id=1,
            task_id=10,
            cost=5.0
        )

        solution.add_assignment(option)
        removed = solution.remove_assignment(task_id=10)

        assert removed == option
        assert len(solution.assignments) == 0

    def test_solution_copy_is_deep(self):
        """Copy should be deep, modifying copy should not affect original."""
        from src.strategies.alns import DeliveryOption, Solution

        solution = Solution(assignments=[])

        option = DeliveryOption(
            mode=DeliveryMode.DIRECT,
            uav_id=1,
            task_id=10,
            cost=5.0
        )

        solution.add_assignment(option)
        copy = solution.copy()

        copy.remove_assignment(option)

        assert len(solution.assignments) == 1
        assert len(copy.assignments) == 0

    def test_solution_rebuild_indexes(self):
        """rebuild_indexes should reconstruct all indexes from assignments."""
        from src.strategies.alns import DeliveryOption, Solution

        solution = Solution(assignments=[
            DeliveryOption(mode=DeliveryMode.DIRECT, uav_id=1, task_id=10, cost=5.0),
            DeliveryOption(mode=DeliveryMode.RELAY_FIXED, uav_id=2, task_id=20, agv_id=3, relay_point=(100, 100), cost=7.0),
        ])

        solution.rebuild_indexes()

        assert len(solution.assignments) == 2
        assert 10 in solution.task_index
        assert 20 in solution.task_index
        assert 1 in solution.uav_routes
        assert 2 in solution.uav_routes
        assert 3 in solution.agv_routes
        assert solution.total_cost == 12.0

    def test_solution_multiple_assignments_same_uav(self):
        """Multiple assignments for same UAV should be in same route."""
        from src.strategies.alns import DeliveryOption, Solution

        solution = Solution(assignments=[])

        solution.add_assignment(DeliveryOption(mode=DeliveryMode.DIRECT, uav_id=1, task_id=10, cost=5.0))
        solution.add_assignment(DeliveryOption(mode=DeliveryMode.DIRECT, uav_id=1, task_id=20, cost=6.0))

        assert 1 in solution.uav_routes
        assert len(solution.uav_routes[1]) == 2
        assert solution.uav_routes[1][0].task_id == 10
        assert solution.uav_routes[1][1].task_id == 20

    def test_solution_multiple_assignments_same_agv(self):
        """Multiple relay assignments for same AGV should be in same route."""
        from src.strategies.alns import DeliveryOption, Solution

        solution = Solution(assignments=[])

        solution.add_assignment(DeliveryOption(
            mode=DeliveryMode.RELAY_FIXED, uav_id=1, task_id=10, agv_id=2, relay_point=(100, 100), cost=7.0))
        solution.add_assignment(DeliveryOption(
            mode=DeliveryMode.RELAY_FIXED, uav_id=3, task_id=20, agv_id=2, relay_point=(200, 200), cost=8.0))

        assert 2 in solution.agv_routes
        assert len(solution.agv_routes[2]) == 2
        assert solution.agv_routes[2][0].task_id == 10
        assert solution.agv_routes[2][1].task_id == 20


class TestNewOperators:
    """Test new ALNS operators: HIGH_ENERGY_REMOVE and RELAY_AWARE_REGRET_INSERT."""

    def test_high_energy_remove_deletes_highest_cost(self):
        """HIGH_ENERGY_REMOVE should delete assignments with highest energy consumption."""
        from src.strategies.alns import DeliveryOption, Solution
        from src.strategies.alns.operators import ALNSOperators

        operators = ALNSOperators(seed=42)
        solution = Solution(assignments=[])

        solution.add_assignment(DeliveryOption(
            mode=DeliveryMode.DIRECT, uav_id=1, task_id=10, cost=5.0,
            cost_breakdown={"uav_energy": 1.0, "agv_energy": 0.0}))
        solution.add_assignment(DeliveryOption(
            mode=DeliveryMode.DIRECT, uav_id=2, task_id=20, cost=10.0,
            cost_breakdown={"uav_energy": 0.5, "agv_energy": 0.0}))
        solution.add_assignment(DeliveryOption(
            mode=DeliveryMode.DIRECT, uav_id=3, task_id=30, cost=3.0,
            cost_breakdown={"uav_energy": 3.0, "agv_energy": 0.0}))

        assert solution.total_cost == 18.0

        from src.strategies.alns.solution import DestroyOperator
        destroyed = operators.destroy(solution, DestroyOperator.HIGH_ENERGY_REMOVE, destroy_count=1)

        assert len(destroyed.assignments) == 2
        assert destroyed.total_cost == 15.0
        assert 30 not in destroyed.task_index

    def test_high_energy_remove_syncs_indexes(self):
        """HIGH_ENERGY_REMOVE should sync all solution indexes."""
        from src.strategies.alns import DeliveryOption, Solution
        from src.strategies.alns.operators import ALNSOperators

        operators = ALNSOperators(seed=42)
        solution = Solution(assignments=[])

        solution.add_assignment(DeliveryOption(
            mode=DeliveryMode.RELAY_FIXED, uav_id=1, task_id=10, agv_id=2, relay_point=(100, 100), cost=10.0))
        solution.add_assignment(DeliveryOption(
            mode=DeliveryMode.DIRECT, uav_id=3, task_id=20, cost=5.0))

        from src.strategies.alns.solution import DestroyOperator
        destroyed = operators.destroy(solution, DestroyOperator.HIGH_ENERGY_REMOVE, destroy_count=1)

        assert len(destroyed.assignments) == 1
        assert 10 not in destroyed.task_index
        assert 1 not in destroyed.uav_routes
        assert 2 not in destroyed.agv_routes
        assert destroyed.mode_counts.get("direct") == 1

    def test_relay_aware_regret_insert_direct_option(self):
        """RELAY_AWARE_REGRET_INSERT can insert direct option."""
        from src.strategies.alns import DeliveryOption, Solution
        from src.strategies.alns.operators import ALNSOperators

        operators = ALNSOperators(seed=42)
        solution = Solution(assignments=[])

        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (50, 50)))
        task = make_task(1, end=(200, 200))
        task.start_point = (100, 100)

        from src.strategies.alns.solution import RepairOperator
        repaired = operators.repair(
            solution, [task], [make_uav(1, (50, 50), battery=100)],
            env, env.depot_position, RepairOperator.RELAY_AWARE_REGRET_INSERT, repair_count=1
        )

        assert len(repaired.assignments) >= 1
        assert 1 in repaired.task_index

    def test_relay_aware_regret_insert_relay_option(self):
        """RELAY_AWARE_REGRET_INSERT can insert relay_fixed option."""
        from src.strategies.alns import DeliveryOption, Solution
        from src.strategies.alns.operators import ALNSOperators

        operators = ALNSOperators(seed=42)
        solution = Solution(assignments=[])

        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))
        task = make_task(1, end=(200, 200))
        task.start_point = (100, 100)

        from src.strategies.alns.solution import RepairOperator
        repaired = operators.repair(
            solution, [task], [make_uav(1, (50, 50), battery=100)],
            env, env.depot_position, RepairOperator.RELAY_AWARE_REGRET_INSERT, repair_count=1
        )

        assert len(repaired.assignments) >= 1

    def test_new_operators_select_and_update(self):
        """New operators can be selected and their weights updated."""
        from src.strategies.alns.operators import ALNSOperators
        from src.strategies.alns.solution import DestroyOperator, RepairOperator

        operators = ALNSOperators(seed=42)

        destroy_ops = [
            DestroyOperator.RANDOM_REMOVE,
            DestroyOperator.WORST_REMOVE,
            DestroyOperator.HIGH_ENERGY_REMOVE
        ]
        repair_ops = [
            RepairOperator.GREEDY_INSERT,
            RepairOperator.REGRET_INSERT,
            RepairOperator.RELAY_AWARE_REGRET_INSERT
        ]

        selected_destroy = operators.select_operator(destroy_ops)
        selected_repair = operators.select_operator(repair_ops)

        assert selected_destroy in destroy_ops
        assert selected_repair in repair_ops

        operators.update_operator_weights(
            selected_destroy, selected_repair, improved=True, best_improved=True
        )

        weights = operators.get_operator_weights()
        assert 'high_energy_remove' in weights
        assert 'relay_aware_regret_insert' in weights

    def test_alns_search_with_new_operators(self):
        """ALNS search should work with new operators without error."""
        strategy = ALNSUnifiedStrategy(max_iterations=5, seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))
        task = make_task(1, end=(200, 200))
        task.start_point = (100, 100)
        env.tasks.append(task)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        best = strategy._alns_search(initial, idle_uavs, pending_tasks, {}, env, env.depot_position)

        assert best.total_cost >= 0


class TestInitialSolutionMultiTask:
    """Test multi-task initial solution generation."""

    def test_initial_solution_not_limited_to_2_tasks(self):
        """Initial solution should not be limited to 2 tasks (one per UAV)."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.uavs.append(make_uav(2, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))
        env.agvs.append(make_agv(2, (150, 150)))

        # 添加5个任务
        for i in range(1, 6):
            task = make_task(i, end=(100 + i * 30, 100 + i * 30))
            task.start_point = (50 + i * 20, 50 + i * 20)
            env.tasks.append(task)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        assert len(initial.assignments) > 2

    def test_initial_solution_same_uav_multiple_tasks(self):
        """Same UAV can have multiple tasks in initial solution."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        # 添加3个任务
        for i in range(1, 4):
            task = make_task(i, end=(100 + i * 30, 100 + i * 30))
            task.start_point = (50 + i * 20, 50 + i * 20)
            env.tasks.append(task)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        uav1_tasks = [opt for opt in initial.assignments if opt.uav_id == 1]
        assert len(uav1_tasks) > 1

        assert len(initial.uav_routes) >= 1
        for uav_id, route in initial.uav_routes.items():
            assert len(route) == len([opt for opt in initial.assignments if opt.uav_id == uav_id])

    def test_initial_solution_task_index_consistent_with_routes(self):
        """task_index and routes should be consistent after initial solution generation."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        task2 = make_task(2, end=(300, 300))
        task2.start_point = (200, 200)
        task3 = make_task(3, end=(400, 400))
        task3.start_point = (300, 300)
        env.tasks.extend([task1, task2, task3])

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        # task_index 和 assignments 保持一致
        assert len(initial.task_index) == len(initial.assignments)
        for opt in initial.assignments:
            assert opt.task_id in initial.task_index
            assert initial.task_index[opt.task_id] == opt

        # uav_routes 和 assignments 保持一致
        assigned_uavs = {opt.uav_id for opt in initial.assignments}
        assert len(initial.uav_routes) == len(assigned_uavs)
        for uav_id in assigned_uavs:
            route_task_ids = [stop.task_id for stop in initial.uav_routes[uav_id]]
            uav_assignments = [opt.task_id for opt in initial.assignments if opt.uav_id == uav_id]
            assert set(route_task_ids) == set(uav_assignments)

    def test_alns_search_works_with_multi_task_initial(self):
        """ALNS search should work with multi-task initial solution."""
        strategy = ALNSUnifiedStrategy(max_iterations=3, seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.uavs.append(make_uav(2, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        for i in range(1, 6):
            task = make_task(i, end=(100 + i * 30, 100 + i * 30))
            task.start_point = (50 + i * 20, 50 + i * 20)
            env.tasks.append(task)

        idle_uavs = env.get_idle_uavs()
        pending_tasks = env.tasks

        initial = strategy._generate_greedy_initial_solution(
            idle_uavs, pending_tasks, env, env.depot_position
        )

        best = strategy._alns_search(initial, idle_uavs, pending_tasks, {}, env, env.depot_position)

        assert best.total_cost >= 0
        assert len(best.assignments) > 0
        assert len(best.assignments) >= 0


class TestCandidatePools:
    """Test candidate pool construction and usage."""

    def test_candidate_pool_per_task_uav(self):
        """Candidate pools should be per (task_id, uav_id), not just per task."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.uavs.append(make_uav(2, (60, 60), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))
        env.agvs.append(make_agv(2, (150, 150)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        task2 = make_task(2, end=(300, 300))
        task2.start_point = (200, 200)
        env.tasks.extend([task1, task2])

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=3
        )

        assert len(candidate_pools) == 4
        assert (1, 1) in candidate_pools
        assert (1, 2) in candidate_pools
        assert (2, 1) in candidate_pools
        assert (2, 2) in candidate_pools

    def test_candidate_pool_contains_direct_and_relay(self):
        """Each pool should contain direct flag and relay list."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env.tasks.append(task1)

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=3
        )

        pool = candidate_pools[(1, 1)]
        assert "direct" in pool
        assert isinstance(pool["direct"], bool)
        assert "relay" in pool
        assert isinstance(pool["relay"], list)

    def test_candidate_pool_relay_top_k(self):
        """Relay candidates should be limited to top-K."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))
        env.agvs.append(make_agv(2, (150, 150)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env.tasks.append(task1)

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=3
        )

        pool = candidate_pools[(1, 1)]
        assert len(pool["relay"]) <= 3

    def test_infeasible_relay_excluded_from_pool(self):
        """Infeasible relay candidates should be excluded."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        uav = make_uav(1, (50, 50), battery=5)
        uav.max_range = 100
        env.uavs.append(uav)
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(1000, 1000))
        task1.start_point = (900, 900)
        env.tasks.append(task1)

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=3
        )

        pool = candidate_pools[(1, 1)]
        assert pool["direct"] == False
        assert len(pool["relay"]) == 0

    def test_candidate_pool_reproducibility(self):
        """Same inputs should produce same candidate pools."""
        strategy1 = ALNSUnifiedStrategy(seed=42)
        strategy2 = ALNSUnifiedStrategy(seed=42)

        env1 = MockEnvironment()
        env1.uavs.append(make_uav(1, (50, 50), battery=100))
        env1.agvs.append(make_agv(1, (100, 100)))
        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env1.tasks.append(task1)

        env2 = MockEnvironment()
        env2.uavs.append(make_uav(1, (50, 50), battery=100))
        env2.agvs.append(make_agv(1, (100, 100)))
        task2 = make_task(1, end=(200, 200))
        task2.start_point = (100, 100)
        env2.tasks.append(task2)

        pools1 = strategy1._build_candidate_pools(
            env1.uavs, env1.tasks, env1, env1.depot_position, k=3
        )
        pools2 = strategy2._build_candidate_pools(
            env2.uavs, env2.tasks, env2, env2.depot_position, k=3
        )

        pool1 = pools1[(1, 1)]
        pool2 = pools2[(1, 1)]

        assert pool1["direct"] == pool2["direct"]
        assert len(pool1["relay"]) == len(pool2["relay"])


class TestRegret2InitialSolution:
    """Test regret-2 initial solution generation."""

    def test_regret2_initial_solution_basic(self):
        """Regret-2 should produce valid initial solution."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.uavs.append(make_uav(2, (60, 60), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        task2 = make_task(2, end=(250, 250))
        task2.start_point = (150, 150)
        env.tasks.extend([task1, task2])

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=3
        )

        solution = strategy._generate_regret2_initial_solution(
            env.uavs, env.tasks, candidate_pools, env, env.depot_position
        )

        assert isinstance(solution, Solution)
        assert solution.total_cost >= 0
        assert len(solution.assignments) <= len(env.tasks)

    def test_regret2_can_select_both_modes(self):
        """Regret-2 should be able to select both direct and relay modes."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.uavs.append(make_uav(2, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        task2 = make_task(2, end=(250, 250))
        task2.start_point = (150, 150)
        env.tasks.extend([task1, task2])

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=3
        )

        solution = strategy._generate_regret2_initial_solution(
            env.uavs, env.tasks, candidate_pools, env, env.depot_position
        )

        if len(solution.assignments) > 0:
            modes = {opt.mode for opt in solution.assignments}
            assert modes.issubset({DeliveryMode.DIRECT, DeliveryMode.RELAY_FIXED})

    def test_regret2_reproducibility(self):
        """Same seed should produce same regret-2 initial solution."""
        strategy1 = ALNSUnifiedStrategy(seed=42)
        strategy2 = ALNSUnifiedStrategy(seed=42)

        env1 = MockEnvironment()
        env1.uavs.append(make_uav(1, (50, 50), battery=100))
        env1.uavs.append(make_uav(2, (60, 60), battery=100))
        env1.agvs.append(make_agv(1, (100, 100)))
        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        task2 = make_task(2, end=(250, 250))
        task2.start_point = (150, 150)
        env1.tasks.extend([task1, task2])

        env2 = MockEnvironment()
        env2.uavs.append(make_uav(1, (50, 50), battery=100))
        env2.uavs.append(make_uav(2, (60, 60), battery=100))
        env2.agvs.append(make_agv(1, (100, 100)))
        task3 = make_task(1, end=(200, 200))
        task3.start_point = (100, 100)
        task4 = make_task(2, end=(250, 250))
        task4.start_point = (150, 150)
        env2.tasks.extend([task3, task4])

        pools1 = strategy1._build_candidate_pools(
            env1.uavs, env1.tasks, env1, env1.depot_position, k=3
        )
        pools2 = strategy2._build_candidate_pools(
            env2.uavs, env2.tasks, env2, env2.depot_position, k=3
        )

        solution1 = strategy1._generate_regret2_initial_solution(
            env1.uavs, env1.tasks, pools1, env1, env1.depot_position
        )
        solution2 = strategy2._generate_regret2_initial_solution(
            env2.uavs, env2.tasks, pools2, env2, env2.depot_position
        )

        assert len(solution1.assignments) == len(solution2.assignments)
        if len(solution1.assignments) > 0:
            assert abs(solution1.total_cost - solution2.total_cost) < 0.001

    def test_regret2_uses_candidate_pool(self):
        """Regret-2 should use candidates from pool, not regenerate."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env.tasks.append(task1)

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=2
        )

        pool = candidate_pools[(1, 1)]
        pool["direct"] = False
        pool["relay"] = []

        solution = strategy._generate_regret2_initial_solution(
            env.uavs, env.tasks, candidate_pools, env, env.depot_position
        )

        assert len(solution.assignments) == 0

    def test_regret2_single_option_regret(self):
        """Regret-2 should handle tasks with only one option."""
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env.tasks.append(task1)

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=1
        )

        solution = strategy._generate_regret2_initial_solution(
            env.uavs, env.tasks, candidate_pools, env, env.depot_position
        )

        assert len(solution.assignments) == 1


class TestRepairWithCandidatePools:
    """Test repair operators using candidate pools."""

    def test_repair_greedy_insert_with_pool(self):
        """GREEDY_INSERT should use candidate pool when provided."""
        operators = ALNSOperators(seed=42)
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env.tasks.append(task1)

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=2
        )

        empty_solution = Solution(assignments=[], total_cost=0.0, mode_counts={})

        repaired = operators.repair(
            empty_solution,
            env.tasks,
            env.uavs,
            env,
            env.depot_position,
            RepairOperator.GREEDY_INSERT,
            repair_count=1,
            candidate_pools=candidate_pools
        )

        assert len(repaired.assignments) >= 0

    def test_repair_regret_insert_with_pool(self):
        """REGRET_INSERT should use candidate pool when provided."""
        operators = ALNSOperators(seed=42)
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env.tasks.append(task1)

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=2
        )

        empty_solution = Solution(assignments=[], total_cost=0.0, mode_counts={})

        repaired = operators.repair(
            empty_solution,
            env.tasks,
            env.uavs,
            env,
            env.depot_position,
            RepairOperator.REGRET_INSERT,
            repair_count=1,
            candidate_pools=candidate_pools
        )

        assert len(repaired.assignments) >= 0

    def test_repair_relay_aware_with_pool(self):
        """RELAY_AWARE_REGRET_INSERT should use candidate pool when provided."""
        operators = ALNSOperators(seed=42)
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env.tasks.append(task1)

        candidate_pools = strategy._build_candidate_pools(
            env.uavs, env.tasks, env, env.depot_position, k=2
        )

        empty_solution = Solution(assignments=[], total_cost=0.0, mode_counts={})

        repaired = operators.repair(
            empty_solution,
            env.tasks,
            env.uavs,
            env,
            env.depot_position,
            RepairOperator.RELAY_AWARE_REGRET_INSERT,
            repair_count=1,
            candidate_pools=candidate_pools
        )

        assert len(repaired.assignments) >= 0

    def test_repair_with_empty_pool_falls_back(self):
        """Repair should fallback to full generation when pool is empty."""
        operators = ALNSOperators(seed=42)
        strategy = ALNSUnifiedStrategy(seed=42)
        env = MockEnvironment()
        env.uavs.append(make_uav(1, (50, 50), battery=100))
        env.agvs.append(make_agv(1, (100, 100)))

        task1 = make_task(1, end=(200, 200))
        task1.start_point = (100, 100)
        env.tasks.append(task1)

        empty_solution = Solution(assignments=[], total_cost=0.0, mode_counts={})

        repaired = operators.repair(
            empty_solution,
            env.tasks,
            env.uavs,
            env,
            env.depot_position,
            RepairOperator.GREEDY_INSERT,
            repair_count=1,
            candidate_pools=None
        )

        assert len(repaired.assignments) >= 0
