<script setup lang="ts">
import { ArrowUp, ArrowDown, Minus } from '@element-plus/icons-vue'

defineProps<{
  title: string
  value: string | number
  unit?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  icon?: string
  color?: string
}>()

function getTrendIcon(trend?: 'up' | 'down' | 'neutral') {
  switch (trend) {
    case 'up': return ArrowUp
    case 'down': return ArrowDown
    default: return Minus
  }
}

function getTrendClass(trend?: 'up' | 'down' | 'neutral') {
  switch (trend) {
    case 'up': return 'trend-up'
    case 'down': return 'trend-down'
    default: return 'trend-neutral'
  }
}
</script>

<template>
  <div class="metric-card" :style="{ '--card-color': color || '#0a4d68' }">
    <div class="metric-icon" :style="{ background: `linear-gradient(135deg, ${color || '#0a4d68'}20, ${color || '#088395'}10)` }">
      <span class="icon-text">{{ icon || '📊' }}</span>
    </div>
    <div class="metric-content">
      <span class="metric-label">{{ title }}</span>
      <div class="metric-value-row">
        <span class="metric-value">{{ value }}</span>
        <span v-if="unit" class="metric-unit">{{ unit }}</span>
      </div>
      <div v-if="trend" class="metric-trend" :class="getTrendClass(trend)">
        <component :is="getTrendIcon(trend)" class="trend-icon" />
        <span>{{ trendValue }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.metric-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
  transition: all 0.3s ease;
  border-left: 4px solid var(--card-color);
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(10, 77, 104, 0.12);
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-text {
  font-size: 24px;
}

.metric-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 13px;
  color: #8898aa;
  margin-bottom: 4px;
}

.metric-value-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--card-color);
}

.metric-unit {
  font-size: 14px;
  color: #8898aa;
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 13px;
}

.trend-up {
  color: #2e7d32;
}

.trend-down {
  color: #c62828;
}

.trend-neutral {
  color: #8898aa;
}

.trend-icon {
  font-size: 14px;
}
</style>