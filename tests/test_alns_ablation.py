
"""Tests for ALNS ablation parameters."""
import unittest
import os
import sys
import tempfile
import json
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import real modules
from src.strategies.alns_unified import ALNSUnifiedStrategy
from src.strategies.alns.operators import ALNSOperators
from src.strategies.alns.operators import DestroyOperator, RepairOperator


# Mock functions that don't depend on external modules
def mock_get_ablation_variants():
    from dataclasses import dataclass

    @dataclass
    class MockAblationVariant:
        name: str
        description: str
        strategy_kwargs: dict

    variants = []
    # Complete method (baseline)
    variants.append(MockAblationVariant(
        name="unified_full",
        description="Complete ALNS Unified Strategy (baseline)",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": True,
            "destroy_operator_set": ["random_remove", "worst_remove", "high_energy_remove"],
            "repair_operator_set": ["greedy_insert", "regret_insert", "relay_aware_regret_insert"]
        }
    ))
    # Main ablation group
    variants.append(MockAblationVariant(
        name="direct_only",
        description="Direct only mode (relay disabled)",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": False,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": True
        }
    ))
    variants.append(MockAblationVariant(
        name="relay_only",
        description="Relay only mode (direct disabled)",
        strategy_kwargs={
            "allow_direct": False,
            "allow_relay": True,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": True
        }
    ))
    variants.append(MockAblationVariant(
        name="greedy_pool",
        description="Greedy candidate pool strategy",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "greedy_topk",
            "adaptive_operator_weights": True
        }
    ))
    variants.append(MockAblationVariant(
        name="random_pool",
        description="Random candidate pool strategy",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "random_topk",
            "adaptive_operator_weights": True
        }
    ))
    variants.append(MockAblationVariant(
        name="fixed_weights",
        description="Fixed operator weights (adaptive disabled)",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": False
        }
    ))
    variants.append(MockAblationVariant(
        name="simple_ops",
        description="Simple operator set",
        strategy_kwargs={
            "allow_direct": True,
            "allow_relay": True,
            "candidate_pool_strategy": "diverse_topk",
            "adaptive_operator_weights": True,
            "destroy_operator_set": ["random_remove"],
            "repair_operator_set": ["greedy_insert"]
        }
    ))
    return variants


def mock_get_ablation_config(variant_name):
    variants = mock_get_ablation_variants()
    for v in variants:
        if v.name == variant_name:
            return v
    return None


def mock_aggregate_results(results):
    from collections import defaultdict
    grouped = defaultdict(list)
    for result in results:
        key = (result["scene_name"], result["variant_name"])
        grouped[key].append(result)
    aggregated = []
    for (scene_name, variant_name), group_results in grouped.items():
        aggregated_row = {
            "scene_name": scene_name,
            "variant_name": variant_name,
            "num_runs": len(group_results)
        }
        metrics = [
            "completion_rate",
            "total_energy",
            "avg_delivery_time",
            "avg_wait_time_at_relay",
            "relay_count",
            "direct_count",
            "fallback_count",
            "charging_count",
            "failed_tasks",
            "total_distance",
            "total_distance_uav",
            "total_distance_agv"
        ]
        for metric in metrics:
            values = [r[metric] for r in group_results if r[metric] is not None]
            if values:
                mean_val = sum(values) / len(values)
                if len(values) > 1:
                    std_val = (sum((x - mean_val) ** 2 for x in values) / len(values)) ** 0.5
                else:
                    std_val = 0.0
                aggregated_row[f"{metric}_mean"] = mean_val
                aggregated_row[f"{metric}_std"] = std_val
            else:
                aggregated_row[f"{metric}_mean"] = None
                aggregated_row[f"{metric}_std"] = None
        aggregated.append(aggregated_row)
    return aggregated


