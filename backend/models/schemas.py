from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class JobCreate(BaseModel):
    batch_size: Optional[int] = None


class BatchStatus(BaseModel):
    index: int
    status: str
    attempts: int
    max_attempts: int
    error: Optional[str] = None
    started_at: Optional[int] = None
    finished_at: Optional[int] = None
    last_attempt_at: Optional[int] = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    created_at: int
    batch_size: int
    total_users: Optional[int] = None
    completed_batches: Optional[int] = None
    total_batches: Optional[int] = None
    failed_batches: Optional[int] = None
    succeeded_batches: Optional[int] = None
    error: Optional[str] = None
    batches: Optional[List[BatchStatus]] = None


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobListResponse(BaseModel):
    jobs: List[JobStatus]


class SummaryResponse(BaseModel):
    summary_text: str


# ─── Subscription Models ───


class SubscriptionCreate(BaseModel):
    name: Optional[str] = None
    schedule_hour: int = 8
    schedule_minute: int = 0
    enabled: bool = True


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    schedule_hour: Optional[int] = None
    schedule_minute: Optional[int] = None
    enabled: Optional[bool] = None


class SubscriptionStatus(BaseModel):
    id: str
    name: Optional[str] = None
    csv_filename: str
    schedule_hour: int
    schedule_minute: int
    enabled: bool
    created_at: int
    updated_at: int
    last_run: Optional[int] = None
    next_run: Optional[int] = None
    last_job_id: Optional[str] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    total_users: Optional[int] = None


class SubscriptionResponse(BaseModel):
    id: str
    status: str


class SubscriptionListResponse(BaseModel):
    subscriptions: List[SubscriptionStatus]