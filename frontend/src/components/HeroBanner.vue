<script setup lang="ts">
import { ArrowRight } from '@element-plus/icons-vue'

defineEmits<{
  (e: 'viewRuns'): void
  (e: 'viewAblation'): void
}>()
</script>

<template>
  <div class="hero-banner">
    <div class="hero-content">
      <div class="hero-text">
        <div class="hero-badge">
          <span class="badge-icon">⚡</span>
          <span>协同优化系统</span>
        </div>
        <h1 class="hero-title">UAV-AGV 协同绿色配送</h1>
        <p class="hero-desc">
          基于自适应大规模邻域搜索的无人机-地面机器人协同配送系统，实现高效、节能的智能物流配送
        </p>
        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-value">100%</span>
            <span class="stat-label">任务完成率</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">265</span>
            <span class="stat-label">总能耗</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">5</span>
            <span class="stat-label">完成任务</span>
          </div>
        </div>
        <div class="hero-actions">
          <button class="btn-primary" @click="$emit('viewRuns')">
            查看最新运行
            <ArrowRight class="btn-icon" />
          </button>
          <button class="btn-secondary" @click="$emit('viewAblation')">
            查看消融对比
          </button>
        </div>
      </div>
      <div class="hero-visual">
        <div class="visual-card">
          <div class="card-header">
            <div class="status-dot active"></div>
            <span>系统状态</span>
          </div>
          <div class="system-status">
            <div class="status-item">
              <span class="status-icon uav">✈</span>
              <span>UAV 在线</span>
            </div>
            <div class="status-item">
              <span class="status-icon agv">🚛</span>
              <span>AGV 在线</span>
            </div>
            <div class="status-item">
              <span class="status-icon task">📦</span>
              <span>任务进行中</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="hero-wave"></div>
  </div>
</template>

<style scoped>
.hero-banner {
  background: linear-gradient(135deg, #0a4d68 0%, #088395 50%, #05bfdb 100%);
  border-radius: 20px;
  padding: 48px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}

.hero-wave {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 120'%3E%3Cpath fill='%23f0f7ff' fill-opacity='1' d='M0,64L48,69.3C96,75,192,85,288,80C384,75,480,53,576,48C672,43,768,53,864,64C960,75,1056,85,1152,80C1248,75,1344,53,1392,42.7L1440,32L1440,120L1392,120C1344,120,1248,120,1152,120C1056,120,960,120,864,120C768,120,672,120,576,120C480,120,384,120,288,120C192,120,96,120,48,120L0,120Z'%3E%3C/path%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-size: cover;
}

.hero-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 32px;
  position: relative;
  z-index: 1;
}

.hero-text {
  color: white;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.2);
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 16px;
}

.badge-icon {
  font-size: 14px;
}

.hero-title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 12px;
  line-height: 1.2;
}

.hero-desc {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.6;
  margin-bottom: 24px;
}

.hero-stats {
  display: flex;
  gap: 48px;
  margin-bottom: 24px;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #05bfdb;
}

.stat-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 4px;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  background: white;
  color: #0a4d68;
  padding: 12px 24px;
  border-radius: 10px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(255, 255, 255, 0.3);
}

.btn-icon {
  font-size: 16px;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  padding: 12px 24px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.25);
}

.hero-visual {
  display: flex;
  align-items: center;
  justify-content: center;
}

.visual-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 24px;
  width: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ccc;
}

.status-dot.active {
  background: #00ff88;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.system-status {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}

.status-icon {
  font-size: 20px;
}

.status-icon.uav { color: #05bfdb; }
.status-icon.agv { color: #f99500; }
.status-icon.task { color: #00ff88; }

@media (max-width: 900px) {
  .hero-content {
    grid-template-columns: 1fr;
    text-align: center;
  }
  
  .hero-stats {
    justify-content: center;
  }
  
  .hero-actions {
    justify-content: center;
  }
  
  .hero-title {
    font-size: 28px;
  }
}
</style>