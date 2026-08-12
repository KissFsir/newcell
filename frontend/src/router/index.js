import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/faces', name: 'faces', component: () => import('../views/FaceRegister.vue') },
  { path: '/reports', name: 'reports', component: () => import('../views/Reports.vue') },
  { path: '/settings', name: 'settings', component: () => import('../views/Settings.vue') },
  { path: '/history', redirect: '/settings' }, // 兼容旧链接
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
