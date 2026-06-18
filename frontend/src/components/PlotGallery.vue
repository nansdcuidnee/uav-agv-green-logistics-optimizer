<script setup lang="ts">
import { ref } from 'vue'

const MOCK_BASE = `${import.meta.env.BASE_URL}mock-results`
const BASE_PATH = `${MOCK_BASE}/runs/demo_relay_demo/20260614_112314/plots`

const images = ref([
  { name: 'trajectory_map', title: '轨迹图', description: '配送轨迹可视化', src: `${BASE_PATH}/trajectory_map.png` },
  { name: 'task_progress', title: '任务进度', description: '任务完成进度', src: `${BASE_PATH}/task_progress.png` },
  { name: 'battery_status', title: '电池状态', description: '电量变化曲线', src: `${BASE_PATH}/battery_status.png` },
  { name: 'energy_curve', title: '能耗曲线', description: '能耗变化趋势', src: `${BASE_PATH}/energy_curve.png` },
  { name: 'coordination_events', title: '协同事件', description: '事件时间线', src: `${BASE_PATH}/coordination_events.png` }
])

const selectedImage = ref<string | null>(null)
const imageLoadError = ref<Set<string>>(new Set())

function openPreview(name: string) {
  selectedImage.value = name
}

function closePreview() {
  selectedImage.value = null
}

function handleImageError(name: string) {
  imageLoadError.value.add(name)
}
</script>

<template>
  <div class="plot-gallery">
    <div class="gallery-grid">
      <div 
        v-for="img in images" 
        :key="img.name" 
        class="gallery-item"
        @click="openPreview(img.name)"
      >
        <div class="gallery-thumb">
          <template v-if="imageLoadError.has(img.name)">
            <div class="thumb-placeholder">
              <svg class="placeholder-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
            </div>
          </template>
          <img 
            v-else 
            :src="img.src" 
            :alt="img.title" 
            class="thumb-image"
            @error="handleImageError(img.name)"
          />
          <div class="gallery-overlay">
            <span class="overlay-text">点击查看</span>
          </div>
        </div>
        <div class="gallery-info">
          <span class="gallery-title">{{ img.title }}</span>
          <span class="gallery-desc">{{ img.description }}</span>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="selectedImage" class="preview-modal" @click="closePreview">
        <div class="modal-content" @click.stop>
          <button class="close-btn" @click="closePreview">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <div class="preview-image">
            <template v-if="imageLoadError.has(selectedImage)">
              <svg class="preview-placeholder" viewBox="0 0 800 600">
                <rect width="800" height="600" fill="#f8fafc"/>
                <text x="400" y="300" text-anchor="middle" fill="#8898aa" font-size="18">
                  {{ selectedImage }}.png
                </text>
                <text x="400" y="330" text-anchor="middle" fill="#b8c5d6" font-size="14">
                  图片加载失败
                </text>
              </svg>
            </template>
            <img 
              v-else 
              :src="images.find(i => i.name === selectedImage)?.src" 
              :alt="selectedImage" 
              class="preview-img"
              @error="handleImageError(selectedImage)"
            />
          </div>
          <div class="preview-info">
            <span class="preview-title">{{ images.find(i => i.name === selectedImage)?.title }}</span>
            <span class="preview-desc">{{ images.find(i => i.name === selectedImage)?.description }}</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.plot-gallery {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(10, 77, 104, 0.08);
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.gallery-item {
  cursor: pointer;
  transition: all 0.3s ease;
}

.gallery-item:hover {
  transform: translateY(-4px);
}

.gallery-thumb {
  position: relative;
  aspect-ratio: 4/3;
  border-radius: 8px;
  overflow: hidden;
  background: #f8fafc;
  margin-bottom: 12px;
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0a4d68;
}

.placeholder-icon {
  width: 48px;
  height: 48px;
  opacity: 0.6;
}

.thumb-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.gallery-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(10, 77, 104, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.gallery-item:hover .gallery-overlay {
  opacity: 1;
}

.overlay-text {
  color: white;
  font-size: 14px;
  font-weight: 500;
}

.gallery-info {
  display: flex;
  flex-direction: column;
}

.gallery-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e3a5f;
}

.gallery-desc {
  font-size: 12px;
  color: #8898aa;
  margin-top: 4px;
}

.preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-content {
  background: white;
  border-radius: 16px;
  padding: 24px;
  max-width: 90vw;
  max-height: 90vh;
  overflow: auto;
  position: relative;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(0, 0, 0, 0.1);
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #525f7f;
  cursor: pointer;
  transition: all 0.3s ease;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.2);
}

.close-btn svg {
  width: 16px;
  height: 16px;
}

.preview-image {
  margin-bottom: 16px;
}

.preview-placeholder {
  max-width: 100%;
  border-radius: 8px;
}

.preview-img {
  max-width: 100%;
  max-height: 70vh;
  border-radius: 8px;
  object-fit: contain;
}

.preview-info {
  display: flex;
  flex-direction: column;
}

.preview-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e3a5f;
}

.preview-desc {
  font-size: 13px;
  color: #8898aa;
  margin-top: 4px;
}
</style>