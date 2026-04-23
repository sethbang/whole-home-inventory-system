"""Vision auto-fill router (v3.1 Part C).

``POST /api/vision/identify`` accepts 1..VISION_MAX_IMAGES_PER_REQUEST
image uploads + optional JSON hints. Behavior:

* Feature flag off → 503.
* ARQ worker inactive → run synchronously and return the full
  ``VisionResult`` inline (same discriminated-union pattern backups
  use in v3.0).
* Worker active → enqueue ``vision_identify`` with base64-encoded
  bytes, return 202 + ``JobReference``. Frontend polls
  ``GET /api/jobs/{id}``.
"""

import base64
import json
import logging
from typing import List, Optional, Union

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..security import get_current_active_user
from ..services.images import validate_image_bytes
from ..settings import settings
from ..vision import VisionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["vision"])


@router.post(
    "/identify",
    response_model=Union[schemas.JobReference, schemas.VisionResult],
)
async def identify_item(
    request: Request,
    files: List[UploadFile] = File(..., description="1..VISION_MAX_IMAGES_PER_REQUEST photos"),
    hints: Optional[str] = Form(
        None, description="Optional JSON blob with user-supplied hints (brand, model, etc.)."
    ),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if not settings.VISION_ENABLED:
        raise HTTPException(
            status_code=503, detail="Vision auto-fill is disabled on this deployment."
        )
    if not files:
        raise HTTPException(status_code=400, detail="At least one image is required.")
    if len(files) > settings.VISION_MAX_IMAGES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Too many images: got {len(files)}, "
                f"max is {settings.VISION_MAX_IMAGES_PER_REQUEST}."
            ),
        )

    # Upfront validation in the request thread — no point enqueueing a
    # worker job to discover the first upload is corrupt.
    image_bytes: List[bytes] = []
    for upload in files:
        data = await upload.read()
        validate_image_bytes(data)  # 400/413 on bad bytes or oversized
        image_bytes.append(data)

    hints_obj: Optional[dict] = None
    if hints:
        try:
            hints_obj = json.loads(hints)
            if not isinstance(hints_obj, dict):
                raise ValueError("hints must be a JSON object")
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid hints JSON: {exc}"
            )

    pool = getattr(request.app.state, "arq", None)
    if pool is not None:
        try:
            job = await pool.enqueue_job(
                "vision_identify",
                user_id=str(current_user.id),
                images_b64=[base64.b64encode(b).decode("ascii") for b in image_bytes],
                hints=hints_obj,
            )
        except Exception:
            logger.exception("vision_identify enqueue failed; falling back to sync")
        else:
            if job is not None:
                return schemas.JobReference(job_id=job.job_id)

    # Sync fallback — runs the vision pipeline on the request thread.
    # Acceptable for dev; production should enable the worker profile.
    # Use the async variant directly (awaited in this handler's event
    # loop); service.identify() wraps it in asyncio.run() which would
    # blow up here since we're already inside a running loop.
    service = VisionService(db=db, user=current_user)
    return await service.identify_async(image_bytes, hints=hints_obj)