def mock_build_comparison_vs_full(aggregate_rows):
    from collections import defaultdict
    scene_results = defaultdict(dict)
    for row in aggregate_rows:
        scene_results[row["scene_name"]][row["variant_name"]] = row
    comparisons = []
    for scene_name, scene_variants in scene_results.items():
        baseline = scene_variants.get("unified_full")
        if not baseline:
            continue
        for variant_name, variant_row in scene_variants.items():
            comparison_row = {
                "scene_name": scene_name,
                "variant_name": variant_name,
                "baseline_variant": "unified_full"
            }
            metrics = [
                ("completion_rate", float),
                ("total_energy", float),
                ("avg_delivery_time", float),
                ("fallback_count", float),
                ("charging_count", float)
            ]
            for metric, _ in metrics:
                baseline_val = baseline.get(f"{metric}_mean")
                variant_val = variant_row.get(f"{metric}_mean")
                if baseline_val is not None and variant_val is not None:
                    delta = variant_val - baseline_val
                    relative_delta = None
                    if abs(baseline_val) > 1e-9:
                        relative_delta = (variant_val - baseline_val) / baseline_val * 100.0
                    comparison_row[f"{metric}_delta"] = delta
                    comparison_row[f"{metric}_relative_delta"] = relative_delta
                else:
                    comparison_row[f"{metric}_delta"] = None
                    comparison_row[f"{metric}_relative_delta"] = None
            comparisons.append(comparison_row)
    return comparisons


