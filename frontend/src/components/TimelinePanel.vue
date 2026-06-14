<script setup lang="ts">
import type { CoordinationEvent } from '../types'

defineProps<{
  events: CoordinationEvent[] | null
}>()

const eventTypeColors: Record<string, string> = {
  'TASK_ASSIGNED': '#0a4d68',
  'TASK_START': '#088395',
  'TASK_COMPLETE': '#2e7d32',
  'CHARGING_START': '#f99500',
  'CHARGING_END': '#e65100',
  'RELAY_TRANSFER': '#7b1fa2',
  'FALLBACK': '#c62828',
  'REPLAN': '#525f7f'
}

const eventTypeLabels: Record<string, string> = {
  'TASK_ASSIGNED': '任务分配',
  'TASK_START': '任务开始',
  'TASK_COMPLETE': '任务完成',
  'CHARGING_START': '充电开始',
  'CHARGING_END': '充电结束',
  'RELAY_TRANSFER': '中继交接',
  'FALLBACK': '降级处理',
  'REPLAN': '重规划'
}

function getEventTypeColor(type: string): string {
  return eventTypeColors[type] || '#525f7f'
}

function getEventTypeLabel(type: string): string {
  return eventTypeLabels[type] || type
}

function formatTime(time: number): string {
  return time.toFixed(1)
}
</script>

<template>
  <div class="timeline-panel">
    <div v-if="!events || events.length === 0" class="empty-timeline">
      <span>暂无协同事件数据</span>
    </div>
    <div v-else class="timeline">
      <div 
        v-for="(event, index) in events.slice(0, 50)" 
        :key="index" 
        class="timeline-item"
      >
        <div class="timeline-marker" :style="{ background: getEventTypeColor(event.event_type) }"></div>
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="event-type" :style="{ color: getEventTypeColor(event.event_type) }">
              {{ getEventTypeLabel(event.event_type) }}
            </span>
            <span class="event-time">Step {{ event.step }} ({{ formatTime(event.sim_time) }}s)</span>
          </div>
          <div class="timeline-body">
            <p class="event-desc">{{ event.description }}</p>
            <div class="event-meta">
              <span v-if="event.task_id" class="meta-item">任务: {{ event.task_id }}</span>
              <span v-if="event.uav_id" class="meta-item">UAV: {{ event.uav_id }}</span>
              <span v-if="event.agv_id" class="meta-item">AGV: {{ event.agv_id }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-if="events.length > 50" class="timeline-more">
        <span>还有 {{ events.length - 50 }} 条事件...</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-panel {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}

.empty-timeline {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #8898aa;
}

.timeline {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.timeline-item:last-child {
  border-bottom: none;
}

.timeline-marker {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 4px;
  flex-shrink: 0;
}

.timeline-content {
  flex: 1;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.event-type {
  font-size: 14px;
  font-weight: 600;
}

.event-time {
  font-size: 12px;
  color: #8898aa;
}

.timeline-body {
  margin-top: 4px;
}

.event-desc {
  font-size: 13px;
  color: #1e3a5f;
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.event-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 12px;
  color: #8898aa;
  background: #f8fafc;
  padding: 2px 8px;
  border-radius: 4px;
}

.timeline-more {
  text-align: center;
  padding: 12px;
  color: #8898aa;
  font-size: 13px;
}
</style>