<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RunSelector from '../components/RunSelector.vue'
import RunTrendChart from '../components/RunTrendChart.vue'
import TaskTable from '../components/TaskTable.vue'
import TimelinePanel from '../components/TimelinePanel.vue'
import PlotGallery from '../components/PlotGallery.vue'
import EmptyState from '../components/EmptyState.vue'
import { getRuns, getRunDetail } from '../services/runRepository'
import type { RunInfo, Metrics, Metadata, StepRecord, TaskRecord, CoordinationEvent } from '../types'

const route = useRoute()
const router = useRouter()
const runs = ref<RunInfo[]>([])
const currentExp = ref('')
const currentTs = ref('')
const metrics = ref<Metrics | null>(null)
const metadata = ref<Metadata | null>(null)
const steps = ref<StepRecord[] | null>(null)
const tasks = ref<TaskRecord[] | null>(null)
const events = ref<CoordinationEvent[] | null>(null)
const loading = ref(true)

const title = computed(() => {
  if (!metadata.value) return '运行详情'
  return `${metadata.value.experiment_name} - ${metadata.value.strategy}`
})

const completionSeries = computed(() => {
  if (!steps.value) return []
  return [{
    name: '已完成任务',
    data: steps.value.map(s => s.completed_tasks_cumulative),
    color: '#2e7d32'
  }]
})

const energySeries = computed(() => {
  if (!steps.value) return []
  return [{
    name: '累计能耗',
    data: steps.value.map(s => s.total_energy_cumulative),
    color: '#f99500'
  }]
})

const distanceSeries = computed(() => {
  if (!steps.value) return []
  return [{
    name: '累计距离',
    data: steps.value.map(s => s.total_distance_cumulative),
    color: '#088395'
  }]
})

const chargingSeries = computed(() => {
  if (!steps.value) return []
  return [{
    name: '累计充电次数',
    data: steps.value.map(s => s.charging_count_cumulative),
    color: '#7b1fa2'
  }]
})

const stepLabels = computed(() => {
  if (!steps.value) return []
  return steps.value.map((s, i) => i % 5 === 0 ? `${s.step}` : '')
})

const hasWaitTimeData = computed(() => {
  return tasks.value?.some(t => t.wait_time_at_relay !== null && t.wait_time_at_relay > 0)
})

async function loadRuns() {
  runs.value = await getRuns()
}

async function loadRunDetail(exp: string, ts: string) {
  loading.value = true
  const result = await getRunDetail(exp, ts)
  metrics.value = result.metrics
  metadata.value = result.metadata
  steps.value = result.steps
  tasks.value = result.tasks
  events.value = result.events
  loading.value = false
}

function handleRunSelect(run: RunInfo) {
  currentExp.value = run.experiment_name
  currentTs.value = run.timestamp
  router.push({ query: { exp: run.experiment_name, ts: run.timestamp } })
}

function goBack() {
  router.push('/')
}

onMounted(async () => {
  await loadRuns()
  const exp = route.query.exp as string || runs.value[0]?.experiment_name || ''
  const ts = route.query.ts as string || runs.value[0]?.timestamp || ''
  if (exp && ts) {
    currentExp.value = exp
    currentTs.value = ts
    await loadRunDetail(exp, ts)
  } else {
    loading.value = false
  }
})

watch([currentExp, currentTs], async ([exp, ts]) => {
  if (exp && ts) {
    await loadRunDetail(exp, ts)
  }
})
</script>

