export interface Job {
  job_id: string
  status: 'queued' | 'running' | 'summarizing' | 'done' | 'failed'
  created_at: number
  batch_size: number
  total_users?: number
  completed_batches?: number
  total_batches?: number
  error?: string
}

export interface JobListResponse {
  jobs: Job[]
}

export interface JobResponse {
  job_id: string
  status: string
}

export interface SummaryResponse {
  summary_text: string
}