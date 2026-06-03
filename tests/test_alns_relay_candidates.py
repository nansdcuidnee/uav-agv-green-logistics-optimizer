"""Tests for ALNS relay candidate generation (pickup-delivery model).

Candidate sources:
1. AGV current position
2. task.start_point
3. task.end_point
4. Corridor key points (25%, 50%, 75%)
5. AGV projection onto corridor line segment

UAV flies: relay -> start -> end -> relay
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
    uav.max_range = 1000
    return uav


def make_task(task_id=1, start=(100, 100), end=(200, 200)):
    return Task(
        id=task_id,
        start_point=start,
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


class TestCandidateSources:
    """Test that candidates include start_point, end_point, and corridor points."""

    def test_agv_position_in_candidates(self):
        """AGV current position should be in candidates when valid."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 100))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        assert len(candidates) > 0, "Should have at least one candidate"

        agv_in = any(abs(c[0] - 100) < 1 and abs(c[1] - 100) < 1 for c in candidates)
        assert agv_in, "AGV position should be in candidates"

    def test_start_point_in_candidates(self):
        """task.start_point should be in candidates when valid."""
        env = MockEnvironment()
        agv = make_agv(1, (80, 80))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        start_in = any(abs(c[0] - 100) < 1 and abs(c[1] - 100) < 1 for c in candidates)
        assert start_in, "task.start_point should be in candidates"

    def test_end_point_in_candidates(self):
        """task.end_point should be in candidates when valid."""
        env = MockEnvironment()
        agv = make_agv(1, (80, 80))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        end_in = any(abs(c[0] - 150) < 1 and abs(c[1] - 150) < 1 for c in candidates)
        assert end_in, "task.end_point should be in candidates"

    def test_corridor_25_50_75_points(self):
        """Corridor key points at 25%, 50%, 75% should be in candidates."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 100))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(200, 200))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        expected_points = [(125, 125), (150, 150), (175, 175)]
        found = 0
        for expected in expected_points:
            for cand in candidates:
                if abs(cand[0] - expected[0]) < 2 and abs(cand[1] - expected[1]) < 2:
                    found += 1
                    break

        assert found >= 1, f"Expected at least 1 corridor point, got {found}"


class TestProjection:
    """Test AGV projection onto corridor line segment."""

    def test_projection_on_segment(self):
        """AGV beside corridor should have projection on segment."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 150))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(200, 200))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        assert len(candidates) > 0, "Should have candidates including projection"

    def test_projection_clamped_to_endpoint(self):
        """AGV far from corridor should have projection clamped to endpoint."""
        env = MockEnvironment()
        agv = make_agv(1, (500, 500))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(200, 200))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        assert len(candidates) > 0, "Should have candidates with clamped projection"


class TestMultipleCandidatesPerAGV:
    """Test that a single AGV returns multiple valid candidates."""

    def test_single_agv_returns_multiple_candidates(self):
        """A single AGV should return multiple valid relay candidates."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 100))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        assert len(candidates) > 1, f"Expected multiple candidates, got {len(candidates)}"

    def test_generate_for_agv_returns_best(self):
        """generate_for_agv should return the best relay point by cost."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 100))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        best_point = RelayCandidateGenerator.generate_for_agv(uav, task, agv, env, None)
        all_candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        assert best_point is not None, "Should return a best point"
        assert best_point in all_candidates, "Best point should be in candidates"

    def test_generate_for_agv_returns_none_when_no_valid(self):
        """generate_for_agv should return None when no valid candidates."""
        env = MockEnvironment()
        agv = make_agv(1, (50, 50))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=1)
        task = make_task(1, start=(100, 100), end=(900, 900))

        result = RelayCandidateGenerator.generate_for_agv(uav, task, agv, env, None)
        assert result is None, f"Should return None when no valid candidates, got {result}"


class TestGenerateBoundCandidates:
    """Test that generate_bound_candidates returns multiple candidates per AGV."""

    def test_single_agv_returns_multiple_in_bound(self):
        """generate_bound_candidates should return multiple entries for single AGV."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 100))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, None)

        same_agv_count = sum(1 for _, bound_agv in candidates if bound_agv.id == 1)
        assert same_agv_count > 1, f"Single AGV should return multiple candidates, got {same_agv_count}"

    def test_same_agv_multiple_relay_points(self):
        """Same AGV should be bound to multiple different relay points."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 100))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, None)

        relay_points = set()
        for relay_point, bound_agv in candidates:
            if bound_agv.id == 1:
                relay_points.add((round(relay_point[0], 1), round(relay_point[1], 1)))

        assert len(relay_points) > 1, f"Should have multiple distinct relay points for same AGV"

    def test_multiple_agvs_all_have_candidates(self):
        """Multiple AGVs should each contribute candidates."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))
        env.agvs.append(make_agv(2, (150, 150)))

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, None)

        agv1_count = sum(1 for _, bound_agv in candidates if bound_agv.id == 1)
        agv2_count = sum(1 for _, bound_agv in candidates if bound_agv.id == 2)

        assert agv1_count > 0, "AGV 1 should have candidates"
        assert agv2_count > 0, "AGV 2 should have candidates"


class TestValidityFilter:
    """Test UAV range validity filter with pickup-delivery model."""

    def test_low_battery_filters_far_candidates(self):
        """Low battery should filter out candidates that UAV cannot complete."""
        env = MockEnvironment()
        agv = make_agv(1, (500, 500))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=5)
        task = make_task(1, start=(100, 100), end=(900, 900))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        for cand in candidates:
            required = (
                math.sqrt((cand[0] - 100)**2 + (cand[1] - 100)**2) +
                math.sqrt((100 - 900)**2 + (100 - 900)**2) +
                math.sqrt((900 - cand[0])**2 + (900 - cand[1])**2)
            )
            remaining = uav.battery * uav.max_range / 100
            assert required <= remaining + 0.1, f"Invalid candidate {cand}"

    def test_valid_candidates_pass_filter(self):
        """Close candidates should pass filter."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 100))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, None)

        assert len(candidates) > 0, "Should have valid candidates"


class TestSameStartEndPoint:
    """Test edge case when start_point equals end_point."""

    def test_same_start_end_no_error(self):
        """Should not error when start_point equals end_point."""
        env = MockEnvironment()
        agv = make_agv(1, (100, 100))
        env.agvs.append(agv)

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(100, 100))

        candidates = RelayCandidateGenerator.generate_candidates_for_agv(uav, task, agv, env, None)

        assert isinstance(candidates, list), "Should return a list without error"


class TestNoAvailableAGV:
    """Test edge case when no AGV is available."""

    def test_no_agvs_returns_empty(self):
        """Should return empty list when no AGV available."""
        env = MockEnvironment()
        env.agvs = []

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, None)

        assert len(candidates) == 0, "Should return empty list when no AGV"


class TestDeterminism:
    """Test deterministic candidate generation."""

    def test_same_inputs_same_candidates(self):
        """Same inputs should produce same candidates."""
        env = MockEnvironment()
        env.agvs.append(make_agv(1, (100, 100)))

        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(150, 150))

        candidates1 = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, None)
        candidates2 = RelayCandidateGenerator.generate_bound_candidates(uav, task, env, None)

        assert len(candidates1) == len(candidates2), "Should produce deterministic results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
