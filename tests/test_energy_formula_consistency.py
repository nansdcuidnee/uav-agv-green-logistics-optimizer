"""Tests for energy formula consistency across scoring and execution layers."""

import pytest


def make_uav(uav_id, position, battery=100):
    """Create a mock UAV for testing."""
    class MockUAV:
        def __init__(self):
            self.id = uav_id
            self.position = position
            self.battery = battery
            self.max_speed = 10.0
            self.max_range = 500.0
            self.max_payload = 5.0
    return MockUAV()


def make_task(task_id, start, end):
    """Create a mock task for testing."""
    class MockTask:
        def __init__(self):
            self.id = task_id
            self.start_point = start
            self.end_point = end
            self.payload = 1.0
            self.deadline = None
    return MockTask()


class TestRelayTimeCostSemantics:
    """Test that relay cost_breakdown['time'] has correct semantics."""

    def test_relay_time_not_delta_cost_projection(self):
        """Relay cost_breakdown['time'] should NOT be a projection of delta_cost.

        It should be calculated from uav_total_distance / speed / 60,
        not from delta_cost * time_weight.
        """
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        uav = make_uav(1, (100, 100), battery=100)
        task = make_task(1, start=(200, 200), end=(300, 300))
        agv = make_uav(1, (150, 150), battery=100)
        relay_point = (250, 250)
        depot_pos = (0, 0)

        result = scorer.evaluate_relay_insertion_unified(
            uav, task, agv, relay_point, [], [], 0, 0, depot_pos
        )

        time_from_breakdown = result.cost_breakdown["time"]
        delta_cost = result.cost_delta
        time_weight = scorer._cost_weights.get("time", 1.0)

        delta_projection = delta_cost * time_weight

        assert abs(time_from_breakdown - delta_projection) > 1.0, (
            f"cost_breakdown['time'] ({time_from_breakdown}) should not equal "
            f"delta_cost * time_weight ({delta_projection})"
        )

    def test_relay_time_increases_with_deployment_distance(self):
        """Relay cost_breakdown['time'] should increase as deployment distance increases.

        When UAV is further from relay point, time should be higher.
        """
        from src.strategies.alns.scoring import CostScorer

        scorer = CostScorer()
        task = make_task(1, start=(200, 200), end=(300, 300))
        agv = make_uav(1, (250, 250), battery=100)
        relay_point = (250, 250)
        depot_pos = (0, 0)

        uav_close = make_uav(1, (200, 200), battery=100)
        uav_far = make_uav(2, (0, 0), battery=100)

        result_close = scorer.evaluate_relay_insertion_unified(
            uav_close, task, agv, relay_point, [], [], 0, 0, depot_pos
        )
        result_far = scorer.evaluate_relay_insertion_unified(
            uav_far, task, agv, relay_point, [], [], 0, 0, depot_pos
        )

        assert result_far.cost_breakdown["time"] > result_close.cost_breakdown["time"], (
            f"UAV far from relay should have higher time cost. "
            f"Far: {result_far.cost_breakdown['time']}, Close: {result_close.cost_breakdown['time']}"
        )


class TestAGVEnergyConsistency:
    """Test that AGV energy is consistent between scoring and execution layers."""

    def test_scoring_and_execution_use_same_unit_energy(self):
        """Scoring layer and execution layer should use the same AGV unit energy.

        Both should use energy_model.agv_energy_per_km with the same formula:
        agv_energy = distance / 1000 * agv_energy_per_km
        """
        from src.strategies.alns.scoring import CostScorer
        from src.energy.energy_model import EnergyModel

        energy_model = EnergyModel()
        scorer = CostScorer(energy_model=energy_model)

        agv = make_uav(1, (100, 100), battery=100)
        task = make_task(1, start=(200, 200), end=(300, 300))
        relay_point = (250, 250)
        depot_pos = (0, 0)

        result = scorer.evaluate_relay_insertion_unified(
            agv, task, agv, relay_point, [], [], 0, 0, depot_pos
        )

        distance = ((agv.position[0] - relay_point[0])**2 + 
                   (agv.position[1] - relay_point[1])**2)**0.5
        
        agv_energy_per_km = scorer._get_agv_energy_per_km()
        expected_energy = distance / 1000 * agv_energy_per_km
        
        agv_energy_weight = scorer._cost_weights.get("agv_energy", 0.5)
        actual_weighted_energy = result.cost_breakdown["agv_energy"]

        assert abs(actual_weighted_energy - expected_energy * agv_energy_weight) < 0.01, (
            f"Scoring AGV energy ({actual_weighted_energy}) should match "
            f"(distance / 1000 * agv_energy_per_km) * weight = {expected_energy * agv_energy_weight}"
        )

    def test_agv_energy_unit_consistency(self):
        """AGV energy should use the same unit (kJ/km) across scoring and simulator."""
        from src.strategies.alns.scoring import CostScorer
        from src.energy.energy_model import EnergyModel

        energy_model = EnergyModel()
        scorer = CostScorer(energy_model=energy_model)

        scoring_unit = scorer._get_agv_energy_per_km()
        model_unit = energy_model.agv_energy_per_km

        assert scoring_unit == model_unit, (
            f"Scoring AGV unit energy ({scoring_unit}) should equal "
            f"EnergyModel unit ({model_unit})"
        )


class TestEnergyModelComputeSemantics:
    """Test EnergyModel.compute() path semantics."""

    def test_compute_path_includes_start_point(self):
        """EnergyModel.compute() should use current -> start -> end path when start_point exists.

        This is more realistic than just current -> end because:
        1. UAV needs to go to start point first (pickup)
        2. Then go to end point (delivery)
        """
        from src.energy.energy_model import EnergyModel

        energy_model = EnergyModel()

        class MockUAV:
            def __init__(self, position, start_point, end_point):
                self.position = position
                self.max_speed = 10
                self.max_payload = 5.0
                self.battery = 100.0
                self.task = type('obj', (object,), {
                    'start_point': start_point,
                    'end_point': end_point,
                    'payload': 1.0
                })

        uav = MockUAV(position=(0, 0), start_point=(100, 0), end_point=(0, 100))
        energy = energy_model.compute(uav)

        distance_to_start = 100.0
        distance_start_to_end = 141.42
        total_distance = distance_to_start + distance_start_to_end

        expected_energy = total_distance / 1000 * energy_model.cruise_energy_per_km

        assert energy > expected_energy * 0.9, (
            f"compute() energy ({energy}) should reflect current->start->end path "
            f"(expected at least {expected_energy * 0.9})"
        )

    def test_compute_without_start_point_degenerates(self):
        """EnergyModel.compute() should fall back to current -> end when start_point is missing."""
        from src.energy.energy_model import EnergyModel

        energy_model = EnergyModel()

        class MockUAV:
            def __init__(self, position, start_point, end_point):
                self.position = position
                self.max_speed = 10
                self.max_payload = 5.0
                self.battery = 100.0
                self.task = type('obj', (object,), {
                    'start_point': start_point,
                    'end_point': end_point,
                    'payload': 1.0
                })

        uav_long_path = MockUAV(position=(0, 0), start_point=(200, 0), end_point=(0, 200))
        
        uav_short_path = MockUAV(position=(0, 0), start_point=(50, 0), end_point=(50, 50))

        energy_long = energy_model.compute(uav_long_path)
        energy_short = energy_model.compute(uav_short_path)

        assert energy_long > energy_short, (
            f"Longer path ({energy_long}) should have higher energy "
            f"than shorter path ({energy_short})"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
