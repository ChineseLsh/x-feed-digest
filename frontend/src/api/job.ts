import axios from 'axios'
import type { Job, JobListResponse, JobResponse, SummaryResponse } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export async function createJob(file: File, batchSize?: number): Promise<JobResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (batchSize) {
    formData.append('batch_size', String(batchSize))
  }
  const resp = await api.post<JobResponse>('/jobs', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return resp.data
}

export async function listJobs(): Promise<Job[]> {
  const resp = await api.get<JobListResponse>('/jobs')
  return resp.data.jobs
}

export async function getJobStatus(jobId: string): Promise<Job> {
  const resp = await api.get<Job>(`/jobs/${jobId}`)
  return resp.data
}

export async function getJobSummary(jobId: string): Promise<string> {
  const resp = await api.get<SummaryResponse>(`/jobs/${jobId}/summary`)
  return resp.data.summary_text
}

export function getDownloadUrl(jobId: string): string {
  return `/api/jobs/${jobId}/download`
}