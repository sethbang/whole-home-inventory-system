"""Items router — thin HTTP shim over ``services.items.ItemService``.

The router is responsible for HTTP wiring: binding dependencies, validating
request shapes, translating between ``UploadFile`` / ``StreamingResponse``
and service calls, and enforcing that every endpoint requires auth. All
query building and ownership checks live in the service.

v2.2 also migrates this router away from the legacy optional-auth pattern
(``get_current_active_user_or_none`` + ``if not current_user: 401``) in
favor of the strict dependency. The only place that used to need the
optional flavor was the barcode endpoint, which v2.1 already fixed.
"""

from __future__ import annotations

import io
import json
import logging
import uuid
from typing import Any, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import database, models, schemas, security
from ..rate_limit import limiter
from ..services.items import ItemService

logger = logging.getLogger(__name__)


class BulkDeleteRequest(BaseModel):
    item_ids: List[uuid.UUID]


router = APIRouter(tags=["items"])


def _service(db: Session, user: models.User) -> ItemService:
    return ItemService(db=db, user=user)


@router.post("/items/", response_model=schemas.Item)
def create_item(
    item: schemas.ItemCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    return _service(db, current_user).create(item)


@router.get("/items", response_model=schemas.ItemList)
def list_items(
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    min_value: Optional[float] = Query(None),
    max_value: Optional[float] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_desc: Optional[bool] = Query(False),
    page: Optional[int] = Query(1),
    page_size: Optional[int] = Query(20),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    # Normalize empty query params to None so the Pydantic schema treats a
    # blank string the same as an unset value.
    query = None if query == "" else query
    category = None if category == "" else category
    location = None if location == "" else location
    sort_by = None if sort_by == "" else sort_by

    try:
        search_filter = schemas.SearchFilter(
            query=query,
            category=category,
            location=location,
            min_value=min_value,
            max_value=max_value,
            sort_by=sort_by,
            sort_desc=sort_desc,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        logger.warning("invalid search parameters: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid search parameters")

    items, total = _service(db, current_user).list(search_filter)
    return {
        "items": items,
        "total": total,
        "page": search_filter.page,
        "page_size": search_filter.page_size,
    }


@router.get("/items/export/data")
@limiter.limit("10/hour")
async def export_items(
    request: Request,  # required by slowapi
    format: str = Query(
        ..., description="Export format (csv or json)", pattern="^(csv|json)$"
    ),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> StreamingResponse:
    records = _service(db, current_user).export_records()

    if format == "csv":
        df = pd.DataFrame(records)
        if "custom_fields" in df.columns:
            df["custom_fields"] = df["custom_fields"].apply(
                lambda x: json.dumps(x) if x else None
            )
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        return StreamingResponse(
            iter([stream.getvalue()]),
            headers={
                "Content-Disposition": 'attachment; filename="items_export.csv"',
                "Content-Type": "text/csv; charset=utf-8",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    stream = io.StringIO()
    json.dump(records, stream, indent=2)
    return StreamingResponse(
        iter([stream.getvalue()]),
        headers={
            "Content-Disposition": 'attachment; filename="items_export.json"',
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get(
    "/items/barcode/{barcode}",
    response_model=schemas.Item,
    responses={404: {"model": schemas.Error}},
)
async def lookup_by_barcode(
    barcode: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    return _service(db, current_user).lookup_by_barcode(barcode)


@router.get("/items/{item_id}", response_model=schemas.Item)
def get_item(
    item_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    return _service(db, current_user).get(item_id)


@router.put("/items/{item_id}", response_model=schemas.Item)
def update_item(
    item_id: uuid.UUID,
    item_update: schemas.ItemUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    return _service(db, current_user).update(item_id, item_update)


@router.delete("/items/{item_id}")
def delete_item(
    item_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    _service(db, current_user).delete(item_id)
    return {"status": "success"}


@router.post("/items/bulk-delete")
def bulk_delete_items(
    request: BulkDeleteRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    deleted_count = _service(db, current_user).bulk_delete(request.item_ids)
    return {"status": "success", "deleted_count": deleted_count}


@router.get("/categories", response_model=List[str])
def get_categories(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    return _service(db, current_user).categories()


@router.get("/locations", response_model=List[str])
def get_locations(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    return _service(db, current_user).locations()


@router.get("/locations/counts", response_model=List[schemas.LocationCount])
def get_location_counts(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    return _service(db, current_user).location_counts()


@router.post("/items/import", response_model=schemas.ImportResult)
async def import_items(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user),
) -> Any:
    content = await file.read()
    filename = file.filename or ""

    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode()))
            records = df.to_dict("records")
        elif filename.lower().endswith(".json"):
            records = json.loads(content)
            if not isinstance(records, list):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON format. Expected a list of items.",
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use .csv or .json",
            )
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8")
    except Exception:
        # Don't leak Pandas/csv parse details to the response body.
        logger.exception("error parsing import file")
        raise HTTPException(status_code=400, detail="Could not parse the uploaded file")

    return _service(db, current_user).import_records(records)
