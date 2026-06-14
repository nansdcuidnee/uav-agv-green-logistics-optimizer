<script setup lang="ts">
import type { Metrics } from '../types'
import { ArrowUp, Clock } from '@element-plus/icons-vue'

defineProps<{
  metrics: Metrics
}>()

function formatNumber(value: number, decimals: number = 2): string {
  return value.toFixed(decimals)
}
</script>

<template>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-icon completion">
        <span class="icon-emoji">🎯</span>
      </div>
      <div class="kpi-content">
        <span class="kpi-label">任务完成率</span>
        <span class="kpi-value">{{ formatNumber(metrics.completion_rate * 100, 1) }}%</span>
      </div>
      <div class="kpi-trend up">
        <ArrowUp />
      </div>
    </div>

    <div class="kpi-card">
      <div class="kpi-icon energy">
        <span class="icon-emoji">⚡</span>
      </div>
      <div class="kpi-content">
        <span class="kpi-label">总能耗</span>
        <span class="kpi-value">{{ formatNumber(metrics.total_energy) }}</span>
      </div>
      <div class="kpi-unit">Wh</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-icon time">
        <Clock class="icon" />
      </div>
      <div class="kpi-content">
        <span class="kpi-label">平均配送时间</span>
        <span class="kpi-value">{{ formatNumber(metrics.avg_delivery_time) }}</span>
      </div>
      <div class="kpi-unit">步</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-icon distance">
        <span class="icon-emoji">📍</span>
      </div>
      <div class="kpi-content">
        <span class="kpi-label">总距离</span>
        <span class="kpi-value">{{ formatNumber(metrics.total_distance) }}</span>
      </div>
      <div class="kpi-unit">m</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-icon charging">
        <span class="icon-emoji">🔋</span>
      </div>
      <div class="kpi-content">
        <span class="kpi-label">充电次数</span>
        <span class="kpi-value">{{ metrics.charging_count }}</span>
      </div>
      <div class="kpi-unit">次</div>
    </div>

    <div class="kpi-card">
      <div class="kpi-icon relay">
        <span class="icon-emoji">🔄</span>
      </div>
      <div class="kpi-content">
        <span class="kpi-label">中继/直送</span>
        <span class="kpi-value">{{ metrics.relay_count }} / {{ metrics.direct_count }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.kpi-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
  transition: all 0.3s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(10, 77, 104, 0.12);
}

.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-icon.completion { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); }
.kpi-icon.completion .icon { color: #2e7d32; }

.kpi-icon.energy { background: linear-gradient(135deg, #fff3e0, #ffe0b2); }
.kpi-icon.energy .icon { color: #e65100; }

.kpi-icon.time { background: linear-gradient(135deg, #e3f2fd, #bbdefb); }
.kpi-icon.time .icon { color: #1565c0; }

.kpi-icon.distance { background: linear-gradient(135deg, #f3e5f5, #e1bee7); }
.kpi-icon.distance .icon { color: #7b1fa2; }

.kpi-icon.charging { background: linear-gradient(135deg, #e0f2f1, #b2dfdb); }
.kpi-icon.charging .icon { color: #00695c; }

.kpi-icon.relay { background: linear-gradient(135deg, #fce4ec, #f8bbd9); }
.kpi-icon.relay .icon { color: #c2185b; }

.icon {
  font-size: 24px;
}

.kpi-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font-size: 13px;
  color: #8898aa;
  margin-bottom: 4px;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: #1e3a5f;
}

.kpi-trend {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-trend.up {
  background: #e8f5e9;
  color: #2e7d32;
}

.kpi-unit {
  font-size: 12px;
  color: #8898aa;
  padding: 4px 8px;
  background: #f0f2f5;
  border-radius: 4px;
}
</style>