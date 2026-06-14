<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

interface ScatterDataPoint {
  x: number
  y: number
  strategy: string
}

const props = defineProps<{
  data: ScatterDataPoint[]
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const strategyColors: Record<string, string> = {
  'alns_unified': '#0a4d68',
  'baseline_direct': '#f99500',
  'relay_coop': '#088395',
  'energy_priority': '#e65100',
  'default': '#525f7f'
}

function getColor(strategy: string): string {
  return strategyColors[strategy] || strategyColors['default']
}

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chartInstance || props.data.length === 0) return
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `<div style="padding: 8px;">
          <div><strong>${params.data.strategy}</strong></div>
          <div>完成率: ${params.data.x.toFixed(1)}%</div>
          <div>能耗: ${params.data.y.toFixed(1)} Wh</div>
        </div>`
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      top: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'value',
      name: '完成率 (%)',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%',
        color: '#8898aa'
      },
      axisLine: {
        lineStyle: { color: '#e6ebf1' }
      },
      splitLine: {
        lineStyle: { color: '#f0f0f0' }
      }
    },
    yAxis: {
      type: 'value',
      name: '能耗 (Wh)',
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
      type: 'scatter',
      data: props.data.map(d => ({
        value: [d.x, d.y],
        strategy: d.strategy,
        itemStyle: {
          color: getColor(d.strategy),
          shadowBlur: 10,
          shadowColor: 'rgba(10, 77, 104, 0.3)'
        },
        symbolSize: 12
      })),
      emphasis: {
        itemStyle: {
          shadowBlur: 20,
          shadowColor: 'rgba(10, 77, 104, 0.5)'
        }
      }
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
  <div ref="chartRef" class="scatter-chart"></div>
</template>

<style scoped>
.scatter-chart {
  width: 100%;
  height: 280px;
}
</style>