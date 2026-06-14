<script setup lang="ts">import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import AblationBarChart from '../components/AblationBarChart.vue';
import HeatmapPanel from '../components/HeatmapPanel.vue';
import EmptyState from '../components/EmptyState.vue';
import { getAblationSummary, getVariantAggregates, getDeltaComparison, getScenes } from '../services/ablationRepository';
import type { VariantAggregate, DeltaItem, SceneVariantPair } from '../types';
const router = useRouter();
const loading = ref(true);
const selectedScene = ref('');
const scenes = ref<string[]>([]);
const aggregates = ref<VariantAggregate[]>([]);
const deltaData = ref<DeltaItem[]>([]);
const heatmapData = ref<SceneVariantPair[]>([]);
const sortKey = ref<'completion_rate_mean' | 'total_energy_mean' | 'avg_delivery_time_mean'>('completion_rate_mean');
const sortOrder = ref<'asc' | 'desc'>('desc');
const sortedAggregates = computed(() => {
 const key = sortKey.value;
 return [...aggregates.value].sort((a, b) => {
 const diff = a[key] - b[key];
 return sortOrder.value === 'desc' ? -diff : diff;
 });
});
const completionRateData = computed(() => ({
 labels: aggregates.value.map(a => a.variant_name),
 values: aggregates.value.map(a => a.completion_rate_mean * 100),
 stds: aggregates.value.map(a => a.completion_rate_std * 100)
}));
const energyData = computed(() => ({
 labels: aggregates.value.map(a => a.variant_name),
 values: aggregates.value.map(a => a.total_energy_mean),
 stds: aggregates.value.map(a => a.total_energy_std)
}));
const deliveryTimeData = computed(() => ({
 labels: aggregates.value.map(a => a.variant_name),
 values: aggregates.value.map(a => a.avg_delivery_time_mean),
 stds: aggregates.value.map(a => a.avg_delivery_time_std)
}));
const deltaCompletionData = computed(() => ({
 labels: deltaData.value.map(d => d.variant_name),
 values: deltaData.value.map(d => d.completion_rate_delta * 100)
}));
const deltaEnergyData = computed(() => ({
 labels: deltaData.value.map(d => d.variant_name),
 values: deltaData.value.map(d => d.total_energy_delta)
}));
function handleSort(key: 'completion_rate_mean' | 'total_energy_mean' | 'avg_delivery_time_mean') {
 if (sortKey.value === key) {
 sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc';
 }
 else {
 sortKey.value = key;
 sortOrder.value = key === 'completion_rate_mean' ? 'desc' : 'asc';
 }
}
function goBack() {
 router.push('/');
}
async function loadData() {
 loading.value = true;
 const [sc, agg, delta, heatmap] = await Promise.all([
 getScenes(),
 getVariantAggregates(),
 getDeltaComparison(),
 getAblationSummary()
 ]);
 scenes.value = sc || [];
 aggregates.value = agg || [];
 deltaData.value = delta || [];
 heatmapData.value = heatmap || [];
 if (scenes.value.length > 0) {
 selectedScene.value = scenes.value[0];
 }
 loading.value = false;
}
onMounted(() => {
 loadData();
});
</script>

