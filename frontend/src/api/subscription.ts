import axios from 'axios'
import type { Subscription, SubscriptionListResponse, SubscriptionResponse, SubscriptionUpdate, JobResponse } from '@/types'

const API_BASE = '/api'

export async function createSubscription(
  file: File,
  name: string | null,
  scheduleHour: number,
  scheduleMinute: number,
  enabled: boolean
): Promise<SubscriptionResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (name) formData.append('name', name)
  formData.append('schedule_hour', String(scheduleHour))
  formData.append('schedule_minute', String(scheduleMinute))
  formData.append('enabled', String(enabled))

  const resp = await axios.post(`${API_BASE}/subscriptions`, formData)
  return resp.data
}

export async function listSubscriptions(): Promise<Subscription[]> {
  const resp = await axios.get<SubscriptionListResponse>(`${API_BASE}/subscriptions`)
  return resp.data.subscriptions
}

export async function getSubscription(subId: string): Promise<Subscription> {
  const resp = await axios.get<Subscription>(`${API_BASE}/subscriptions/${subId}`)
  return resp.data
}

export async function updateSubscription(subId: string, update: SubscriptionUpdate): Promise<Subscription> {
  const resp = await axios.patch<Subscription>(`${API_BASE}/subscriptions/${subId}`, update)
  return resp.data
}

export async function deleteSubscription(subId: string): Promise<void> {
  await axios.delete(`${API_BASE}/subscriptions/${subId}`)
}

export async function runSubscriptionNow(subId: string): Promise<JobResponse> {
  const resp = await axios.post<JobResponse>(`${API_BASE}/subscriptions/${subId}/run`)
  return resp.data
}