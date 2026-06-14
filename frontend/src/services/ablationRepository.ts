import type { VariantAggregate, SceneVariantPair, DeltaItem } from '../types'

export async function getAblationSummary(): Promise<SceneVariantPair[] | null> {
  const mockData: SceneVariantPair[] = [
    { scene_name: 'scene_small', variant_name: 'unified_full', completion_rate: 0.98, total_energy: 245.6 },
    { scene_name: 'scene_small', variant_name: 'direct_only', completion_rate: 0.85, total_energy: 289.3 },
    { scene_name: 'scene_small', variant_name: 'relay_only', completion_rate: 0.92, total_energy: 267.8 },
    { scene_name: 'scene_small', variant_name: 'simple_ops', completion_rate: 0.95, total_energy: 252.1 },
    { scene_name: 'scene_small', variant_name: 'fixed_weights', completion_rate: 0.93, total_energy: 261.4 },
    { scene_name: 'scene_small', variant_name: 'greedy_pool', completion_rate: 0.91, total_energy: 273.2 },
    { scene_name: 'scene_small', variant_name: 'random_pool', completion_rate: 0.88, total_energy: 278.9 },
    { scene_name: 'scene_medium', variant_name: 'unified_full', completion_rate: 0.96, total_energy: 312.4 },
    { scene_name: 'scene_medium', variant_name: 'direct_only', completion_rate: 0.82, total_energy: 356.7 },
    { scene_name: 'scene_medium', variant_name: 'relay_only', completion_rate: 0.89, total_energy: 334.2 },
    { scene_name: 'scene_medium', variant_name: 'simple_ops', completion_rate: 0.93, total_energy: 321.8 },
    { scene_name: 'scene_medium', variant_name: 'fixed_weights', completion_rate: 0.91, total_energy: 328.5 },
    { scene_name: 'scene_medium', variant_name: 'greedy_pool', completion_rate: 0.88, total_energy: 341.3 },
    { scene_name: 'scene_medium', variant_name: 'random_pool', completion_rate: 0.85, total_energy: 347.9 },
    { scene_name: 'scene_large', variant_name: 'unified_full', completion_rate: 0.94, total_energy: 389.2 },
    { scene_name: 'scene_large', variant_name: 'direct_only', completion_rate: 0.78, total_energy: 423.5 },
    { scene_name: 'scene_large', variant_name: 'relay_only', completion_rate: 0.86, total_energy: 401.7 },
    { scene_name: 'scene_large', variant_name: 'simple_ops', completion_rate: 0.90, total_energy: 392.4 },
    { scene_name: 'scene_large', variant_name: 'fixed_weights', completion_rate: 0.88, total_energy: 398.6 },
    { scene_name: 'scene_large', variant_name: 'greedy_pool', completion_rate: 0.85, total_energy: 409.1 },
    { scene_name: 'scene_large', variant_name: 'random_pool', completion_rate: 0.82, total_energy: 415.8 }
  ]
  return mockData
}

export async function getVariantAggregates(): Promise<VariantAggregate[] | null> {
  const mockData: VariantAggregate[] = [
    { variant_name: 'unified_full', completion_rate_mean: 0.96, completion_rate_std: 0.016, total_energy_mean: 315.7, total_energy_std: 71.8, avg_delivery_time_mean: 45.2, avg_delivery_time_std: 8.3, num_runs: 15 },
    { variant_name: 'direct_only', completion_rate_mean: 0.817, completion_rate_std: 0.029, total_energy_mean: 356.5, total_energy_std: 67.1, avg_delivery_time_mean: 52.8, avg_delivery_time_std: 9.1, num_runs: 15 },
    { variant_name: 'relay_only', completion_rate_mean: 0.89, completion_rate_std: 0.025, total_energy_mean: 334.6, total_energy_std: 67.0, avg_delivery_time_mean: 49.5, avg_delivery_time_std: 8.7, num_runs: 15 },
    { variant_name: 'simple_ops', completion_rate_mean: 0.927, completion_rate_std: 0.021, total_energy_mean: 322.1, total_energy_std: 70.2, avg_delivery_time_mean: 47.1, avg_delivery_time_std: 8.5, num_runs: 15 },
    { variant_name: 'fixed_weights', completion_rate_mean: 0.907, completion_rate_std: 0.021, total_energy_mean: 329.5, total_energy_std: 69.6, avg_delivery_time_mean: 48.2, avg_delivery_time_std: 8.6, num_runs: 15 },
    { variant_name: 'greedy_pool', completion_rate_mean: 0.88, completion_rate_std: 0.025, total_energy_mean: 341.2, total_energy_std: 68.5, avg_delivery_time_mean: 49.8, avg_delivery_time_std: 8.8, num_runs: 15 },
    { variant_name: 'random_pool', completion_rate_mean: 0.85, completion_rate_std: 0.029, total_energy_mean: 347.5, total_energy_std: 68.9, avg_delivery_time_mean: 50.9, avg_delivery_time_std: 8.9, num_runs: 15 }
  ]
  return mockData
}

export async function getDeltaComparison(): Promise<DeltaItem[] | null> {
  const mockData: DeltaItem[] = [
    { variant_name: 'direct_only', completion_rate_delta: -0.143, total_energy_delta: 40.8 },
    { variant_name: 'relay_only', completion_rate_delta: -0.07, total_energy_delta: 18.9 },
    { variant_name: 'simple_ops', completion_rate_delta: -0.033, total_energy_delta: 6.4 },
    { variant_name: 'fixed_weights', completion_rate_delta: -0.053, total_energy_delta: 13.8 },
    { variant_name: 'greedy_pool', completion_rate_delta: -0.08, total_energy_delta: 25.5 },
    { variant_name: 'random_pool', completion_rate_delta: -0.11, total_energy_delta: 31.8 }
  ]
  return mockData
}

export async function getScenes(): Promise<string[] | null> {
  return ['scene_small', 'scene_medium', 'scene_large']
}