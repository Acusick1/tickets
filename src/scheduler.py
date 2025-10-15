"""Scheduler for periodic price checking."""
import logging
import random
from typing import Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .alert_manager import AlertManager

logger = logging.getLogger(__name__)


class AlertScheduler:
    """Scheduler for periodic alert processing."""

    def __init__(
        self,
        alert_manager: AlertManager,
        interval_minutes: int = 15,
        jitter_minutes: int = 2,
    ):
        """Initialize the scheduler.

        Args:
            alert_manager: AlertManager instance
            interval_minutes: Interval between checks in minutes
            jitter_minutes: Random jitter to add/subtract from interval
        """
        self.alert_manager = alert_manager
        self.interval_minutes = interval_minutes
        self.jitter_minutes = jitter_minutes
        self.scheduler = BackgroundScheduler()
        self.job_id = "process_alerts"

    def _process_with_jitter(self):
        """Process alerts with random jitter."""
        # Add random delay (jitter) to avoid detection patterns
        if self.jitter_minutes > 0:
            jitter_seconds = random.uniform(0, self.jitter_minutes * 60)
            logger.info(f"Adding jitter: {jitter_seconds:.2f} seconds")
            import time

            time.sleep(jitter_seconds)

        # Process all alerts
        stats = self.alert_manager.process_all_alerts()
        logger.info(f"Alert processing completed: {stats}")

    def start(self):
        """Start the scheduler."""
        logger.info(
            f"Starting scheduler: checking every {self.interval_minutes} minutes "
            f"(±{self.jitter_minutes} min jitter)"
        )

        # Add job with interval trigger
        self.scheduler.add_job(
            self._process_with_jitter,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id=self.job_id,
            name="Process price alerts",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Scheduler started")

        # Run immediately on start without jitter (fail fast)
        logger.info("Running initial alert check...")
        stats = self.alert_manager.process_all_alerts()
        logger.info(f"Initial alert check completed: {stats}")

    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping scheduler...")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    def get_status(self) -> Dict:
        """Get scheduler status.

        Returns:
            Dictionary with scheduler status information
        """
        if not self.scheduler.running:
            return {"running": False, "jobs": []}

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": str(job.next_run_time),
                }
            )

        return {"running": True, "jobs": jobs}
