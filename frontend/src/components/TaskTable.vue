<script setup lang="ts">
import type { TaskRecord } from '../types'

defineProps<{
  tasks: TaskRecord[] | null
}>()

const deliveryTypeLabels: Record<string, string> = {
  'direct': '直送',
  'relay': '中继',
  'agv_only': 'AGV'
}

function getDeliveryTypeLabel(type: string): string {
  return deliveryTypeLabels[type] || type
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'completed': return '#2e7d32'
    case 'failed': return '#c62828'
    case 'in_progress': return '#f99500'
    default: return '#525f7f'
  }
}

function formatTime(time: number | null): string {
  return time === null ? '-' : time.toFixed(1)
}
</script>

<template>
  <div class="task-table-container">
    <div v-if="!tasks || tasks.length === 0" class="empty-table">
      <span>暂无任务数据</span>
    </div>
    <div v-else class="task-table-wrapper">
      <table class="task-table">
        <thead>
          <tr>
            <th>任务ID</th>
            <th>状态</th>
            <th>配送类型</th>
            <th>开始时间</th>
            <th>结束时间</th>
            <th>能耗</th>
            <th>距离</th>
            <th>中继等待</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.task_id">
            <td class="task-id">{{ task.task_id }}</td>
            <td>
              <span class="status-badge" :style="{ background: getStatusColor(task.status) }">
                {{ task.status }}
              </span>
            </td>
            <td>{{ getDeliveryTypeLabel(task.delivery_type) }}</td>
            <td>{{ formatTime(task.start_time) }}</td>
            <td>{{ formatTime(task.end_time) }}</td>
            <td>{{ task.energy_consumed.toFixed(1) }}</td>
            <td>{{ task.distance.toFixed(1) }}</td>
            <td>{{ task.wait_time_at_relay !== null ? task.wait_time_at_relay.toFixed(1) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.task-table-container {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
  overflow-x: auto;
}

.empty-table {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #8898aa;
}

.task-table-wrapper {
  overflow-x: auto;
}

.task-table {
  width: 100%;
  border-collapse: collapse;
}

.task-table th,
.task-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e6ebf1;
}

.task-table th {
  font-weight: 600;
  color: #525f7f;
  font-size: 13px;
  background: #f8fafc;
}

.task-table td {
  font-size: 14px;
  color: #1e3a5f;
}

.task-id {
  font-weight: 600;
  color: #0a4d68;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  color: white;
  font-size: 12px;
  font-weight: 500;
}
</style>