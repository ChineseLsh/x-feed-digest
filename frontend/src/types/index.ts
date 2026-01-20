export type BatchStatusType = 'pending' | 'running' | 'succeeded' | 'failed'

export interface Batch {
  index: number
  status: BatchStatusType
  attempts: number
  max_attempts: number
  error?: string
  started_at?: number
  finished_at?: number
  last_attempt_at?: number
}

export interface Job {
  job_id: string
  status: 'queued' | 'running' | 'summarizing' | 'done' | 'failed'
  created_at: number
  batch_size: number
  total_users?: number
  completed_batches?: number
  total_batches?: number
  failed_batches?: number
  succeeded_batches?: number
  error?: string
  batches?: Batch[]
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

// ─── Subscription Types ───

export interface Subscription {
  id: string
  name: string | null
  csv_filename: string
  schedule_hour: number
  schedule_minute: number
  enabled: boolean
  created_at: number
  updated_at: number
  last_run: number | null
  next_run: number | null
  last_job_id: string | null
  last_status: 'queued' | 'running' | 'summarizing' | 'done' | 'failed' | null
  last_error: string | null
  total_users: number | null
}

export interface SubscriptionListResponse {
  subscriptions: Subscription[]
}

export interface SubscriptionResponse {
  id: string
  status: string
}

export interface SubscriptionUpdate {
  name?: string
  schedule_hour?: number
  schedule_minute?: number
  enabled?: boolean
}