import { createRouter, createWebHashHistory } from 'vue-router'
import Overview from '../views/Overview.vue'
import RunDetail from '../views/RunDetail.vue'
import Ablation from '../views/Ablation.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'Overview',
      component: Overview
    },
    {
      path: '/runs',
      name: 'RunDetail',
      component: RunDetail
    },
    {
      path: '/ablation',
      name: 'Ablation',
      component: Ablation
    }
  ]
})

export default router