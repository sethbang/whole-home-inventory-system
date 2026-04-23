"""Background job status endpoint (v3.0).

``GET /api/jobs/{job_id}`` returns the lifecycle state of any ARQ job
belonging to the current user. Job ownership is enforced by looking at
the job's stored kwargs — every enqueuer in the service layer is
required to pass ``user_id`` so this guard has something to check.

When the ARQ pool isn't configured (no Redis / default dev stack) the
endpoint returns 503 because there is nothing to look up.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from arq.jobs import DeserializationError, Job, JobStatus as ArqJobStatus
from fastapi import APIRouter, Depends, HTTPException, Request

from .. import models, schemas
from ..security import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# Map ARQ's native lifecycle states onto WHIS's trimmed-down set. We
# collapse the two "not started yet" states (``deferred``/``queued``)
# into one ``queued`` state since the frontend doesn't need to
# distinguish them. ``not_found`` is returned when no job with the
# given id exists in Redis.
_STATUS_MAP: dict[ArqJobStatus, schemas.JobStatus] = {
    ArqJobStatus.deferred: schemas.JobStatus.queued,
    ArqJobStatus.queued: schemas.JobStatus.queued,
    ArqJobStatus.in_progress: schemas.JobStatus.running,
    ArqJobStatus.complete: schemas.JobStatus.complete,
    ArqJobStatus.not_found: schemas.JobStatus.not_found,
}


def _unix_to_dt(value: float | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


@router.get("/{job_id}", response_model=schemas.JobDetail)
async def get_job(
    job_id: str,
    request: Request,
    current_user: models.User = Depends(get_current_active_user),
) -> schemas.JobDetail:
    pool = getattr(request.app.state, "arq", None)
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Background job queue is not configured on this deployment. "
                "Set REDIS_URL and run the worker profile to enable it."
            ),
        )

    job = Job(job_id, pool)
    status = await job.status()
    if status == ArqJobStatus.not_found:
        raise HTTPException(status_code=404, detail="Job not found")

    info = await job.info()

    # Every WHIS-enqueued job stores the owning user in kwargs["user_id"].
    # Refuse to leak status for jobs that belong to someone else.
    job_user_id = (info.kwargs or {}).get("user_id") if info else None
    if job_user_id and str(job_user_id) != str(current_user.id):
        # Same 404 as non-existent jobs — don't reveal existence.
        raise HTTPException(status_code=404, detail="Job not found")

    result: dict | None = None
    error: str | None = None
    finished_at: float | None = None

    if status == ArqJobStatus.complete:
        try:
            # ``result_info()`` is the zero-raise variant that returns both
            # success and failure payloads without re-raising the worker
            # exception on the request path.
            result_info = await job.result_info()
        except DeserializationError as exc:
            # ARQ couldn't unpickle the stored result — usually because
            # the task raised an exception type whose __init__ doesn't
            # round-trip through pickle (Starlette's HTTPException is the
            # canonical offender; the task layer now catches it before
            # re-raise, but other exception types could trip this in
            # the future). Surface as a generic failure rather than a
            # 500 on the polling endpoint.
            logger.warning("job %s result_info deserialization failed: %s", job_id, exc)
            result_info = None
            error = "Job completed with an un-deserializable result; check worker logs."

        if result_info is not None:
            finished_at = result_info.finish_time.timestamp() if result_info.finish_time else None
            if result_info.success:
                payload = result_info.result
                # Tasks that catch HTTPException internally return a
                # ``{ok: False, status_code, error}`` envelope so they
                # don't poison the pickle. Promote that into the same
                # ``failed`` shape callers expect from a real exception.
                if (
                    isinstance(payload, dict)
                    and payload.get("ok") is False
                    and "status_code" in payload
                ):
                    error = f"{payload['status_code']}: {payload.get('error') or 'Job failed'}"
                else:
                    result = payload if isinstance(payload, dict) else {"value": payload}
            else:
                error = str(result_info.result)

    normalized_status = (
        schemas.JobStatus.failed
        if status == ArqJobStatus.complete and error is not None
        else _STATUS_MAP.get(status, schemas.JobStatus.queued)
    )

    return schemas.JobDetail(
        job_id=job_id,
        status=normalized_status,
        result=result,
        error=error,
        queued_at=_unix_to_dt(info.enqueue_time.timestamp()) if info and info.enqueue_time else None,
        started_at=_unix_to_dt(info.start_time.timestamp()) if info and getattr(info, "start_time", None) else None,
        finished_at=_unix_to_dt(finished_at),
    )
