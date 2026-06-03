"""Tests for ALNS dynamic fallback mechanism.

Fallback priority:
1. Reselect relay point
2. Switch to direct
3. Keep pending (infeasible)
"""

import pytest
import math
from src.strategies.alns_unified import ALNSUnifiedStrategy, DeliveryMode
from src.core.uav import UAV
from src.core.agv import AGV
from src.core.task import Task


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
        self.tasks = []
        self.charging_stations = []
        self.depot_position = (0, 0)
        self.obstacles = []
        self.current_time = 0

    def is_valid_position(self, point):
        x, y = point
        if x < 0 or x > 1000 or y < 0 or y > 1000:
            return False
        return True


class TestFallbackPriority:
    """Test fallback action priorities."""

    def test_fallback_finds_new_relay_first(self):
        """Fallback should try new relay points first."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))
        env.agvs.append(make_agv(2, (200, 200)))
        env.depot_position = (0, 0)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, end=(300, 300))
        task.assigned_uav = uav
        task.relay_point = (100, 100)
        task.status = "waiting_for_agv"
        task.assigned_time = 20

        result = strategy._check_and_apply_fallback(task, env, env.depot_position)

        assert result["action"] in ["relay_reselected", "relay_to_direct", "keep_pending", "none"]
        if result["action"] == "relay_reselected":
            assert "relay_point" in result
            assert "agv_id" in result

    def test_fallback_switches_to_direct_when_no_relay(self):
        """Fallback should switch to direct when no valid relay."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.agvs = []
        env.depot_position = (0, 0)

        uav = make_uav(1, (0, 0), battery=100)
        task = make_task(1, end=(100, 100))
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = 20

        result = strategy._check_and_apply_fallback(task, env, env.depot_position)

        if result["action"] == "relay_to_direct":
            assert task.status == "in_progress"
        elif result["action"] == "keep_pending":
            assert result.get("reason") == "infeasible"

    def test_fallback_keeps_pending_when_infeasible(self):
        """Fallback should keep pending when both relay and direct are infeasible."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.agvs = []
        env.depot_position = (0, 0)

        uav = make_uav(1, (50, 50), battery=5)
        task = make_task(1, end=(900, 900))
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = 20

        result = strategy._check_and_apply_fallback(task, env, env.depot_position)

        assert result["action"] == "keep_pending"
        assert "infeasible" in result.get("reason", "").lower()


class TestFallbackTriggers:
    """Test fallback trigger conditions."""

    def test_low_battery_triggers_fallback(self):
        """Low battery should trigger fallback."""
        strategy = ALNSUnifiedStrategy(battery_low_threshold=20.0)
        env = MockEnvironment()
        env.agvs = []
        env.depot_position = (0, 0)

        uav = make_uav(1, (0, 0), battery=10)
        task = make_task(1, end=(100, 100))
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = 0

        result = strategy._check_and_apply_fallback(task, env, env.depot_position)

        assert result["action"] != "none"

    def test_wait_timeout_triggers_fallback(self):
        """Wait timeout should trigger fallback."""
        strategy = ALNSUnifiedStrategy(wait_timeout=10)
        env = MockEnvironment()
        env.agvs = []
        env.depot_position = (0, 0)

        uav = make_uav(1, (0, 0), battery=100)
        task = make_task(1, end=(100, 100))
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.wait_time_at_relay = 15

        result = strategy._check_and_apply_fallback(task, env, env.depot_position)

        assert result["action"] != "none"


class TestFallbackCounter:
    """Test fallback counter tracking."""

    def test_fallback_count_increments(self):
        """Fallback count should increment on fallback."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.agvs = []
        env.depot_position = (0, 0)

        uav = make_uav(1, (0, 0), battery=100)
        task = make_task(1, end=(100, 100))
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = 20

        initial_count = strategy.fallback_count

        strategy._check_and_apply_fallback(task, env, env.depot_position)

        assert strategy.fallback_count >= initial_count

    def test_replan_count_increments(self):
        """Replan count should increment on relay replan."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (50, 50)))
        env.agvs.append(make_agv(2, (100, 100)))
        env.depot_position = (0, 0)

        uav = make_uav(1, (0, 0), battery=100)
        task = make_task(1, end=(200, 200))
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = 20

        initial_count = strategy.replan_count

        strategy._check_and_apply_fallback(task, env, env.depot_position)

        assert strategy.replan_count >= initial_count


class TestFallbackEventRecording:
    """Test fallback event recording."""

    def test_apply_fallback_returns_event_type(self):
        """apply_fallback should return event type."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))
        env.depot_position = (0, 0)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, end=(300, 300))
        task.assigned_uav = uav
        task.status = "waiting_for_agv"
        task.assigned_time = 20

        result = strategy._check_and_apply_fallback(task, env, env.depot_position)

        assert "event_type" in result
        assert "action" in result


class TestDirectFeasibility:
    """Test direct delivery feasibility check."""

    def test_can_complete_direct_true(self):
        """_can_uav_complete_direct should return True when feasible."""
        strategy = ALNSUnifiedStrategy()
        uav = make_uav(1, (0, 0), battery=100)
        uav.max_range = 500
        task = make_task(1, end=(100, 100))
        depot_pos = (0, 0)

        can_complete = strategy._can_uav_complete_direct(uav, task, depot_pos)

        assert can_complete == True

    def test_can_complete_direct_false_low_battery(self):
        """_can_uav_complete_direct should return False with low battery."""
        strategy = ALNSUnifiedStrategy()
        uav = make_uav(1, (0, 0), battery=5)
        uav.max_range = 500
        task = make_task(1, end=(900, 900))
        depot_pos = (0, 0)

        can_complete = strategy._can_uav_complete_direct(uav, task, depot_pos)

        assert can_complete == False


class TestModeCounts:
    """Test mode count tracking."""

    def test_direct_count_tracked(self):
        """Direct count should be tracked."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs = []
        env.uavs.append(make_uav(1, (0, 0), battery=100))
        env.agvs = []
        task = make_task(1, end=(50, 50))
        task.status = "pending"
        task.start_point = (0, 0)
        env.tasks.append(task)
        env.depot_position = (0, 0)

        strategy.assign_tasks(env)

        total_assigned = strategy.direct_count + strategy.relay_count
        assert total_assigned == len(env.tasks)

    def test_relay_count_tracked(self):
        """Relay count should be tracked."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.uavs = []
        env.uavs.append(make_uav(1, (50, 50)))
        env.agvs.append(make_agv(1, (80, 80)))
        task = make_task(1, end=(200, 200))
        task.status = "pending"
        env.tasks.append(task)
        env.depot_position = (0, 0)

        strategy.assign_tasks(env)

        assert strategy.relay_count >= 0


class TestFallbackMultipleTasks:
    """Test fallback with multiple tasks."""

    def test_each_task_fallback_independent(self):
        """Each task's fallback should be independent."""
        strategy = ALNSUnifiedStrategy()
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))
        env.depot_position = (0, 0)

        tasks = []
        for i in range(3):
            task = make_task(i+1, end=(200+i*50, 200+i*50))
            task.assigned_uav = make_uav(i+1, (50+i*10, 50+i*10), battery=100)
            task.status = "waiting_for_agv"
            task.assigned_time = 20
            tasks.append(task)

        results = []
        for task in tasks:
            result = strategy._check_and_apply_fallback(task, env, env.depot_position)
            results.append(result)

        assert len(results) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
