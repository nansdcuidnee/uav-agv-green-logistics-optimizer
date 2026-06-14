<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

interface ChartData {
  labels: string[]
  values: number[]
  stds?: number[]
}

const props = defineProps<{
  data: ChartData
  showError?: boolean
  isDelta?: boolean
  height?: number
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chartInstance || props.data.labels.length === 0) return
  
  const colors = props.isDelta 
    ? props.data.values.map(v => v >= 0 ? '#c62828' : '#2e7d32')
    : ['#0a4d68', '#088395', '#05bfdb', '#f99500', '#e65100', '#7b1fa2', '#525f7f', '#8898aa']
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const data = params[0]
        const label = data.name
        const value = data.value.toFixed(2)
        if (props.showError && props.data.stds) {
          const idx = data.dataIndex
          const std = props.data.stds[idx]?.toFixed(2) || '0'
          return `<div style="padding: 8px;">
            <div><strong>${label}</strong></div>
            <div>值: ${value} (±${std})</div>
          </div>`
        }
        return `<div style="padding: 8px;">
          <div><strong>${label}</strong></div>
          <div>值: ${value}</div>
        </div>`
      }
    },
    grid: {
      left: '3%',
      right: '3%',
      top: '10%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: props.data.labels,
      axisLabel: {
        color: '#8898aa',
        rotate: props.data.labels.length > 5 ? 30 : 0,
        fontSize: 12
      },
      axisLine: {
        lineStyle: { color: '#e6ebf1' }
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#8898aa'
      },
      axisLine: {
        lineStyle: { color: '#e6ebf1' }
      },
      splitLine: {
        lineStyle: { color: '#f0f0f0' }
      }
    },
    series: [{
      type: 'bar',
      data: props.data.values.map((v, i) => ({
        value: v,
        itemStyle: {
          color: colors[i % colors.length],
          borderRadius: [4, 4, 0, 0]
        }
      })),
      barWidth: '50%'
    }]
  }
  
  
  
  chartInstance.setOption(option)
}

function handleResize() {
  chartInstance?.resize()
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})

watch(() => props.data, () => {
  updateChart()
}, { deep: true })
</script>

<template>
  <div ref="chartRef" class="ablation-bar-chart" :style="{ height: `${height || 280}px` }"></div>
</template>

<style scoped>
.ablation-bar-chart {
  width: 100%;
}
</style>