<template>
  <div class="run-detail-page">
    <div class="page-header">
      <button class="back-btn" @click="goBack">
        <svg class="back-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 18l-6-6 6-6" />
        </svg>
        返回
      </button>
      <h1 class="page-title">{{ title }}</h1>
    </div>

    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <span>加载数据中...</span>
    </div>

    <template v-else>
      <div v-if="!metrics" class="empty-state-container">
        <EmptyState 
          title="暂无数据" 
          description="未找到该运行的数据，请选择其他运行记录" 
        />
      </div>

      <div v-else class="detail-content">
        <div class="selector-section">
          <RunSelector 
            :runs="runs" 
            :current-exp="currentExp" 
            :current-ts="currentTs"
            @select="handleRunSelect" 
          />
        </div>

        <div class="summary-header">
          <div class="summary-card">
            <div class="summary-row">
              <div class="summary-item">
                <span class="summary-label">场景</span>
                <span class="summary-value">{{ metrics.scenario_name }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">策略</span>
                <span class="summary-value">{{ metadata?.strategy }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">种子</span>
                <span class="summary-value">{{ metrics.seed }}</span>
              </div>
            </div>
            <div class="summary-row">
              <div class="summary-item highlight">
                <span class="summary-label">完成率</span>
                <span class="summary-value">{{ (metrics.completion_rate * 100).toFixed(1) }}%</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">总能耗</span>
                <span class="summary-value">{{ metrics.total_energy.toFixed(1) }} Wh</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">总距离</span>
                <span class="summary-value">{{ metrics.total_distance.toFixed(1) }} m</span>
              </div>
            </div>
          </div>
        </div>

        <div class="charts-section">
          <div class="section-header">
            <h2 class="section-title">累积时序图</h2>
          </div>
          <div class="charts-grid">
            <div class="chart-item">
              <div class="chart-title">已完成任务</div>
              <RunTrendChart 
                :x-data="stepLabels" 
                :series="completionSeries" 
                type="line" 
                :height="220"
              />
            </div>
            <div class="chart-item">
              <div class="chart-title">累计能耗</div>
              <RunTrendChart 
                :x-data="stepLabels" 
                :series="energySeries" 
                type="area" 
                :height="220"
              />
            </div>
            <div class="chart-item">
              <div class="chart-title">累计距离</div>
              <RunTrendChart 
                :x-data="stepLabels" 
                :series="distanceSeries" 
                type="area" 
                :height="220"
              />
            </div>
            <div class="chart-item">
              <div class="chart-title">累计充电次数</div>
              <RunTrendChart 
                :x-data="stepLabels" 
                :series="chargingSeries" 
                type="line" 
                :height="220"
              />
            </div>
          </div>
        </div>

        <div class="task-section">
          <div class="section-header">
            <h2 class="section-title">任务分析</h2>
            <span class="section-subtitle">共 {{ tasks?.length || 0 }} 个任务</span>
          </div>
          <TaskTable :tasks="tasks" />
        </div>

        <div v-if="hasWaitTimeData" class="wait-time-section">
          <div class="section-header">
            <h2 class="section-title">中继等待时间</h2>
          </div>
          <div class="wait-time-chart">
            <RunTrendChart 
              :x-data="tasks?.map(t => t.task_id) || []" 
              :series="[{ name: '等待时间', data: tasks?.map(t => t.wait_time_at_relay || 0) || [], color: '#e65100' }]" 
              type="line" 
              :height="250"
            />
          </div>
        </div>

        <div class="timeline-section">
          <div class="section-header">
            <h2 class="section-title">协同事件</h2>
          </div>
          <TimelinePanel :events="events" />
        </div>

        <div class="gallery-section">
          <div class="section-header">
            <h2 class="section-title">可视化结果</h2>
          </div>
          <PlotGallery />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.run-detail-page {
  padding-bottom: 32px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: white;
  border: 1px solid #e6ebf1;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  color: #525f7f;
  font-size: 14px;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: #f0f7ff;
  border-color: #0a4d68;
}

.back-icon {
  width: 16px;
  height: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1e3a5f;
  margin: 0;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f0f0f0;
  border-top-color: #0a4d68;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state-container {
  padding: 40px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.summary-header {
  margin-bottom: 8px;
}

.summary-card {
  background: linear-gradient(135deg, #0a4d68 0%, #088395 100%);
  border-radius: 16px;
  padding: 24px;
}

.summary-row {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  flex-direction: column;
}

.summary-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 4px;
}

.summary-value {
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.summary-item.highlight .summary-value {
  font-size: 24px;
  color: #05bfdb;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e3a5f;
  margin: 0;
}

.section-subtitle {
  font-size: 14px;
  color: #8898aa;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.chart-item {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}

.chart-title {
  font-size: 14px;
  font-weight: 500;
  color: #525f7f;
  margin-bottom: 12px;
}

.wait-time-chart {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}
</style>