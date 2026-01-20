import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Subscription, SubscriptionUpdate } from '@/types'
import {
  createSubscription as apiCreate,
  listSubscriptions as apiList,
  updateSubscription as apiUpdate,
  deleteSubscription as apiDelete,
  runSubscriptionNow as apiRun,
} from '@/api/subscription'

export const useSubscriptionStore = defineStore('subscription', () => {
  const subscriptions = ref<Subscription[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadSubscriptions() {
    loading.value = true
    error.value = null
    try {
      subscriptions.value = await apiList()
    } catch (e: any) {
      error.value = e.message || 'Failed to load subscriptions'
    } finally {
      loading.value = false
    }
  }

  async function createSubscription(
    file: File,
    name: string | null,
    scheduleHour: number,
    scheduleMinute: number,
    enabled: boolean
  ): Promise<string | null> {
    loading.value = true
    error.value = null
    try {
      const resp = await apiCreate(file, name, scheduleHour, scheduleMinute, enabled)
      await loadSubscriptions()
      return resp.id
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to create subscription'
      return null
    } finally {
      loading.value = false
    }
  }

  async function updateSubscription(subId: string, update: SubscriptionUpdate): Promise<boolean> {
    error.value = null
    try {
      await apiUpdate(subId, update)
      await loadSubscriptions()
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to update subscription'
      return false
    }
  }

  async function deleteSubscription(subId: string): Promise<boolean> {
    error.value = null
    try {
      await apiDelete(subId)
      subscriptions.value = subscriptions.value.filter((s) => s.id !== subId)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to delete subscription'
      return false
    }
  }

  async function runNow(subId: string): Promise<string | null> {
    error.value = null
    try {
      const resp = await apiRun(subId)
      await loadSubscriptions()
      return resp.job_id
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to run subscription'
      return null
    }
  }

  return {
    subscriptions,
    loading,
    error,
    loadSubscriptions,
    createSubscription,
    updateSubscription,
    deleteSubscription,
    runNow,
  }
})