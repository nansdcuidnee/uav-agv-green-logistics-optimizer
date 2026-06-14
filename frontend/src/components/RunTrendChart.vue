<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(defineProps<{
  title?: string
  xData: string[]
  series: { name: string; data: number[]; color: string }[]
  type?: 'line' | 'area'
}>(), {
  title: ''
})

const chartRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chartInstance) return
  
  const option: echarts.EChartsOption = {
    title: {
      text: props.title,
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 14,
        fontWeight: 600,
        color: '#1e3a5f'
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e4e8f0',
      borderWidth: 1,
      textStyle: {
        color: '#1e3a5f'
      },
      formatter: (params: unknown) => {
        const paramArray = params as { axisValue: string; marker: string; seriesName: string; value: number }[]
        let result = `<div style="font-weight: 600; margin-bottom: 8px;">${paramArray[0].axisValue}</div>`
        paramArray.forEach(p => {
          result += `<div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">${p.marker}${p.seriesName}: <strong>${p.value.toFixed(1)}</strong></div>`
        })
        return result
      }
    },
    legend: {
      bottom: 10,
      textStyle: {
        color: '#5a6a85'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '20%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.xData,
      axisLine: {
        lineStyle: {
          color: '#e4e8f0'
        }
      },
      axisLabel: {
        color: '#5a6a85',
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      splitLine: {
        lineStyle: {
          color: '#f0f2f5',
          type: 'dashed'
        }
      },
      axisLabel: {
        color: '#5a6a85',
        fontSize: 11
      }
    },
    series: props.series.map(s => ({
      name: s.name,
      type: props.type === 'area' ? 'line' : 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 3,
        color: s.color
      },
      itemStyle: {
        color: s.color
      },
      areaStyle: props.type === 'area' ? {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: s.color + '40' },
          { offset: 1, color: s.color + '05' }
        ])
      } : undefined,
      data: s.data
    }))
  }
  
  chartInstance.setOption(option)
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chartInstance?.resize())
})

watch(() => props, updateChart, { deep: true })
</script>

<template>
  <div class="chart-container">
    <div ref="chartRef" class="chart"></div>
  </div>
</template>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 250px;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 250px;
}
</style>