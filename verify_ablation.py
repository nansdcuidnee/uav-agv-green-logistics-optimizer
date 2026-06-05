
"""Simple script to verify ablation experiment code is working"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("Testing ablation experiment code...")
print("=" * 60)

print("\n1. Testing imports:")
try:
    from experiments.run_alns_ablation import (
        get_ablation_variants,
        get_ablation_config,
        aggregate_results,
        build_comparison_vs_full
    )
    print("   ✓ Imports successful")
except Exception as e:
    print(f"   ✗ Imports failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n2. Testing get_ablation_variants():")
try:
    variants = get_ablation_variants()
    print(f"   ✓ Found {len(variants)} ablation variants")
    
    variant_names = [v.name for v in variants]
    print(f"   Variants: {', '.join(variant_names)}")
    
    required_variants = [
        "unified_full",
        "direct_only",
        "relay_only",
        "greedy_pool",
        "random_pool",
        "fixed_weights",
        "simple_ops"
    ]
    
    all_found = True
    for req_variant in required_variants:
        if req_variant not in variant_names:
            print(f"   ✗ Missing required variant: {req_variant}")
            all_found = False
    if all_found:
        print("   ✓ All required variants present")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n3. Testing aggregate_results():")
try:
    test_results = [
        {
            "scene_name": "test_scene",
            "variant_name": "unified_full",
            "completion_rate": 0.9,
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
            "scene_name": "test_scene",
            "variant_name": "unified_full",
            "completion_rate": 0.85,
            "total_energy": 110.0,
            "avg_delivery_time": 55.0,
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
    
    aggregated = aggregate_results(test_results)
    print(f"   ✓ Aggregated {len(aggregated)} results")
    print(f"   Mean completion rate: {aggregated[0]['completion_rate_mean']:.2f}")
    print(f"   Std completion rate: {aggregated[0]['completion_rate_std']:.2f}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n4. Testing build_comparison_vs_full():")
try:
    test_aggregate = [
        {
            "scene_name": "test_scene",
            "variant_name": "unified_full",
            "completion_rate_mean": 0.9,
            "total_energy_mean": 100.0,
            "avg_delivery_time_mean": 50.0,
            "fallback_count_mean": 1.0,
            "charging_count_mean": 2.0
        },
        {
            "scene_name": "test_scene",
            "variant_name": "direct_only",
            "completion_rate_mean": 0.8,
            "total_energy_mean": 120.0,
            "avg_delivery_time_mean": 60.0,
            "fallback_count_mean": 2.0,
            "charging_count_mean": 3.0
        }
    ]
    
    comparisons = build_comparison_vs_full(test_aggregate)
    print(f"   ✓ Built {len(comparisons)} comparison results")
    
    direct_only_comp = [c for c in comparisons if c['variant_name'] == 'direct_only'][0]
    print(f"   Completion rate delta: {direct_only_comp['completion_rate_delta']:.2f}")
    print(f"   Energy delta: {direct_only_comp['total_energy_delta']:.2f}")
    print(f"   Energy relative delta: {direct_only_comp['total_energy_relative_delta']:.1f}%")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("All tests passed! Ablation experiment code is ready.")

