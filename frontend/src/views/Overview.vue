<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import HeroBanner from '../components/HeroBanner.vue'
import KpiGrid from '../components/KpiGrid.vue'
import RunList from '../components/RunList.vue'
import RunTrendChart from '../components/RunTrendChart.vue'
import ScatterInsightChart from '../components/ScatterInsightChart.vue'
import PlotGallery from '../components/PlotGallery.vue'
import EmptyState from '../components/EmptyState.vue'
import { getRuns, getLatestRun } from '../services/runRepository'
import type { RunInfo } from '../types'

const router = useRouter()
const runs = ref<RunInfo[]>([])
const latestRun = ref<RunInfo | null>(null)
const loading = ref(true)

const runDates = computed(() => {
  return runs.value.map(r => {
    const ts = r.timestamp
    return `${ts.slice(4, 6)}/${ts.slice(6, 8)} ${ts.slice(8, 10)}:${ts.slice(10, 12)}`
  })
})

const completionRateSeries = computed(() => [{
  name: '完成率',
  data: runs.value.map(r => r.metrics.completion_rate * 100),
  color: '#088395'
}])

const energySeries = computed(() => [{
  name: '总能耗',
  data: runs.value.map(r => r.metrics.total_energy),
  color: '#f99500'
}])

const scatterData = computed(() => {
  return runs.value.map(r => ({
    x: r.metrics.completion_rate * 100,
    y: r.metrics.total_energy,
    strategy: r.strategy
  }))
})

const insightSummary = computed(() => {
  if (runs.value.length === 0) return ''
  const avgCompletion = runs.value.reduce((sum, r) => sum + r.metrics.completion_rate, 0) / runs.value.length
  const avgEnergy = runs.value.reduce((sum, r) => sum + r.metrics.total_energy, 0) / runs.value.length
  const bestStrategy = [...runs.value].sort((a, b) => {
    const scoreA = a.metrics.completion_rate - a.metrics.total_energy * 0.01
    const scoreB = b.metrics.completion_rate - b.metrics.total_energy * 0.01
    return scoreB - scoreA
  })[0]
  return `最近 ${runs.value.length} 次运行中，平均完成率 ${(avgCompletion * 100).toFixed(1)}%，平均能耗 ${avgEnergy.toFixed(1)} Wh。策略「${bestStrategy.strategy}」在完成率与能耗平衡上表现最优。`
})

async function loadData() {
  loading.value = true
  const [allRuns, latest] = await Promise.all([getRuns(), getLatestRun()])
  runs.value = allRuns.slice(0, 12)
  latestRun.value = latest
  loading.value = false
}

function handleViewRuns() {
  router.push('/runs')
}

function handleViewAblation() {
  router.push('/ablation')
}

function handleRunSelect(run: RunInfo) {
  router.push({ path: '/runs', query: { exp: run.experiment_name, ts: run.timestamp } })
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="overview-page">
    <HeroBanner @viewRuns="handleViewRuns" @viewAblation="handleViewAblation" />
    
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <span>加载数据中...</span>
    </div>
    
    <template v-else>
      <div v-if="!latestRun" class="empty-state-container">
        <EmptyState 
          title="暂无运行数据" 
          description="尚未有实验运行记录，请先运行实验生成数据" 
        />
      </div>
      
      <div v-else class="grid-layout">
        <div class="grid-item full-width">
          <div class="section-header">
            <h2 class="section-title">核心指标</h2>
            <span class="section-subtitle">最新运行结果</span>
          </div>
          <KpiGrid :metrics="latestRun.metrics" />
        </div>
        
        <div class="grid-item half-width">
          <div class="section-header">
            <h2 class="section-title">完成率趋势</h2>
            <span class="section-subtitle">最近运行记录</span>
          </div>
          <RunTrendChart 
            :x-data="runDates" 
            :series="completionRateSeries" 
            type="line" 
            :height="280"
          />
        </div>
        
        <div class="grid-item half-width">
          <div class="section-header">
            <h2 class="section-title">能耗趋势</h2>
            <span class="section-subtitle">总能耗变化</span>
          </div>
          <RunTrendChart 
            :x-data="runDates" 
            :series="energySeries" 
            type="area" 
            :height="280"
          />
        </div>
        
        <div class="grid-item full-width">
          <div class="section-header">
            <h2 class="section-title">策略洞察</h2>
            <span class="section-subtitle">完成率 vs 能耗分布</span>
          </div>
          <div class="insight-section">
            <ScatterInsightChart :data="scatterData" />
            <div class="insight-summary">
              <p>{{ insightSummary }}</p>
            </div>
          </div>
        </div>
        
        <div class="grid-item full-width">
          <div class="section-header">
            <h2 class="section-title">最近运行</h2>
            <button class="view-all-btn" @click="handleViewRuns">查看全部</button>
          </div>
          <RunList :runs="runs.slice(0, 5)" @select="handleRunSelect" />
        </div>
        
        <div class="grid-item full-width">
          <div class="section-header">
            <h2 class="section-title">实验产物预览</h2>
            <span class="section-subtitle">轨迹与状态可视化</span>
          </div>
          <PlotGallery />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.overview-page {
  padding-bottom: 32px;
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

.grid-layout {
  display: grid;
  gap: 24px;
}

.grid-item {
  &.full-width { grid-column: 1 / -1; }
  &.half-width { grid-column: span 1; }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: #1e3a5f;
  margin: 0;
}

.section-subtitle {
  font-size: 14px;
  color: #8898aa;
  margin-left: 8px;
}

.view-all-btn {
  background: #0a4d68;
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.view-all-btn:hover {
  background: #088395;
}

.insight-section {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}

.insight-summary {
  margin-top: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #e8f5f8 0%, #f0f7ff 100%);
  border-radius: 12px;
  border-left: 4px solid #088395;
}

.insight-summary p {
  margin: 0;
  font-size: 14px;
  color: #1e3a5f;
  line-height: 1.6;
}

@media (min-width: 768px) {
  .grid-layout {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1200px) {
  .grid-layout {
    grid-template-columns: repeat(3, 1fr);
  }
  .grid-item.half-width {
    grid-column: span 1;
  }
}
</style>