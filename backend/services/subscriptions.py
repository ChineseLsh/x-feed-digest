"""Subscription scheduler service using APScheduler."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.core.storage import (
    get_subscription,
    get_subscription_csv_path,
    list_subscriptions,
    save_subscription,
)
from backend.services.csv_parser import extract_users
from backend.services.job_runner import run_job

logger = logging.getLogger(__name__)


class SubscriptionScheduler:
    """Manages scheduled subscription jobs using APScheduler."""

    def __init__(self, app_cfg: Dict[str, Any], providers_cfg: Dict[str, Any]):
        self.app_cfg = app_cfg
        self.providers_cfg = providers_cfg
        
        scheduler_cfg = app_cfg.get("scheduler", {})
        timezone = scheduler_cfg.get("timezone", "Asia/Shanghai")
        
        self.scheduler = AsyncIOScheduler(timezone=timezone)
        self._job_config = {
            "coalesce": scheduler_cfg.get("coalesce", True),
            "misfire_grace_time": scheduler_cfg.get("misfire_grace_s", 300),
        }

    def start(self) -> None:
        """Start the scheduler and load all enabled subscriptions."""
        self.scheduler.start()
        logger.info("Subscription scheduler started")
        
        # Load all enabled subscriptions
        subs = list_subscriptions(self.app_cfg)
        for sub in subs:
            if sub.get("enabled", True):
                self._schedule_subscription(sub)

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Subscription scheduler stopped")

    def _schedule_subscription(self, sub: Dict[str, Any]) -> None:
        """Schedule a subscription job."""
        sub_id = sub["id"]
        hour = sub.get("schedule_hour", 8)
        minute = sub.get("schedule_minute", 0)
        
        job_id = f"sub_{sub_id}"
        
        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Add new job
        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            self._run_subscription,
            trigger=trigger,
            id=job_id,
            args=[sub_id],
            replace_existing=True,
            **self._job_config,
        )
        
        # Update next_run in subscription
        next_run_time = trigger.get_next_fire_time(None, datetime.now(self.scheduler.timezone))
        if next_run_time:
            sub["next_run"] = int(next_run_time.timestamp())
            save_subscription(self.app_cfg, sub_id, sub)
        
        logger.info(f"Scheduled subscription {sub_id} at {hour:02d}:{minute:02d}")

    def _unschedule_subscription(self, sub_id: str) -> None:
        """Remove a subscription from the scheduler."""
        job_id = f"sub_{sub_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled subscription {sub_id}")

    def _run_subscription(self, sub_id: str) -> None:
        """Run a subscription job (called by scheduler)."""
        logger.info(f"Running scheduled subscription: {sub_id}")
        self.run_now(sub_id)

    def run_now(self, sub_id: str) -> Optional[str]:
        """
        Manually trigger a subscription run.
        
        Returns:
            job_id if successful, None if subscription not found
        """
        sub = get_subscription(self.app_cfg, sub_id)
        if not sub:
            logger.warning(f"Subscription not found: {sub_id}")
            return None
        
        csv_path = get_subscription_csv_path(self.app_cfg, sub_id)
        if not csv_path:
            logger.error(f"CSV file not found for subscription: {sub_id}")
            sub["last_status"] = "failed"
            sub["last_error"] = "CSV file not found"
            sub["last_run"] = int(time.time())
            save_subscription(self.app_cfg, sub_id, sub)
            return None
        
        # Extract users
        try:
            handles, _ = extract_users(csv_path)
            total_users = len(handles)
        except Exception as e:
            logger.error(f"Failed to parse CSV for subscription {sub_id}: {e}")
            sub["last_status"] = "failed"
            sub["last_error"] = f"CSV parse error: {e}"
            sub["last_run"] = int(time.time())
            save_subscription(self.app_cfg, sub_id, sub)
            return None
        
        # Create job
        job_id = str(uuid.uuid4())
        batching_cfg = self.app_cfg.get("batching", {})
        batch_size = int(batching_cfg.get("default_batch_size", 10))
        
        # Update subscription status
        sub["last_run"] = int(time.time())
        sub["last_job_id"] = job_id
        sub["last_status"] = "running"
        sub["last_error"] = None
        save_subscription(self.app_cfg, sub_id, sub)
        
        def on_status_update(status: dict):
            sub["last_status"] = status.get("status")
            if status.get("error"):
                sub["last_error"] = status["error"]
            save_subscription(self.app_cfg, sub_id, sub)
        
        try:
            run_job(
                job_id=job_id,
                upload_path=csv_path,
                app_cfg=self.app_cfg,
                providers_cfg=self.providers_cfg,
                batch_size=batch_size,
                total_users=total_users,
                on_status_update=on_status_update,
            )
            logger.info(f"Subscription {sub_id} job {job_id} completed successfully")
        except Exception as e:
            logger.error(f"Subscription {sub_id} job {job_id} failed: {e}")
        
        return job_id

    def schedule_subscription(self, sub_id: str) -> None:
        """Add or update a subscription in the scheduler."""
        sub = get_subscription(self.app_cfg, sub_id)
        if sub and sub.get("enabled", True):
            self._schedule_subscription(sub)
        else:
            self._unschedule_subscription(sub_id)

    def get_next_run(self, sub_id: str) -> Optional[int]:
        """Get the next scheduled run time for a subscription."""
        job_id = f"sub_{sub_id}"
        job = self.scheduler.get_job(job_id)
        if job and job.next_run_time:
            return int(job.next_run_time.timestamp())
        return None