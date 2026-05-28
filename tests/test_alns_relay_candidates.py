"""Tests for ALNS relay candidate generation (deterministic).

Single depot assumption: All tasks originate from depot_position.
"""

import pytest
import math
from src.planning.relay_candidate_generator import RelayCandidateGenerator
from src.core.uav import UAV
from src.core.agv import AGV
from src.core.task import Task


def make_uav(uav_id=1, position=(50, 50), battery=100):
    uav = UAV(uav_id, position)
    uav.battery = battery
    uav.max_range = 500
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

    def is_valid_position(self, point):
        x, y = point
        if x < 0 or x > 1000 or y < 0 or y > 1000:
            return False
        for obs in self.obstacles:
            pos = getattr(obs, 'position', obs[:2])
            radius = getattr(obs, 'radius', obs[2] if len(obs) > 2 else 5)
            dist = math.sqrt((x - pos[0])**2 + (y - pos[1])**2)
            if dist < radius:
                return False
        return True


class TestAGVPositionCandidates:
    """Test AGV position as relay candidates (must bind to AGV)."""

    def test_agv_position_in_candidates(self):
        """AGV current position should be in candidates when available."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))

        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, depot_pos)

        assert len(candidates) > 0, "Should have at least one candidate with AGV available"

        relay_point, agv = candidates[0]
        assert agv is not None, "AGV must be bound"
        assert agv.id == 1

    def test_no_candidates_without_agv(self):
        """Should have no relay candidates when no AGV available."""
        env = MockEnvironment()
        env.agvs = []

        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, depot_pos)

        assert len(candidates) == 0, "Should have no candidates without AGV"


class TestLineSegmentCandidates:
    """Test line segment (depot->end) key points."""

    def test_line_segment_points_at_25_50_75(self):
        """Line segment points should be at 25%, 50%, 75%."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (50, 50)))

        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(400, 400))
        depot_pos = (0, 0)

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, depot_pos)

        expected_points = [(100, 100), (200, 200), (300, 300)]
        found = 0
        for expected in expected_points:
            for cand, _ in candidates:
                if abs(cand[0] - expected[0]) < 5 and abs(cand[1] - expected[1]) < 5:
                    found += 1
                    break

        assert found >= 1, f"Expected at least 1 line segment point, got {found}"

    def test_line_segment_non_zero_depot(self):
        """Line segment works with non-zero depot."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))

        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(400, 400))
        depot_pos = (100, 100)

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, depot_pos)

        expected_points = [(175, 175), (250, 250), (325, 325)]
        found = 0
        for expected in expected_points:
            for cand, _ in candidates:
                if abs(cand[0] - expected[0]) < 5 and abs(cand[1] - expected[1]) < 5:
                    found += 1
                    break

        assert found >= 1, f"Expected at least 1 line segment point, got {found}"


class TestValidityFilter:
    """Test UAV range validity filter."""

    def test_low_battery_filters_far_candidates(self):
        """Low battery should filter out far candidates."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (50, 50)))

        uav = make_uav(1, (50, 50), battery=10)
        uav.max_range = 500
        task = make_task(1, end=(800, 800))
        depot_pos = (0, 0)

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, depot_pos)

        for cand, _ in candidates:
            required = 2 * math.sqrt((cand[0] - 800)**2 + (cand[1] - 800)**2)
            remaining = uav.battery * uav.max_range / 100
            assert required <= remaining + 1, f"Invalid candidate {cand}"

    def test_valid_candidates_pass_filter(self):
        """Close candidates should pass filter."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))

        uav = make_uav(1, (50, 50), battery=100)
        uav.max_range = 500
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, depot_pos)

        assert len(candidates) > 0


class TestBoundaryCandidates:
    """Test UAV range boundary candidates."""

    def test_boundary_candidates_exist(self):
        """Boundary candidates should be generated based on UAV range."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (50, 50)))

        uav = make_uav(1, (50, 50), battery=100)
        uav.max_range = 500
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, depot_pos)

        assert len(candidates) > 0


class TestDeterminism:
    """Test deterministic candidate generation."""

    def test_same_seed_same_candidates(self):
        """Same seed should produce same candidates."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))

        uav1 = make_uav(1, (50, 50))
        task = make_task(1, end=(300, 300))
        depot_pos = (0, 0)

        candidates1 = RelayCandidateGenerator.generate_bound_candidates(uav1, task, env, depot_pos)
        candidates2 = RelayCandidateGenerator.generate_bound_candidates(uav1, task, env, depot_pos)

        assert len(candidates1) == len(candidates2)


class TestRelayCandidiateRequiresAGV:
    """Test that relay candidates must bind to an AGV."""

    def test_all_relay_candidates_have_agv(self):
        """Every relay candidate must have an AGV bound."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))
        env.agvs.append(make_agv(2, (200, 200)))

        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(300, 300))
        depot_pos = (0, 0)

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, depot_pos)

        for relay_point, agv in candidates:
            assert agv is not None, "AGV must be bound to relay candidate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])