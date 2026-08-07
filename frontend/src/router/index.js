import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/faces', name: 'faces', component: () => import('../views/FaceRegister.vue') },
  { path: '/history', name: 'history', component: () => import('../views/History.vue') },
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
