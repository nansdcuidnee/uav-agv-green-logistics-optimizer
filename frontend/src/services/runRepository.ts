import { loadJson, loadCsv } from './dataLoader'
import type { Metrics, Metadata, StepRecord, TaskRecord, CoordinationEvent, RunInfo } from '../types'

const MOCK_BASE = '/mock-results'

export async function getRuns(): Promise<RunInfo[]> {
  const runs: RunInfo[] = []
  const experiments = [
    'demo_relay_demo',
    'demo_presentation',
    'default_experiment',
    'pickup_delivery_generated'
  ]

  for (const exp of experiments) {
    const timestamps = ['20260614_112314', '20260614_111633', '20260614_093350', '20260603_214047']
    for (const ts of timestamps) {
      const metrics = await loadJson<Metrics>(`${MOCK_BASE}/runs/${exp}/${ts}/metrics.json`)
      const metadata = await loadJson<Metadata>(`${MOCK_BASE}/runs/${exp}/${ts}/metadata.json`)
      if (metrics && metadata) {
        runs.push({
          experiment_name: exp,
          timestamp: ts,
          strategy: metadata.strategy,
          full_path: `${exp}/${ts}`,
          metrics,
          metadata
        })
      }
    }
  }
  return runs.sort((a, b) => b.timestamp.localeCompare(a.timestamp))
}

export async function getRunDetail(experimentName: string, timestamp: string): Promise<{
  metrics: Metrics | null
  metadata: Metadata | null
  steps: StepRecord[] | null
  tasks: TaskRecord[] | null
  events: CoordinationEvent[] | null
}> {
  const basePath = `${MOCK_BASE}/runs/${experimentName}/${timestamp}`
  const [metrics, metadata, steps, tasks, events] = await Promise.all([
    loadJson<Metrics>(`${basePath}/metrics.json`),
    loadJson<Metadata>(`${basePath}/metadata.json`),
    loadCsv<StepRecord>(`${basePath}/records/steps.csv`),
    loadCsv<TaskRecord>(`${basePath}/records/tasks.csv`),
    loadCsv<CoordinationEvent>(`${basePath}/records/coordination_events.csv`)
  ])
  return { metrics, metadata, steps, tasks, events }
}

export async function getLatestRun(): Promise<RunInfo | null> {
  const runs = await getRuns()
  return runs.length > 0 ? runs[0] : null
}