import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Job } from '@/types'
import { createJob, getJobStatus, getJobSummary, getDownloadUrl, listJobs } from '@/api/job'

export const useJobStore = defineStore('job', () => {
  const currentJob = ref<Job | null>(null)
  const summary = ref<string>('')
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pollingInterval = ref<number | null>(null)
  const jobHistory = ref<Job[]>([])
  const historyLoading = ref(false)

  const isProcessing = computed(() => {
    if (!currentJob.value) return false
    return ['queued', 'running', 'summarizing'].includes(currentJob.value.status)
  })

  const isDone = computed(() => currentJob.value?.status === 'done')
  const isFailed = computed(() => currentJob.value?.status === 'failed')

  const progressPercent = computed(() => {
    if (!currentJob.value) return 0
    const { completed_batches, total_batches, status } = currentJob.value
    if (status === 'done') return 100
    if (status === 'summarizing') return 95
    if (!total_batches || total_batches === 0) return 0
    return Math.round(((completed_batches || 0) / total_batches) * 90)
  })

  const progressText = computed(() => {
    if (!currentJob.value) return ''
    const { status, completed_batches, total_batches } = currentJob.value
    if (status === 'queued') return '排队中...'
    if (status === 'running') return `获取推文中 (${completed_batches || 0}/${total_batches || 0} 批次)`
    if (status === 'summarizing') return '正在生成摘要...'
    if (status === 'done') return '处理完成'
    if (status === 'failed') return '处理失败'
    return ''
  })

  async function submitJob(file: File, batchSize?: number) {
    loading.value = true
    error.value = null
    summary.value = ''

    try {
      const resp = await createJob(file, batchSize)
      currentJob.value = {
        job_id: resp.job_id,
        status: 'queued',
        created_at: Date.now() / 1000,
        batch_size: batchSize || 10
      }
      startPolling()
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || '上传失败'
      loading.value = false
    }
  }

  function startPolling() {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
    }
    pollingInterval.value = window.setInterval(pollStatus, 2000)
  }

  async function pollStatus() {
    if (!currentJob.value) return

    try {
      const status = await getJobStatus(currentJob.value.job_id)
      currentJob.value = status

      if (status.status === 'done') {
        stopPolling()
        await fetchSummary()
        loading.value = false
      } else if (status.status === 'failed') {
        stopPolling()
        error.value = status.error || '处理失败'
        loading.value = false
      }
    } catch (e: any) {
      error.value = e.message || '获取状态失败'
    }
  }

  function stopPolling() {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
  }

  async function fetchSummary() {
    if (!currentJob.value) return
    try {
      summary.value = await getJobSummary(currentJob.value.job_id)
    } catch (e: any) {
      error.value = e.message || '获取摘要失败'
    }
  }

  function getDownloadLink(): string {
    if (!currentJob.value) return ''
    return getDownloadUrl(currentJob.value.job_id)
  }

  function reset() {
    stopPolling()
    currentJob.value = null
    summary.value = ''
    loading.value = false
    error.value = null
  }

  async function fetchHistory() {
    historyLoading.value = true
    try {
      jobHistory.value = await listJobs()
    } catch (e: any) {
      console.error('Failed to fetch job history:', e)
    } finally {
      historyLoading.value = false
    }
  }

  async function viewHistoryJob(jobId: string) {
    try {
      currentJob.value = await getJobStatus(jobId)
      if (currentJob.value.status === 'done') {
        summary.value = await getJobSummary(jobId)
      }
    } catch (e: any) {
      error.value = e.message || '加载历史记录失败'
    }
  }

  return {
    currentJob,
    summary,
    loading,
    error,
    jobHistory,
    historyLoading,
    isProcessing,
    isDone,
    isFailed,
    progressPercent,
    progressText,
    submitJob,
    getDownloadLink,
    reset,
    fetchHistory,
    viewHistoryJob
  }
})