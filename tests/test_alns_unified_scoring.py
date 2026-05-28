"""Tests for ALNS unified cost scoring.

Single depot assumption:
- Direct mode: depot -> end_point -> depot (no task.start_point in path)
- Relay mode: AGV -> relay_point, relay_point -> end_point -> depot
"""

import pytest
import math
from src.strategies.alns import DeliveryMode, DeliveryOption, CostScorer
from src.core.uav import UAV
from src.core.agv import AGV
from src.core.task import Task
from src.energy.energy_model import EnergyModel


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


class TestTimeCost:
    """Test time cost calculation with single depot model."""

    def test_direct_time_cost(self):
        """Direct mode time cost should reflect depot->end->depot distance."""
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, end=(100, 0))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        assert "time" in option.cost_breakdown
        time_cost = option.cost_breakdown["time"]
        assert time_cost > 0

    def test_relay_time_cost(self):
        """Relay mode time cost should be calculated."""
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, end=(200, 200))
        relay_point = (100, 100)
        agv = make_agv(1, (50, 50))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.RELAY_FIXED,
            relay_point=relay_point, agv=agv, depot_pos=depot_pos
        )

        assert "time" in option.cost_breakdown
        assert option.cost_breakdown["time"] > 0


class TestUAVEnergyCost:
    """Test UAV energy cost calculation."""

    def test_uav_energy_positive(self):
        """UAV energy cost should be positive."""
        scorer = CostScorer(energy_model=EnergyModel())
        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(300, 300))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        assert "uav_energy" in option.cost_breakdown
        assert option.cost_breakdown["uav_energy"] >= 0

    def test_longer_distance_more_energy(self):
        """Longer distance should cost more energy."""
        scorer = CostScorer(energy_model=EnergyModel())

        depot_pos = (0, 0)

        uav1 = make_uav(1, (50, 50))
        task1 = make_task(1, end=(200, 200))

        uav2 = make_uav(2, (50, 50))
        task2 = make_task(2, end=(500, 500))

        option1 = scorer.evaluate(
            uav1, task1, DeliveryMode.DIRECT, depot_pos=depot_pos
        )
        option2 = scorer.evaluate(
            uav2, task2, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        assert option2.cost_breakdown["uav_energy"] >= option1.cost_breakdown["uav_energy"]


class TestAGVEnergyCost:
    """Test AGV energy cost calculation."""

    def test_agv_energy_zero_without_agv(self):
        """AGV energy should be zero when no AGV assigned."""
        scorer = CostScorer(energy_model=EnergyModel())
        uav = make_uav(1, (0, 0))
        task = make_task(1, end=(200, 200))
        relay_point = (100, 100)
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.RELAY_FIXED,
            relay_point=relay_point, agv=None, depot_pos=depot_pos
        )

        assert option.cost_breakdown["agv_energy"] == 0

    def test_agv_energy_with_agv(self):
        """AGV energy should be positive when AGV assigned."""
        scorer = CostScorer(energy_model=EnergyModel())
        uav = make_uav(1, (0, 0))
        task = make_task(1, end=(200, 200))
        relay_point = (100, 100)
        agv = make_agv(1, (50, 50))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.RELAY_FIXED,
            relay_point=relay_point, agv=agv, depot_pos=depot_pos
        )

        assert option.cost_breakdown["agv_energy"] > 0


class TestCarbonCost:
    """Test carbon emission cost calculation."""

    def test_carbon_based_on_energy(self):
        """Carbon should be 0.5 * total energy."""
        scorer = CostScorer(energy_model=EnergyModel())
        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        carbon = option.cost_breakdown["carbon"]
        uav_energy = option.cost_breakdown["uav_energy"]
        agv_energy = option.cost_breakdown["agv_energy"]

        expected_carbon = (uav_energy + agv_energy) * 0.5
        assert abs(carbon - expected_carbon) < 0.001


class TestWaitPenalty:
    """Test wait penalty calculation."""

    def test_direct_no_wait_penalty(self):
        """Direct mode should have no wait penalty."""
        scorer = CostScorer()
        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        assert option.cost_breakdown["wait_penalty"] == 0

    def test_relay_has_wait_penalty(self):
        """Relay mode should have wait penalty."""
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, end=(200, 200))
        relay_point = (100, 100)
        agv = make_agv(1, (50, 50))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.RELAY_FIXED,
            relay_point=relay_point, agv=agv, depot_pos=depot_pos
        )

        assert option.cost_breakdown["wait_penalty"] > 0


class TestFallbackRisk:
    """Test fallback risk penalty."""

    def test_direct_low_fallback_risk(self):
        """Direct mode should have low fallback risk."""
        scorer = CostScorer()
        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        assert option.cost_breakdown["fallback_risk"] == 0.1

    def test_relay_higher_fallback_risk(self):
        """Relay mode should have higher fallback risk."""
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, end=(200, 200))
        relay_point = (100, 100)
        agv = make_agv(1, (50, 50))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.RELAY_FIXED,
            relay_point=relay_point, agv=agv, depot_pos=depot_pos
        )

        assert option.cost_breakdown["fallback_risk"] > 0.1


class TestTotalCost:
    """Test total cost aggregation."""

    def test_total_cost_sum_of_parts(self):
        """Total cost should be sum of weighted parts."""
        scorer = CostScorer()
        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        weights = scorer.get_cost_weights()
        total = sum(
            weights[key] * option.cost_breakdown[key]
            for key in option.cost_breakdown
        )

        assert abs(option.cost - total) < 0.001

    def test_cost_breakdown_has_all_keys(self):
        """Cost breakdown should have all 7 keys."""
        scorer = CostScorer()
        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(200, 200))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        expected_keys = {
            "time", "uav_energy", "agv_energy", "carbon",
            "wait_penalty", "timeout_penalty", "fallback_risk"
        }
        assert set(option.cost_breakdown.keys()) == expected_keys


class TestSingleDepotModel:
    """Test single depot model does not use task.start_point."""

    def test_direct_path_is_depot_to_end_to_depot(self):
        """Direct mode should use depot->end->depot, not task.start_point."""
        scorer = CostScorer()
        uav = make_uav(1, (50, 50))
        task = make_task(1, end=(100, 0))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        depot_to_end = math.sqrt((0-100)**2 + (0-0)**2)
        end_to_depot = math.sqrt((100-0)**2 + (0-0)**2)
        expected_distance = depot_to_end + end_to_depot

        time_cost = option.cost_breakdown["time"]
        expected_time = expected_distance / 10 / 60

        assert abs(time_cost - expected_time) < 0.01, "Should use depot->end->depot"


class TestCostWeights:
    """Test cost weight configuration."""

    def test_default_weights_exist(self):
        """Default cost weights should be defined."""
        scorer = CostScorer()
        weights = scorer.get_cost_weights()

        assert "time" in weights
        assert "uav_energy" in weights
        assert "agv_energy" in weights
        assert "carbon" in weights
        assert "wait_penalty" in weights
        assert "timeout_penalty" in weights
        assert "fallback_risk" in weights

    def test_weights_positive(self):
        """All weights should be positive."""
        scorer = CostScorer()
        weights = scorer.get_cost_weights()

        for key, value in weights.items():
            assert value >= 0, f"Weight for {key} is negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])