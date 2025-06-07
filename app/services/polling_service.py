from typing import Dict, Optional, Callable, Any
import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
import asyncio
import logging

logger = logging.getLogger(__name__)


class PollingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PollingJob(BaseModel):
    id: str
    status: PollingStatus
    message: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class PollingService:
    """Simple in-memory polling service for background tasks"""

    def __init__(self):
        self.jobs: Dict[str, PollingJob] = {}

    def create_polling_job(
        self, processor_fn: Callable, message: str = "Job created"
    ) -> PollingJob:
        """Create a new polling job"""
        job_id = str(uuid.uuid4())

        job = PollingJob(
            id=job_id,
            status=PollingStatus.PENDING,
            message=message,
            created_at=datetime.utcnow(),
        )

        self.jobs[job_id] = job

        # Start processing in background
        asyncio.create_task(self._process_job(job_id, processor_fn))

        logger.info(f"Created polling job {job_id}")
        return job

    def get_job(self, job_id: str) -> Optional[PollingJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        status: PollingStatus,
        message: str,
        result: Any = None,
        error: Optional[str] = None,
    ):
        """Update job status"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.status = status
            job.message = message

            if result is not None:
                job.result = result

            if error:
                job.error = error

            if status in [PollingStatus.COMPLETED, PollingStatus.FAILED]:
                job.completed_at = datetime.utcnow()

            logger.info(f"Updated job {job_id}: {status} - {message}")

    async def _process_job(self, job_id: str, processor_fn: Callable):
        """Process job in background"""
        try:
            self.update_job(job_id, PollingStatus.PROCESSING, "Processing...")

            # Execute the processor function
            result = await processor_fn()

            self.update_job(
                job_id,
                PollingStatus.COMPLETED,
                "Processing completed successfully",
                result=result,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job {job_id} failed: {error_msg}")

            self.update_job(
                job_id,
                PollingStatus.FAILED,
                f"Processing failed: {error_msg}",
                error=error_msg,
            )


# Global instance - safe since it's just a simple in-memory store
polling_service = PollingService()
