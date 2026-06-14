<script setup lang="ts">
import { FolderOpened } from '@element-plus/icons-vue'

defineProps<{
  title: string
  description: string
  icon?: string
}>()
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon">
      <FolderOpened v-if="!icon" class="icon" />
      <span v-else>{{ icon }}</span>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-description">{{ description }}</p>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.icon {
  font-size: 40px;
  color: #2e7d32;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #1e3a5f;
  margin-bottom: 8px;
}

.empty-description {
  font-size: 14px;
  color: #8898aa;
  max-width: 300px;
}
</style>