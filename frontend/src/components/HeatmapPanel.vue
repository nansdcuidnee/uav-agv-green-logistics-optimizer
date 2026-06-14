<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SceneVariantPair } from '../types'

const props = defineProps<{
  data: SceneVariantPair[]
}>()

const selectedMetric = ref<'completion_rate' | 'total_energy'>('completion_rate')

const scenes = computed(() => {
  return [...new Set(props.data.map(d => d.scene_name))]
})

const variants = computed(() => {
  return [...new Set(props.data.map(d => d.variant_name))]
})

const heatmapValues = computed(() => {
  return scenes.value.map(scene => {
    return variants.value.map(variant => {
      const item = props.data.find(d => d.scene_name === scene && d.variant_name === variant)
      return item ? item[selectedMetric.value] : null
    })
  })
})

function getCellColor(value: number | null): string {
  if (value === null) return '#e6ebf1'
  if (selectedMetric.value === 'completion_rate') {
    const intensity = value
    return `rgb(${Math.round(46 - intensity * 30)}, ${Math.round(125 - intensity * 60)}, ${Math.round(50 + intensity * 180)})`
  } else {
    const maxVal = Math.max(...props.data.map(d => d.total_energy))
    const minVal = Math.min(...props.data.map(d => d.total_energy))
    const normalized = (value - minVal) / (maxVal - minVal)
    return `rgb(${Math.round(230 - normalized * 180)}, ${Math.round(235 - normalized * 150)}, ${Math.round(240 - normalized * 50)})`
  }
}

function formatValue(value: number | null): string {
  if (value === null) return '-'
  if (selectedMetric.value === 'completion_rate') {
    return `${(value * 100).toFixed(1)}%`
  }
  return value.toFixed(1)
}
</script>

<template>
  <div class="heatmap-panel">
    <div class="heatmap-header">
      <div class="metric-selector">
        <label class="selector-label">选择指标</label>
        <div class="selector-buttons">
          <button 
            :class="['selector-btn', selectedMetric === 'completion_rate' ? 'active' : '']"
            @click="selectedMetric = 'completion_rate'"
          >
            完成率
          </button>
          <button 
            :class="['selector-btn', selectedMetric === 'total_energy' ? 'active' : '']"
            @click="selectedMetric = 'total_energy'"
          >
            能耗
          </button>
        </div>
      </div>
    </div>
    <div class="heatmap-container">
      <div class="heatmap">
        <div class="heatmap-row">
          <div class="heatmap-header-cell"></div>
          <div v-for="variant in variants" :key="variant" class="heatmap-header-cell">
            {{ variant }}
          </div>
        </div>
        <div v-for="(row, sceneIdx) in heatmapValues" :key="sceneIdx" class="heatmap-row">
          <div class="heatmap-header-cell scene-label">{{ scenes[sceneIdx] }}</div>
          <div 
            v-for="(value, variantIdx) in row" 
            :key="variantIdx"
            class="heatmap-cell"
            :style="{ background: getCellColor(value) }"
          >
            {{ formatValue(value) }}
          </div>
        </div>
      </div>
      <div class="heatmap-legend">
        <div class="legend-label">低</div>
        <div class="legend-gradient" :class="selectedMetric"></div>
        <div class="legend-label">高</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.heatmap-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}

.heatmap-header {
  margin-bottom: 16px;
}

.metric-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selector-label {
  font-size: 13px;
  font-weight: 500;
  color: #525f7f;
}

.selector-buttons {
  display: flex;
  gap: 8px;
}

.selector-btn {
  padding: 6px 16px;
  border: 1px solid #e6ebf1;
  border-radius: 6px;
  background: white;
  font-size: 13px;
  color: #525f7f;
  cursor: pointer;
  transition: all 0.3s ease;
}

.selector-btn.active {
  background: #0a4d68;
  color: white;
  border-color: #0a4d68;
}

.heatmap-container {
  overflow-x: auto;
}

.heatmap {
  display: flex;
  flex-direction: column;
  min-width: max-content;
}

.heatmap-row {
  display: flex;
}

.heatmap-header-cell {
  padding: 12px 16px;
  background: #f8fafc;
  font-size: 13px;
  font-weight: 600;
  color: #525f7f;
  min-width: 120px;
  text-align: center;
  border-right: 1px solid #e6ebf1;
  border-bottom: 1px solid #e6ebf1;
}

.heatmap-header-cell:last-child {
  border-right: none;
}

.heatmap-row:last-child .heatmap-header-cell,
.heatmap-row:last-child .heatmap-cell {
  border-bottom: none;
}

.scene-label {
  background: #e8f5f8;
  color: #0a4d68;
  text-align: left;
}

.heatmap-cell {
  padding: 12px 16px;
  min-width: 100px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: #1e3a5f;
  border-right: 1px solid #e6ebf1;
  border-bottom: 1px solid #e6ebf1;
}

.heatmap-cell:last-child {
  border-right: none;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

.legend-label {
  font-size: 12px;
  color: #8898aa;
}

.legend-gradient {
  width: 200px;
  height: 16px;
  border-radius: 8px;
}

.legend-gradient.completion_rate {
  background: linear-gradient(to right, rgb(46, 125, 50), rgb(16, 65, 200));
}

.legend-gradient.total_energy {
  background: linear-gradient(to right, rgb(230, 235, 240), rgb(50, 85, 190));
}
</style>