"""Tests for ALNS unified cost scoring.

Pickup-delivery model:
- Direct: UAV origin -> start -> end -> origin
- Relay: AGV -> relay_point, UAV relay -> start -> end -> relay
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


def make_task(task_id=1, start=(0, 0), end=(300, 300)):
    return Task(
        id=task_id,
        start_point=start,
        end_point=end,
        payload=1.0,
        priority=1
    )


def make_agv(agv_id=1, position=(80, 80)):
    agv = AGV(agv_id, position)
    agv.max_speed = 5
    return agv


class TestPickupDeliverySemantic:
    """Test that scoring follows pickup-delivery model exactly."""

    def test_direct_includes_start_point(self):
        """Direct mode MUST include start_point in path: origin -> start -> end -> origin.

        This test will FAIL if start_point is removed from the path.
        """
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, start=(100, 0), end=(200, 0))
        depot_pos = (0, 0)

        option = scorer.evaluate(uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos)

        dist_origin_to_start = math.sqrt((0-100)**2 + (0-0)**2)
        dist_start_to_end = math.sqrt((100-200)**2 + (0-0)**2)
        dist_end_to_origin = math.sqrt((200-0)**2 + (0-0)**2)
        expected_total = dist_origin_to_start + dist_start_to_end + dist_end_to_origin

        time_cost = option.cost_breakdown["time"]
        expected_time = expected_total / 10 / 60

        assert abs(time_cost - expected_time) < 0.01, (
            f"Direct mode must include start_point in path. "
            f"Expected time={expected_time}, got {time_cost}"
        )

    def test_direct_start_point_affects_cost(self):
        """Different start_point should result in different cost.

        This test will FAIL if start_point is ignored in calculation.
        Using 2D coordinates to ensure start_point affects path length.
        """
        scorer = CostScorer()
        depot_pos = (0, 0)

        task1 = make_task(1, start=(0, 0), end=(100, 0))
        task2 = make_task(2, start=(0, 50), end=(100, 0))

        uav1 = make_uav(1, (0, 0))
        uav2 = make_uav(2, (0, 0))

        opt1 = scorer.evaluate(uav1, task1, DeliveryMode.DIRECT, depot_pos=depot_pos)
        opt2 = scorer.evaluate(uav2, task2, DeliveryMode.DIRECT, depot_pos=depot_pos)

        assert opt1.cost != opt2.cost, (
            f"Different start_point should produce different cost. "
            f"Got task1 cost={opt1.cost}, task2 cost={opt2.cost}. "
            f"This fails if start_point is ignored."
        )

    def test_relay_includes_start_point(self):
        """Relay mode MUST include start_point in UAV path.

        New semantics: uav_current -> relay -> start -> end -> relay
        
        This test will FAIL if start_point is removed from relay path.
        """
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, start=(100, 0), end=(200, 0))
        relay_point = (50, 0)
        agv = make_agv(1, (50, 0))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.RELAY_FIXED,
            relay_point=relay_point, agv=agv, depot_pos=depot_pos
        )

        dist_uav_to_relay = math.sqrt((0-50)**2 + (0-0)**2)
        dist_relay_to_start = math.sqrt((50-100)**2 + (0-0)**2)
        dist_start_to_end = math.sqrt((100-200)**2 + (0-0)**2)
        dist_end_to_relay = math.sqrt((200-50)**2 + (0-0)**2)
        expected_total = dist_uav_to_relay + dist_relay_to_start + dist_start_to_end + dist_end_to_relay

        time_cost = option.cost_breakdown["time"]
        expected_time = expected_total / 10 / 60

        assert abs(time_cost - expected_time) < 0.01, (
            f"Relay mode must include start_point in UAV path. "
            f"Expected time={expected_time}, got {time_cost}"
        )

    def test_relay_does_not_include_depot_in_uav_path(self):
        """Relay mode UAV should NOT return to depot, only to relay_point.

        New semantics: uav_current -> relay -> start -> end -> relay (not depot)
        """
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, start=(100, 0), end=(200, 0))
        relay_point = (50, 0)
        agv = make_agv(1, (50, 0))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.RELAY_FIXED,
            relay_point=relay_point, agv=agv, depot_pos=depot_pos
        )

        dist_uav_to_relay = math.sqrt((0-50)**2 + (0-0)**2)
        dist_relay_to_start = math.sqrt((50-100)**2 + (0-0)**2)
        dist_start_to_end = math.sqrt((100-200)**2 + (0-0)**2)
        dist_end_to_relay = math.sqrt((200-50)**2 + (0-0)**2)
        expected_total = dist_uav_to_relay + dist_relay_to_start + dist_start_to_end + dist_end_to_relay

        time_cost = option.cost_breakdown["time"]
        expected_time = expected_total / 10 / 60

        assert abs(time_cost - expected_time) < 0.01, (
            f"Relay mode UAV should return to relay, not depot. "
            f"Expected time={expected_time}, got {time_cost}"
        )

    def test_relay_agv_energy_only_includes_agv_to_relay(self):
        """AGV energy should only be distance from AGV position to relay_point."""
        scorer = CostScorer(energy_model=EnergyModel())
        uav = make_uav(1, (0, 0))
        task = make_task(1, start=(100, 0), end=(200, 0))
        relay_point = (50, 0)
        agv = make_agv(1, (0, 0))
        depot_pos = (100, 100)

        option = scorer.evaluate(
            uav, task, DeliveryMode.RELAY_FIXED,
            relay_point=relay_point, agv=agv, depot_pos=depot_pos
        )

        dist_agv_to_relay = 50.0
        expected_agv_energy = dist_agv_to_relay / 1000 * 3.0

        assert abs(option.cost_breakdown["agv_energy"] - expected_agv_energy) < 0.01, (
            f"AGV energy should only be agv->relay distance. "
            f"Expected={expected_agv_energy}, got {option.cost_breakdown['agv_energy']}"
        )


class TestTimeCost:
    """Test time cost calculation with pickup-delivery model."""

    def test_direct_time_cost(self):
        """Direct mode time cost should reflect origin->start->end->origin."""
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, start=(100, 0), end=(200, 0))
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
        task = make_task(1, start=(100, 0), end=(200, 0))
        relay_point = (50, 0)
        agv = make_agv(1, (50, 0))
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
        task = make_task(1, start=(100, 100), end=(300, 300))
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
        task1 = make_task(1, start=(100, 100), end=(200, 200))

        uav2 = make_uav(2, (50, 50))
        task2 = make_task(2, start=(100, 100), end=(500, 500))

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
        task = make_task(1, start=(100, 0), end=(200, 0))
        relay_point = (100, 0)
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
        task = make_task(1, start=(100, 0), end=(200, 0))
        relay_point = (100, 0)
        agv = make_agv(1, (50, 0))
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
        task = make_task(1, start=(100, 100), end=(200, 200))
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
        task = make_task(1, start=(100, 100), end=(200, 200))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        assert option.cost_breakdown["wait_penalty"] == 0

    def test_relay_has_wait_penalty(self):
        """Relay mode should have wait penalty."""
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, start=(100, 0), end=(200, 0))
        relay_point = (100, 0)
        agv = make_agv(1, (50, 0))
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
        task = make_task(1, start=(100, 100), end=(200, 200))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        assert option.cost_breakdown["fallback_risk"] == 0.1

    def test_relay_higher_fallback_risk(self):
        """Relay mode should have higher fallback risk."""
        scorer = CostScorer()
        uav = make_uav(1, (0, 0))
        task = make_task(1, start=(100, 0), end=(200, 0))
        relay_point = (100, 0)
        agv = make_agv(1, (50, 0))
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
        task = make_task(1, start=(100, 100), end=(200, 200))
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
        task = make_task(1, start=(100, 100), end=(200, 200))
        depot_pos = (0, 0)

        option = scorer.evaluate(
            uav, task, DeliveryMode.DIRECT, depot_pos=depot_pos
        )

        expected_keys = {
            "time", "uav_energy", "agv_energy", "carbon",
            "wait_penalty", "timeout_penalty", "fallback_risk"
        }
        assert set(option.cost_breakdown.keys()) == expected_keys


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


class TestUnifiedEvaluator:
    """Test unified evaluation result structure."""

    def test_direct_evaluation_result_has_all_fields(self):
        """Direct unified evaluation should return all fields."""
        from src.strategies.alns.scoring import CostScorer, EvaluationResult

        scorer = CostScorer()
        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(200, 200))
        depot_pos = (0, 0)

        result = scorer.evaluate_direct_insertion_unified(
            uav, task, [], 0, depot_pos
        )

        assert isinstance(result, EvaluationResult)
        assert "cost_delta" in result.to_dict()
        assert "feasibility" in result.to_dict()
        assert "predicted_wait" in result.to_dict()
        assert "predicted_slack" in result.to_dict()
        assert "mode_risk" in result.to_dict()
        assert result.option is not None

    def test_relay_evaluation_result_has_all_fields(self):
        """Relay unified evaluation should return all fields."""
        from src.strategies.alns.scoring import CostScorer, EvaluationResult

        scorer = CostScorer()
        uav = make_uav(1, (50, 50), battery=100)
        agv = make_agv(1, (100, 100))
        task = make_task(1, start=(150, 150), end=(200, 200))
        depot_pos = (0, 0)
        relay_point = (100, 100)

        result = scorer.evaluate_relay_insertion_unified(
            uav, task, agv, relay_point, [], [], 0, 0, depot_pos
        )

        assert isinstance(result, EvaluationResult)
        assert "cost_delta" in result.to_dict()
        assert "feasibility" in result.to_dict()
        assert "predicted_wait" in result.to_dict()
        assert "predicted_slack" in result.to_dict()
        assert "mode_risk" in result.to_dict()
        assert result.option is not None

    def test_direct_feasibility_check(self):
        """Direct feasibility should check energy/range."""
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        depot_pos = (0, 0)
        task = make_task(1, start=(10, 10), end=(15, 15))

        uav_high = make_uav(1, depot_pos, battery=100)
        result_high = scorer.evaluate_direct_insertion_unified(
            uav_high, task, [], 0, depot_pos
        )
        assert result_high.feasibility is True

        uav_low = make_uav(2, depot_pos, battery=1)
        result_low = scorer.evaluate_direct_insertion_unified(
            uav_low, task, [], 0, depot_pos
        )
        assert result_low.feasibility is False

    def test_relay_feasibility_check(self):
        """Relay feasibility should check UAV range."""
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        depot_pos = (0, 0)
        agv = make_agv(1, (100, 100))
        task = make_task(1, start=(150, 150), end=(200, 200))
        relay_point = (100, 100)

        uav_high = make_uav(1, (50, 50), battery=100)
        result_high = scorer.evaluate_relay_insertion_unified(
            uav_high, task, agv, relay_point, [], [], 0, 0, depot_pos
        )
        assert result_high.feasibility is True

        uav_low = make_uav(2, (50, 50), battery=1)
        result_low = scorer.evaluate_relay_insertion_unified(
            uav_low, task, agv, relay_point, [], [], 0, 0, depot_pos
        )
        assert result_low.feasibility is False

    def test_direct_predicted_wait_is_zero(self):
        """Direct mode should have predicted_wait = 0.0."""
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(200, 200))
        depot_pos = (0, 0)

        result = scorer.evaluate_direct_insertion_unified(
            uav, task, [], 0, depot_pos
        )

        assert result.predicted_wait == 0.0

    def test_relay_predicted_wait_is_positive(self):
        """Relay mode should have predicted_wait > 0.0."""
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        uav = make_uav(1, (50, 50), battery=100)
        agv = make_agv(1, (0, 0))
        task = make_task(1, start=(150, 150), end=(200, 200))
        depot_pos = (0, 0)
        relay_point = (100, 100)

        result = scorer.evaluate_relay_insertion_unified(
            uav, task, agv, relay_point, [], [], 0, 0, depot_pos
        )

        assert result.predicted_wait > 0.0

    def test_mode_risk_direct_lower_than_relay(self):
        """Direct mode should have lower fallback risk than relay mode.

        New semantics: mode_risk is dynamically computed based on energy margin,
        slack, and sync deviation. Relay mode has higher risk due to:
        - energy_margin_penalty (UAV must fly to relay first)
        - sync_penalty (UAV/AGV must arrive at relay simultaneously)
        """
        scorer = CostScorer()
        uav = make_uav(1, (50, 50), battery=100)
        agv = make_agv(1, (100, 100))
        task = make_task(1, start=(150, 150), end=(200, 200))
        depot_pos = (0, 0)
        relay_point = (100, 100)

        direct_result = scorer.evaluate_direct_insertion_unified(
            uav, task, [], 0, depot_pos
        )
        relay_result = scorer.evaluate_relay_insertion_unified(
            uav, task, agv, relay_point, [], [], 0, 0, depot_pos
        )

        assert direct_result.mode_risk < relay_result.mode_risk
        assert 0 <= direct_result.mode_risk <= 1.0
        assert 0 <= relay_result.mode_risk <= 1.0

    def test_cost_breakdown_in_result(self):
        """EvaluationResult should include cost_breakdown."""
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(100, 100), end=(200, 200))
        depot_pos = (0, 0)

        result = scorer.evaluate_direct_insertion_unified(
            uav, task, [], 0, depot_pos
        )

        assert "uav_energy" in result.cost_breakdown
        assert "agv_energy" in result.cost_breakdown
        assert "carbon" in result.cost_breakdown


class TestDirectSemanticConsistency:
    """Test that direct mode semantics are consistent between unified and delta evaluators."""

    def test_empty_route_unified_delta_start_consistent(self):
        """When uav_route is empty, unified feasibility and delta cost must use same starting point.

        This verifies that both evaluate_direct_insertion_unified() and
        evaluate_direct_insertion_delta() use uav.position as starting point,
        not depot_pos.
        """
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        uav = make_uav(1, (100, 100), battery=100)
        task = make_task(1, start=(200, 200), end=(300, 300))
        depot_pos = (0, 0)

        unified_result = scorer.evaluate_direct_insertion_unified(
            uav, task, [], 0, depot_pos
        )

        delta_cost, _ = scorer.evaluate_direct_insertion_delta(
            uav, task, [], 0, depot_pos
        )

        assert unified_result.cost_delta == delta_cost, (
            f"Unified cost_delta ({unified_result.cost_delta}) should equal delta cost ({delta_cost})"
        )

    def test_uav_position_changes_affect_both_feasibility_and_cost(self):
        """When UAV position changes, both feasibility and cost should change in same direction.

        If UAV moves closer to task, both feasibility should improve (or stay same)
        and cost should decrease.
        """
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        task = make_task(1, start=(200, 200), end=(300, 300))
        depot_pos = (0, 0)

        uav_far = make_uav(1, (0, 0), battery=50)
        uav_close = make_uav(2, (150, 150), battery=50)

        result_far = scorer.evaluate_direct_insertion_unified(
            uav_far, task, [], 0, depot_pos
        )
        result_close = scorer.evaluate_direct_insertion_unified(
            uav_close, task, [], 0, depot_pos
        )

        assert result_close.cost_delta < result_far.cost_delta, (
            f"UAV closer to task should have lower cost. "
            f"Close: {result_close.cost_delta}, Far: {result_far.cost_delta}"
        )

    def test_non_empty_route_respects_route_context(self):
        """When uav_route is not empty, delta should respect route context for prev/next positions.

        This ensures that insertion semantics are correct: inserting between
        existing route stops should use those stops as prev/next positions.
        """
        from src.strategies.alns.scoring import CostScorer
        from src.strategies.alns.solution import RouteStop
        from src.strategies.alns import DeliveryMode

        scorer = CostScorer()
        uav = make_uav(1, (50, 50), battery=100)
        task = make_task(1, start=(150, 150), end=(200, 200))
        depot_pos = (0, 0)

        uav_route = [
            RouteStop(task_id=None, mode=DeliveryMode.DIRECT, uav_id=1, position=(100, 100)),
            RouteStop(task_id=None, mode=DeliveryMode.DIRECT, uav_id=1, position=(250, 250))
        ]

        delta_cost_middle, _ = scorer.evaluate_direct_insertion_delta(
            uav, task, uav_route, 1, depot_pos
        )

        delta_cost_start, _ = scorer.evaluate_direct_insertion_delta(
            uav, task, [], 0, depot_pos
        )

        assert delta_cost_middle != delta_cost_start, (
            f"Inserting into non-empty route ({delta_cost_middle}) should have different cost "
            f"than inserting into empty route ({delta_cost_start})"
        )

    def test_feasibility_based_on_uav_position_not_depot(self):
        """Direct feasibility check must be based on uav.position, not depot_pos.

        This test verifies that a UAV that is close to the task (feasible from
        current position) but far from depot (infeasible from depot) is correctly
        marked as feasible.
        """
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        task = make_task(1, start=(195, 195), end=(205, 205))
        depot_pos = (0, 0)

        uav_close_to_task = make_uav(1, (190, 190), battery=100)
        uav_close_to_task.max_range = 50

        result = scorer.evaluate_direct_insertion_unified(
            uav_close_to_task, task, [], 0, depot_pos
        )

        assert result.feasibility is True, (
            f"UAV at (190,190) with range 50 should be feasible to task at (195,195)-(205,205). "
            f"Required range from uav.position: ~30, from depot: ~424"
        )

    def test_cost_breakdown_time_and_energy_consistent(self):
        """cost_breakdown time and uav_energy should be based on same position semantics.

        Both time and uav_energy should use required_range calculated from uav.position,
        not from depot_pos or delta_distance.
        """
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        uav = make_uav(1, (100, 100), battery=100)
        task = make_task(1, start=(200, 200), end=(300, 300))
        depot_pos = (0, 0)

        result = scorer.evaluate_direct_insertion_unified(
            uav, task, [], 0, depot_pos
        )

        required_range = (
            scorer._distance(uav.position, task.start_point) +
            scorer._distance(task.start_point, task.end_point) +
            scorer._distance(task.end_point, uav.position)
        )

        expected_time = required_range / uav.max_speed / 60
        expected_energy = required_range / 1000 * 5.0

        actual_time = result.cost_breakdown["time"] / scorer._cost_weights.get("time", 1.0)
        actual_energy = result.cost_breakdown["uav_energy"] / scorer._cost_weights.get("uav_energy", 0.8)

        assert abs(actual_time - expected_time) < 0.01, (
            f"time should be based on required_range from uav.position. "
            f"Expected: {expected_time}, Actual: {actual_time}"
        )
        assert abs(actual_energy - expected_energy) < 0.01, (
            f"uav_energy should be based on required_range from uav.position. "
            f"Expected: {expected_energy}, Actual: {actual_energy}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
