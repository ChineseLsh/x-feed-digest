import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Subscriptions from '../views/Subscriptions.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/subscriptions',
      name: 'subscriptions',
      component: Subscriptions
    }
  ]
})

export default router