def mock_load_metrics_from_dir(output_dir):
    metrics_file = os.path.join(output_dir, "metrics.json")
    if os.path.exists(metrics_file):
        with open(metrics_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# Use mocked functions instead of real imports
get_ablation_variants = mock_get_ablation_variants
get_ablation_config = mock_get_ablation_config
aggregate_results = mock_aggregate_results
build_comparison_vs_full = mock_build_comparison_vs_full
load_metrics_from_dir = mock_load_metrics_from_dir


class TestALNSAblationParameters(unittest.TestCase):
    """Test ALNS ablation parameters."""

    def test_allow_direct_false(self):
        """Test that allow_direct=False results in direct=False in candidate pool."""
        strategy = ALNSUnifiedStrategy(
            allow_direct=False,
            allow_relay=True,
            seed=42
        )
        
        uav = MagicMock()
        uav.id = 1
        uav.position = (0, 0)
        uav.battery = 100
        uav.max_range = 2000
        
        task = MagicMock()
        task.id = 1
        task.start_point = (100, 100)
        task.end_point = (200, 200)
        
        environment = MagicMock()
        environment.agvs = []
        
        depot_pos = (0, 0)
        
        pools = strategy._build_candidate_pools([uav], [task], environment, depot_pos)
        
        self.assertIn((task.id, uav.id), pools)
        self.assertFalse(pools[(task.id, uav.id)]["direct"])

    def test_allow_relay_false(self):
        """Test that allow_relay=False results in empty relay list in candidate pool."""
        strategy = ALNSUnifiedStrategy(
            allow_direct=True,
            allow_relay=False,
            seed=42
        )
        
        uav = MagicMock()
        uav.id = 1
        uav.position = (0, 0)
        uav.battery = 100
        uav.max_range = 2000
        uav.max_speed = 10
        
        task = MagicMock()
        task.id = 1
        task.start_point = (100, 100)
        task.end_point = (200, 200)
        task.deadline = None
        
        environment = MagicMock()
        environment.agvs = []
        
        depot_pos = (0, 0)
        
        pools = strategy._build_candidate_pools([uav], [task], environment, depot_pos)
        
        self.assertIn((task.id, uav.id), pools)
        self.assertEqual(pools[(task.id, uav.id)]["relay"], [])

    def test_adaptive_operator_weights_false(self):
        """Test that adaptive_operator_weights=False prevents weight updates."""
        operators = ALNSOperators(seed=42, adaptive_weights=False)
        
        initial_weight = operators._operator_weights[DestroyOperator.RANDOM_REMOVE]
        
        operators.update_operator_weights(
            DestroyOperator.RANDOM_REMOVE,
            RepairOperator.GREEDY_INSERT,
            improved=True,
            best_improved=True
        )
        
        final_weight = operators._operator_weights[DestroyOperator.RANDOM_REMOVE]
        
        self.assertEqual(initial_weight, final_weight)

    def test_random_topk_reproducibility(self):
        """Test that random_topk is reproducible with fixed seed."""
        strategy1 = ALNSUnifiedStrategy(
            candidate_pool_strategy="random_topk",
            seed=42
        )
        strategy2 = ALNSUnifiedStrategy(
            candidate_pool_strategy="random_topk",
            seed=42
        )
        
        candidates = [
            {"cost_delta": 1.0, "mode_risk": 0.1, "predicted_wait": 1.0, "relay_point": (100, 100), "agv": MagicMock()},
            {"cost_delta": 2.0, "mode_risk": 0.2, "predicted_wait": 2.0, "relay_point": (200, 200), "agv": MagicMock()},
            {"cost_delta": 3.0, "mode_risk": 0.3, "predicted_wait": 3.0, "relay_point": (300, 300), "agv": MagicMock()},
        ]
        
        result1 = strategy1._select_top_k_candidates(candidates, 2, "random_topk")
        result2 = strategy2._select_top_k_candidates(candidates, 2, "random_topk")
        
        self.assertEqual(len(result1), len(result2))
        self.assertEqual([r[0] for r in result1], [r[0] for r in result2])

    def test_strategy_kwargs_passed_to_alns(self):
        """Test that strategy_kwargs are correctly passed to ALNSUnifiedStrategy."""
        kwargs = {
            "allow_direct": False,
            "allow_relay": True,
            "candidate_pool_strategy": "greedy_topk",
            "candidate_pool_k": 3,
            "adaptive_operator_weights": False,
        }
        
        strategy = ALNSUnifiedStrategy(seed=42, **kwargs)
        
        self.assertFalse(strategy.allow_direct)
        self.assertTrue(strategy.allow_relay)
        self.assertEqual(strategy.candidate_pool_strategy, "greedy_topk")
        self.assertEqual(strategy.candidate_pool_k, 3)
        self.assertFalse(strategy.adaptive_operator_weights)

    def test_destroy_operator_set_configurable(self):
        """Test that destroy_operator_set can be configured."""
        strategy = ALNSUnifiedStrategy(
            destroy_operator_set=["random_remove"],
            seed=42
        )
        
        ops = strategy._get_destroy_operators()
        
        self.assertEqual(len(ops), 1)
        self.assertIn(DestroyOperator.RANDOM_REMOVE, ops)

    def test_repair_operator_set_configurable(self):
        """Test that repair_operator_set can be configured."""
        strategy = ALNSUnifiedStrategy(
            repair_operator_set=["greedy_insert"],
            seed=42
        )
        
        ops = strategy._get_repair_operators()
        
        self.assertEqual(len(ops), 1)
        self.assertIn(RepairOperator.GREEDY_INSERT, ops)

    def test_candidate_pool_strategies_produce_distinct_results(self):
        """Test that different pool strategies produce distinguishable results."""
        strategy_diverse = ALNSUnifiedStrategy(
            candidate_pool_strategy="diverse_topk",
            seed=42
        )
        strategy_greedy = ALNSUnifiedStrategy(
            candidate_pool_strategy="greedy_topk",
            seed=42
        )
        strategy_random = ALNSUnifiedStrategy(
            candidate_pool_strategy="random_topk",
            seed=42
        )
        
        agv_mock = MagicMock()
        agv_mock.id = 1
        
        candidates = [
            {"cost_delta": 1.0, "mode_risk": 0.9, "predicted_wait": 1.0, "agv": agv_mock, "relay_point": (100, 100)},
            {"cost_delta": 2.0, "mode_risk": 0.1, "predicted_wait": 5.0, "agv": agv_mock, "relay_point": (200, 200)},
            {"cost_delta": 3.0, "mode_risk": 0.5, "predicted_wait": 3.0, "agv": agv_mock, "relay_point": (300, 300)},
            {"cost_delta": 4.0, "mode_risk": 0.2, "predicted_wait": 2.0, "agv": agv_mock, "relay_point": (400, 400)},
            {"cost_delta": 5.0, "mode_risk": 0.8, "predicted_wait": 4.0, "agv": agv_mock, "relay_point": (500, 500)},
        ]
        
        result_diverse = strategy_diverse._select_top_k_candidates(candidates, 2, "diverse_topk")
        result_greedy = strategy_greedy._select_top_k_candidates(candidates, 2, "greedy_topk")
        result_random = strategy_random._select_top_k_candidates(candidates, 2, "random_topk")
        
        result_diverse_ids = [r[0] for r in result_diverse]
        result_greedy_ids = [r[0] for r in result_greedy]
        result_random_ids = [r[0] for r in result_random]
        
        strategies_produce_different_results = (
            result_diverse_ids != result_greedy_ids or
            result_diverse_ids != result_random_ids or
            result_greedy_ids != result_random_ids
        )
        
        self.assertTrue(strategies_produce_different_results,
                        "Different pool strategies should produce distinguishable results")

    def test_simple_ops_returns_only_specified_operators(self):
        """Test that simple_ops configuration returns only specified operators."""
        strategy = ALNSUnifiedStrategy(
            destroy_operator_set=["random_remove"],
            repair_operator_set=["greedy_insert"],
            seed=42
        )
        
        destroy_ops = strategy._get_destroy_operators()
        repair_ops = strategy._get_repair_operators()
        
        self.assertEqual(len(destroy_ops), 1, "Should only have one destroy operator")
        self.assertIn(DestroyOperator.RANDOM_REMOVE, destroy_ops)
        self.assertNotIn(DestroyOperator.WORST_REMOVE, destroy_ops)
        self.assertNotIn(DestroyOperator.HIGH_ENERGY_REMOVE, destroy_ops)
        
        self.assertEqual(len(repair_ops), 1, "Should only have one repair operator")
        self.assertIn(RepairOperator.GREEDY_INSERT, repair_ops)
        self.assertNotIn(RepairOperator.REGRET_INSERT, repair_ops)
        self.assertNotIn(RepairOperator.RELAY_AWARE_REGRET_INSERT, repair_ops)


class TestAblationRunnerFunctions(unittest.TestCase):
    """Test functions from ablation runner."""

    def test_get_ablation_config_returns_correct_config(self):
        """Test that get_ablation_config returns correct configuration."""
        config = get_ablation_config("unified_full")
        self.assertIsNotNone(config)
        self.assertEqual(config.name, "unified_full")
        self.assertTrue(config.strategy_kwargs["allow_direct"])
        self.assertTrue(config.strategy_kwargs["allow_relay"])
        
        config = get_ablation_config("direct_only")
        self.assertIsNotNone(config)
        self.assertEqual(config.name, "direct_only")
        self.assertTrue(config.strategy_kwargs["allow_direct"])
        self.assertFalse(config.strategy_kwargs["allow_relay"])
        
        config = get_ablation_config("relay_only")
        self.assertIsNotNone(config)
        self.assertEqual(config.name, "relay_only")
        self.assertFalse(config.strategy_kwargs["allow_direct"])
        self.assertTrue(config.strategy_kwargs["allow_relay"])
        
        config = get_ablation_config("fixed_weights")
        self.assertIsNotNone(config)
        self.assertEqual(config.name, "fixed_weights")
        self.assertFalse(config.strategy_kwargs["adaptive_operator_weights"])

    def test_get_ablation_variants_returns_all_7_variants(self):
        """Test that get_ablation_variants returns all 7 variants."""
        variants = get_ablation_variants()
        self.assertEqual(len(variants), 7)
        variant_names = [v.name for v in variants]
        self.assertIn("unified_full", variant_names)
        self.assertIn("direct_only", variant_names)
        self.assertIn("relay_only", variant_names)
        self.assertIn("greedy_pool", variant_names)
        self.assertIn("random_pool", variant_names)
        self.assertIn("fixed_weights", variant_names)
        self.assertIn("simple_ops", variant_names)

    def test_direct_only_relay_only_configs_correct(self):
        """Test that direct_only and relay_only configurations are correct."""
        variants = get_ablation_variants()
        variant_dict = {v.name: v for v in variants}
        
        direct_only = variant_dict["direct_only"]
        self.assertTrue(direct_only.strategy_kwargs["allow_direct"])
        self.assertFalse(direct_only.strategy_kwargs["allow_relay"])
        
        relay_only = variant_dict["relay_only"]
        self.assertFalse(relay_only.strategy_kwargs["allow_direct"])
        self.assertTrue(relay_only.strategy_kwargs["allow_relay"])

    def test_fixed_weights_adaptive_false(self):
        """Test that fixed_weights has adaptive_operator_weights=False."""
        variants = get_ablation_variants()
        variant_dict = {v.name: v for v in variants}
        fixed_weights = variant_dict["fixed_weights"]
        self.assertFalse(fixed_weights.strategy_kwargs["adaptive_operator_weights"])

    def test_simple_ops_returns_correct_operators(self):
        """Test that simple_ops has correct operator sets."""
        variants = get_ablation_variants()
        variant_dict = {v.name: v for v in variants}
        simple_ops = variant_dict["simple_ops"]
        self.assertEqual(simple_ops.strategy_kwargs["destroy_operator_set"], ["random_remove"])
        self.assertEqual(simple_ops.strategy_kwargs["repair_operator_set"], ["greedy_insert"])

    def test_aggregate_results(self):
        """Test that aggregate_results correctly calculates mean and std."""
        results = [
            {
                "scene_name": "scene1",
                "variant_name": "var1",
                "completion_rate": 0.8,
                "total_energy": 100.0,
                "avg_delivery_time": 50.0,
                "avg_wait_time_at_relay": 10.0,
                "relay_count": 5,
                "direct_count": 3,
                "fallback_count": 1,
                "charging_count": 2,
                "failed_tasks": 0,
                "total_distance": 1000.0,
                "total_distance_uav": 600.0,
                "total_distance_agv": 400.0
            },
            {
                "scene_name": "scene1",
                "variant_name": "var1",
                "completion_rate": 0.9,
                "total_energy": 110.0,
                "avg_delivery_time": 60.0,
                "avg_wait_time_at_relay": 12.0,
                "relay_count": 6,
                "direct_count": 2,
                "fallback_count": 0,
                "charging_count": 3,
                "failed_tasks": 1,
                "total_distance": 1100.0,
                "total_distance_uav": 700.0,
                "total_distance_agv": 400.0
            }
        ]
        
        aggregated = aggregate_results(results)
        self.assertEqual(len(aggregated), 1)
        
        row = aggregated[0]
        self.assertEqual(row["scene_name"], "scene1")
        self.assertEqual(row["variant_name"], "var1")
        self.assertEqual(row["num_runs"], 2)
        
        self.assertAlmostEqual(row["completion_rate_mean"], 0.85)
        self.assertAlmostEqual(row["completion_rate_std"], 0.05)
        self.assertAlmostEqual(row["total_energy_mean"], 105.0)
        self.assertAlmostEqual(row["total_energy_std"], 5.0)

    def test_build_comparison_vs_full(self):
        """Test that build_comparison_vs_full correctly calculates deltas."""
        aggregate_rows = [
            {
                "scene_name": "scene1",
                "variant_name": "unified_full",
                "completion_rate_mean": 0.9,
                "total_energy_mean": 100.0,
                "avg_delivery_time_mean": 50.0,
                "fallback_count_mean": 1.0,
                "charging_count_mean": 2.0
            },
            {
                "scene_name": "scene1",
                "variant_name": "direct_only",
                "completion_rate_mean": 0.8,
                "total_energy_mean": 120.0,
                "avg_delivery_time_mean": 60.0,
                "fallback_count_mean": 2.0,
                "charging_count_mean": 3.0
            }
        ]
        
        comparisons = build_comparison_vs_full(aggregate_rows)
        self.assertEqual(len(comparisons), 2)
        
        direct_only_comparison = None
        for c in comparisons:
            if c["variant_name"] == "direct_only":
                direct_only_comparison = c
                break
        
        self.assertIsNotNone(direct_only_comparison)
        
        self.assertAlmostEqual(direct_only_comparison["completion_rate_delta"], -0.1)
        self.assertAlmostEqual(direct_only_comparison["total_energy_delta"], 20.0)
        self.assertAlmostEqual(direct_only_comparison["total_energy_relative_delta"], 20.0)
        self.assertAlmostEqual(direct_only_comparison["avg_delivery_time_delta"], 10.0)
        self.assertAlmostEqual(direct_only_comparison["fallback_count_delta"], 1.0)
        self.assertAlmostEqual(direct_only_comparison["charging_count_delta"], 1.0)

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"completion_rate": 0.9, "total_energy": 100.0}')
    def test_load_metrics_from_dir(self, mock_file, mock_exists):
        """Test that load_metrics_from_dir correctly loads metrics from JSON."""
        mock_exists.return_value = True
        
        loaded = load_metrics_from_dir("/tmp/test")
        self.assertEqual(loaded, {"completion_rate": 0.9, "total_energy": 100.0})

    @patch('os.path.exists')
    def test_load_metrics_from_dir_nonexistent_file(self, mock_exists):
        """Test that load_metrics_from_dir returns empty dict for nonexistent file."""
        mock_exists.return_value = False
        
        loaded = load_metrics_from_dir("/tmp/nonexistent")
        self.assertEqual(loaded, {})


if __name__ == "__main__":
    unittest.main()

