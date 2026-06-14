<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const isMobileMenuOpen = ref(false)

const navItems = [
  { path: '/', label: '总览', icon: '📊' },
  { path: '/runs', label: '运行详情', icon: '✈️' },
  { path: '/ablation', label: '消融实验', icon: '🚛' }
]

function isActive(path: string): boolean {
  return route.path === path
}

function navigate(path: string) {
  router.push(path)
  isMobileMenuOpen.value = false
}
</script>

<template>
  <nav class="navbar">
    <div class="navbar-container">
      <div class="navbar-brand" @click="navigate('/')">
        <div class="brand-icon">
          <span class="icon-emoji">✈️</span>
          <span class="icon-emoji truck">🚛</span>
        </div>
        <span class="brand-text">UAV-AGV 协同配送</span>
      </div>
      
      <div class="navbar-nav">
        <button
          v-for="item in navItems"
          :key="item.path"
          :class="['nav-item', { active: isActive(item.path) }]"
          @click="navigate(item.path)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>
      </div>

      <button class="mobile-menu-btn" @click="isMobileMenuOpen = !isMobileMenuOpen">
        <Menu v-if="!isMobileMenuOpen" />
        <span v-else class="close-icon">✕</span>
      </button>
    </div>

    <div v-if="isMobileMenuOpen" class="mobile-nav">
      <button
        v-for="item in navItems"
        :key="item.path"
        :class="['mobile-nav-item', { active: isActive(item.path) }]"
        @click="navigate(item.path)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  background: linear-gradient(135deg, #0a4d68 0%, #088395 100%);
  color: white;
  padding: 0 24px;
  box-shadow: 0 2px 12px rgba(10, 77, 104, 0.3);
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-container {
  max-width: 1400px;
  margin: 0 auto;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  font-weight: 600;
  font-size: 18px;
}

.brand-icon {
  position: relative;
  width: 36px;
  height: 36px;
}

.icon-emoji {
  position: absolute;
  font-size: 24px;
}

.icon-emoji.truck {
  font-size: 18px;
  top: 14px;
  left: 10px;
}

.brand-text {
  background: linear-gradient(135deg, #ffffff 0%, #e0f7fa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.navbar-nav {
  display: flex;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 8px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.nav-icon {
  font-size: 16px;
}

.mobile-menu-btn {
  display: none;
  background: transparent;
  border: none;
  color: white;
  font-size: 20px;
  cursor: pointer;
}

.mobile-nav {
  display: none;
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.mobile-nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  border-radius: 8px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.85);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.mobile-nav-item:hover,
.mobile-nav-item.active {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

@media (max-width: 768px) {
  .navbar-nav {
    display: none;
  }
  
  .mobile-menu-btn {
    display: block;
  }
  
  .mobile-nav {
    display: block;
  }
}
</style>