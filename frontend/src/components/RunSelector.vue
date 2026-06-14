<script setup lang="ts">
import { ref, computed } from 'vue'
import type { RunInfo } from '../types'

const props = defineProps<{
  runs: RunInfo[]
  currentExp: string
  currentTs: string
}>()

const emit = defineEmits<{
  (e: 'select', run: RunInfo): void
}>()

const selectedExperiment = ref('')

const experiments = computed(() => {
  const exps = [...new Set(props.runs.map(r => r.experiment_name))]
  return exps
})

const timestamps = computed(() => {
  if (!selectedExperiment.value) return []
  return props.runs
    .filter(r => r.experiment_name === selectedExperiment.value)
    .map(r => r.timestamp)
})

const currentRun = computed(() => {
  return props.runs.find(r => 
    r.experiment_name === props.currentExp && r.timestamp === props.currentTs
  )
})

function handleExperimentChange(exp: string) {
  selectedExperiment.value = exp
  const run = props.runs.find(r => r.experiment_name === exp)
  if (run) {
    emit('select', run)
  }
}

function handleTimestampChange(ts: string) {
  const run = props.runs.find(r => 
    r.experiment_name === selectedExperiment.value && r.timestamp === ts
  )
  if (run) {
    emit('select', run)
  }
}

if (!selectedExperiment.value && experiments.value.length > 0) {
  selectedExperiment.value = props.currentExp || experiments.value[0]
}
</script>

<template>
  <div class="run-selector">
    <div class="selector-row">
      <div class="selector-item">
        <label class="selector-label">实验名称</label>
        <select 
          v-model="selectedExperiment" 
          @change="handleExperimentChange(selectedExperiment)"
          class="selector-input"
        >
          <option v-for="exp in experiments" :key="exp" :value="exp">{{ exp }}</option>
        </select>
      </div>
      <div class="selector-item">
        <label class="selector-label">运行时间</label>
        <select 
          :disabled="!selectedExperiment"
          @change="handleTimestampChange(($event.target as HTMLSelectElement).value)"
          class="selector-input"
        >
          <option v-for="ts in timestamps" :key="ts" :value="ts">
            {{ ts.slice(4, 6) }}/{{ ts.slice(6, 8) }} {{ ts.slice(8, 10) }}:{{ ts.slice(10, 12) }}
          </option>
        </select>
      </div>
    </div>
    <div v-if="currentRun" class="run-info">
      <div class="info-item">
        <span class="info-label">策略</span>
        <span class="info-value">{{ currentRun.strategy }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">场景</span>
        <span class="info-value">{{ currentRun.metrics.scenario_name }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">完成率</span>
        <span class="info-value highlight">{{ (currentRun.metrics.completion_rate * 100).toFixed(1) }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.run-selector {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}

.selector-row {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.selector-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selector-label {
  font-size: 13px;
  font-weight: 500;
  color: #525f7f;
}

.selector-input {
  padding: 10px 16px;
  border: 1px solid #e6ebf1;
  border-radius: 8px;
  background: white;
  font-size: 14px;
  color: #1e3a5f;
  min-width: 200px;
}

.selector-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.run-info {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e6ebf1;
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-label {
  font-size: 13px;
  color: #8898aa;
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: #1e3a5f;
}

.info-value.highlight {
  color: #0a4d68;
  font-weight: 600;
}
</style>