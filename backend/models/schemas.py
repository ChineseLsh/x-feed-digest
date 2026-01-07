from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class JobCreate(BaseModel):
    batch_size: Optional[int] = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    created_at: int
    batch_size: int
    total_users: Optional[int] = None
    completed_batches: Optional[int] = None
    total_batches: Optional[int] = None
    error: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobListResponse(BaseModel):
    jobs: List[JobStatus]


class SummaryResponse(BaseModel):
    summary_text: str