<template>
  <div class="ablation-page">
    <div class="page-header">
      <button class="back-btn" @click="goBack">
        <svg class="back-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 18l-6-6 6-6" />
        </svg>
        返回
      </button>
      <h1 class="page-title">消融实验对比</h1>
    </div>

    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <span>加载数据中...</span>
    </div>

    <template v-else>
      <div v-if="aggregates.length === 0" class="empty-state-container">
        <EmptyState 
          title="暂无消融实验数据" 
          description="尚未有消融实验记录，请先运行消融实验生成数据" 
        />
      </div>

      <div v-else class="ablation-content">
        <div class="selector-row">
          <div class="scene-selector">
            <label class="selector-label">选择场景</label>
            <select v-model="selectedScene" class="scene-select">
              <option v-for="scene in scenes" :key="scene" :value="scene">{{ scene }}</option>
            </select>
          </div>
        </div>

        <div class="variant-overview">
          <div class="section-header">
            <h2 class="section-title">Variant 总览</h2>
            <span class="section-subtitle">共 {{ aggregates.length }} 种变体</span>
          </div>
          <div class="variant-cards">
            <div v-for="variant in aggregates" :key="variant.variant_name" class="variant-card">
              <div class="variant-header">
                <span class="variant-name">{{ variant.variant_name }}</span>
                <span class="variant-count">{{ variant.num_runs }} runs</span>
              </div>
              <div class="variant-stats">
                <div class="stat">
                  <span class="stat-value">{{ (variant.completion_rate_mean * 100).toFixed(1) }}%</span>
                  <span class="stat-label">完成率</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ variant.total_energy_mean.toFixed(1) }}</span>
                  <span class="stat-label">能耗 (Wh)</span>
                </div>
                <div class="stat">
                  <span class="stat-value">{{ variant.avg_delivery_time_mean.toFixed(1) }}</span>
                  <span class="stat-label">配送时间</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="charts-section">
          <div class="section-header">
            <h2 class="section-title">指标对比</h2>
          </div>
          <div class="charts-grid">
            <div class="chart-card">
              <div class="chart-title">完成率对比</div>
              <AblationBarChart :data="completionRateData" :show-error="true" :height="280" />
            </div>
            <div class="chart-card">
              <div class="chart-title">总能耗对比</div>
              <AblationBarChart :data="energyData" :show-error="true" :height="280" />
            </div>
            <div class="chart-card">
              <div class="chart-title">平均配送时间</div>
              <AblationBarChart :data="deliveryTimeData" :show-error="true" :height="280" />
            </div>
          </div>
        </div>

        <div class="delta-section">
          <div class="section-header">
            <h2 class="section-title">Baseline Delta 对比</h2>
            <span class="section-subtitle">相对于 unified_full 的变化</span>
          </div>
          <div class="delta-charts">
            <div class="delta-chart">
              <div class="delta-label">完成率变化 (%)</div>
              <AblationBarChart :data="deltaCompletionData" :show-error="false" :is-delta="true" :height="200" />
            </div>
            <div class="delta-chart">
              <div class="delta-label">能耗变化 (Wh)</div>
              <AblationBarChart :data="deltaEnergyData" :show-error="false" :is-delta="true" :height="200" />
            </div>
          </div>
        </div>

        <div class="heatmap-section">
          <div class="section-header">
            <h2 class="section-title">Scene × Variant 热力图</h2>
          </div>
          <HeatmapPanel :data="heatmapData" />
        </div>

        <div class="table-section">
          <div class="section-header">
            <h2 class="section-title">明细数据</h2>
          </div>
          <div class="data-table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Variant</th>
                  <th @click="handleSort('completion_rate_mean')" class="sortable">
                    完成率(%)
                    <span class="sort-icon">{{ sortKey === 'completion_rate_mean' ? (sortOrder === 'desc' ? '↑' : '↓') : '' }}</span>
                  </th>
                  <th>Std</th>
                  <th @click="handleSort('total_energy_mean')" class="sortable">
                    能耗(Wh)
                    <span class="sort-icon">{{ sortKey === 'total_energy_mean' ? (sortOrder === 'desc' ? '↑' : '↓') : '' }}</span>
                  </th>
                  <th>Std</th>
                  <th @click="handleSort('avg_delivery_time_mean')" class="sortable">
                    配送时间
                    <span class="sort-icon">{{ sortKey === 'avg_delivery_time_mean' ? (sortOrder === 'desc' ? '↑' : '↓') : '' }}</span>
                  </th>
                  <th>Std</th>
                  <th>Run Count</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in sortedAggregates" :key="row.variant_name">
                  <td class="variant-cell">{{ row.variant_name }}</td>
                  <td>{{ (row.completion_rate_mean * 100).toFixed(2) }}</td>
                  <td>{{ (row.completion_rate_std * 100).toFixed(2) }}</td>
                  <td>{{ row.total_energy_mean.toFixed(2) }}</td>
                  <td>{{ row.total_energy_std.toFixed(2) }}</td>
                  <td>{{ row.avg_delivery_time_mean.toFixed(2) }}</td>
                  <td>{{ row.avg_delivery_time_std.toFixed(2) }}</td>
                  <td>{{ row.num_runs }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ablation-page {
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

.ablation-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.selector-row {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.scene-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selector-label {
  font-size: 14px;
  font-weight: 500;
  color: #525f7f;
}

.scene-select {
  padding: 10px 16px;
  border: 1px solid #e6ebf1;
  border-radius: 8px;
  background: white;
  font-size: 14px;
  color: #1e3a5f;
  min-width: 200px;
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

.variant-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.variant-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
  transition: all 0.3s ease;
}

.variant-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(10, 77, 104, 0.12);
}

.variant-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.variant-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e3a5f;
}

.variant-count {
  font-size: 12px;
  color: #8898aa;
  background: #f0f7ff;
  padding: 4px 8px;
  border-radius: 10px;
}

.variant-stats {
  display: flex;
  gap: 16px;
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #0a4d68;
}

.stat-label {
  font-size: 12px;
  color: #8898aa;
  margin-top: 4px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.chart-card {
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

.delta-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.delta-chart {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}

.delta-label {
  font-size: 14px;
  font-weight: 500;
  color: #525f7f;
  margin-bottom: 12px;
}

.data-table-container {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e6ebf1;
}

.data-table th {
  font-weight: 600;
  color: #525f7f;
  font-size: 13px;
}

.data-table td {
  font-size: 14px;
  color: #1e3a5f;
}

.data-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.data-table th.sortable:hover {
  background: #f0f7ff;
}

.sort-icon {
  margin-left: 4px;
  font-size: 12px;
  color: #8898aa;
}

.variant-cell {
  font-weight: 600;
  color: #0a4d68;
}
</style>