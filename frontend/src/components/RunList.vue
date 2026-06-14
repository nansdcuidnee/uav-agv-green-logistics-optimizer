<script setup lang="ts">
import type { RunInfo } from '../types'
import { Clock } from '@element-plus/icons-vue'

defineProps<{
  runs: RunInfo[]
}>()

defineEmits<{
  (e: 'select', run: RunInfo): void
}>()

function formatTime(timestamp: string): string {
  const date = new Date(timestamp.replace('_', ' '))
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getCompletionColor(rate: number): string {
  if (rate >= 0.9) return '#2e7d32'
  if (rate >= 0.7) return '#f99500'
  return '#f53f3f'
}
</script>

<template>
  <div class="run-list">
    <div class="list-header">
      <h3 class="list-title">最近运行记录</h3>
      <span class="list-count">{{ runs.length }} 条记录</span>
    </div>
    
    <div class="list-content">
      <div
        v-for="run in runs"
        :key="run.full_path"
        class="run-card"
        @click="$emit('select', run)"
      >
        <div class="run-info">
          <div class="run-header">
            <span class="run-name">{{ run.experiment_name }}</span>
            <span :style="{ color: getCompletionColor(run.metrics.completion_rate) }" class="completion-badge">
              {{ (run.metrics.completion_rate * 100).toFixed(0) }}%
            </span>
          </div>
          <div class="run-meta">
            <span class="meta-item">
              <Clock class="meta-icon" />
              {{ formatTime(run.timestamp) }}
            </span>
            <span class="meta-item">
              <span class="meta-icon">⚡</span>
              {{ run.strategy }}
            </span>
          </div>
        </div>
        
        <div class="run-stats">
          <div class="stat">
            <span class="stat-value">{{ run.metrics.total_energy.toFixed(1) }}</span>
            <span class="stat-label">能耗</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ run.metrics.completed_tasks }}/{{ run.metrics.total_tasks }}</span>
            <span class="stat-label">任务</span>
          </div>
        </div>
        
        <div class="run-action">
          <span class="action-icon">✓</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.run-list {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e3a5f;
  margin: 0;
}

.list-count {
  font-size: 13px;
  color: #8898aa;
}

.list-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.run-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.run-card:hover {
  background: #f0f7ff;
  border-color: #088395;
  transform: translateX(4px);
}

.run-info {
  flex: 1;
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.run-name {
  font-weight: 600;
  color: #1e3a5f;
}

.completion-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  background: rgba(46, 125, 50, 0.1);
  border-radius: 10px;
}

.run-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #8898aa;
}

.meta-icon {
  font-size: 12px;
}

.run-stats {
  display: flex;
  gap: 24px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1e3a5f;
}

.stat-label {
  font-size: 11px;
  color: #8898aa;
}

.run-action {
  width: 36px;
  height: 36px;
  background: #e8f5e9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-icon {
  color: #2e7d32;
}
</style>