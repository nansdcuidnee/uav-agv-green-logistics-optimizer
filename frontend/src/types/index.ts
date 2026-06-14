export interface Metrics {
  strategy_name: string
  scenario_name: string
  seed: number
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  completion_rate: number
  on_time_tasks: number
  on_time_rate: number
  on_time_rate_given_completed: number
  total_time: number
  avg_delivery_time: number
  avg_wait_time_at_relay: number | null
  max_delivery_time: number
  total_distance_uav: number
  total_distance_agv: number
  total_distance: number
  uav_energy: number
  agv_energy: number
  charge_loss_energy: number
  total_energy: number
  avg_energy_per_task: number
  energy_per_km: number
  carbon_emission: number
  charging_count: number
  fallback_count: number
  replan_count: number
  relay_count: number
  direct_count: number
}

export interface Metadata {
  experiment_name: string
  timestamp: string
  strategy: string
  records_granularity: string
  required_artifacts: string[]
  plots: string[]
  summary: {
    initial_task_count: number
    completed_tasks: number
    time_steps: number
  }
}

export interface StepRecord {
  step: number
  sim_time: number
  active_tasks: number
  completed_tasks_cumulative: number
  charging_count_cumulative: number
  uav_distance_cumulative: number
  agv_distance_cumulative: number
  total_distance_cumulative: number
  uav_energy_cumulative: number
  agv_energy_cumulative: number
  charge_loss_energy_cumulative: number
  total_energy_cumulative: number
}

export interface TaskRecord {
  task_id: string
  status: string
  start_time: number
  end_time: number | null
  origin_x: number
  origin_y: number
  dest_x: number
  dest_y: number
  priority: number
  assigned_uav: string | null
  assigned_agv: string | null
  delivery_type: string
  energy_consumed: number
  distance: number
  wait_time_at_relay: number | null
}

export interface CoordinationEvent {
  step: number
  sim_time: number
  event_type: string
  task_id: string | null
  uav_id: string | null
  agv_id: string | null
  description: string
  location_x?: number
  location_y?: number
}

export interface RunInfo {
  experiment_name: string
  timestamp: string
  strategy: string
  full_path: string
  metrics: Metrics
  metadata: Metadata
}

export interface AblationResult {
  scene_name: string
  config_path: string
  variant_name: string
  seed: number
  completion_rate: number
  total_energy: number
  avg_delivery_time: number
  avg_wait_time_at_relay: number | null
  relay_count: number
  direct_count: number
  fallback_count: number
  charging_count: number
  failed_tasks: number
  total_distance: number
  total_distance_uav: number
  total_distance_agv: number
  run_dir: string
}

export interface AblationSummary {
  timestamp: string
  total_runs: number
  results: AblationResult[]
}

export interface VariantAggregate {
  variant_name: string
  completion_rate_mean: number
  completion_rate_std: number
  total_energy_mean: number
  total_energy_std: number
  avg_delivery_time_mean: number
  avg_delivery_time_std: number
  num_runs: number
}

export interface SceneVariantPair {
  scene_name: string
  variant_name: string
  completion_rate: number
  total_energy: number
}

export interface DeltaItem {
  variant_name: string
  completion_rate_delta: number
  total_energy_delta: number
}