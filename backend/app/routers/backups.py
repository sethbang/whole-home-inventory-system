import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..security import get_current_active_user
from ..settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

BACKUP_DIR = str(settings.backup_path)
os.makedirs(BACKUP_DIR, exist_ok=True)
logger.info("backup directory: %s", BACKUP_DIR)

# Cap total decompressed size of an uploaded backup zip. Multiplier chosen to
# give real backups (many images + data.json) headroom while refusing the
# classic zip-bomb shape where a small zip expands to many gigabytes.
MAX_BACKUP_DECOMPRESSED_BYTES = settings.MAX_UPLOAD_BYTES * 20


def _inspect_backup_zip(file_path: str) -> int:
    """Validate a backup zip and return total uncompressed size.

    Raises HTTPException(400) for malformed zips, (413) for oversized archives.
    Uses the standard library's own structural checks rather than trusting the
    ``.zip`` extension — an attacker can rename any file to ``.zip``.
    """
    if not zipfile.is_zipfile(file_path):
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a valid zip archive"
        )

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            corrupt = zf.testzip()
            if corrupt is not None:
                raise HTTPException(
                    status_code=400, detail="Backup zip contains a corrupt entry"
                )
            total = sum(info.file_size for info in zf.infolist())
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Backup zip is malformed")

    if total > MAX_BACKUP_DECOMPRESSED_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Backup archive exceeds the maximum allowed decompressed size",
        )
    return total


async def create_backup_file(
    user_id: str, db: Session, backup_record: models.Backup
) -> None:
    try:
        logger.info("starting backup for user %s", user_id)
        # Eager-load images to avoid an N+1 query when serializing each item.
        items = (
            db.query(models.Item)
            .options(selectinload(models.Item.images))
            .filter(models.Item.owner_id == user_id)
            .all()
        )

        temp_dir = os.path.join(BACKUP_DIR, f"temp_{user_id}")
        os.makedirs(temp_dir, exist_ok=True)

        backup_data = {
            "items": [],
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        images_dir = os.path.join(temp_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        image_count = 0
        for item in items:
            item_data = {
                "id": str(item.id),
                "name": item.name,
                "category": item.category,
                "location": item.location,
                "brand": item.brand,
                "model_number": item.model_number,
                "serial_number": item.serial_number,
                "purchase_date": item.purchase_date.isoformat()
                if item.purchase_date
                else None,
                "purchase_price": item.purchase_price,
                "current_value": item.current_value,
                "warranty_expiration": item.warranty_expiration.isoformat()
                if item.warranty_expiration
                else None,
                "notes": item.notes,
                "custom_fields": item.custom_fields,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "images": [],
            }

            for image in item.images:
                image_count += 1
                if os.path.exists(image.file_path):
                    backup_image_path = os.path.join(images_dir, image.filename)
                    shutil.copy2(image.file_path, backup_image_path)
                    item_data["images"].append(
                        {
                            "id": str(image.id),
                            "filename": image.filename,
                            "created_at": image.created_at.isoformat(),
                        }
                    )

            backup_data["items"].append(item_data)

        with open(os.path.join(temp_dir, "data.json"), "w") as f:
            json.dump(backup_data, f, indent=2)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"backup_{user_id}_{timestamp}.zip"
        zip_path = os.path.join(BACKUP_DIR, zip_filename)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zf.write(file_path, arcname)

        backup_record.filename = zip_filename
        backup_record.file_path = zip_path
        backup_record.size_bytes = os.path.getsize(zip_path)
        backup_record.item_count = len(items)
        backup_record.image_count = image_count
        backup_record.status = "completed"
        db.commit()

        shutil.rmtree(temp_dir)

    except Exception as exc:
        logger.exception("error during backup creation")
        backup_record.status = "failed"
        # error_message is operator-facing (visible in the DB/admin), not end-user-facing.
        backup_record.error_message = str(exc)
        db.commit()
        raise


@router.post("/backups", response_model=schemas.Backup)
async def create_backup(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    owner_id = (
        str(current_user.id)
        if not isinstance(current_user.id, str)
        else current_user.id
    )
    backup = None
    try:
        backup = models.Backup(owner_id=owner_id, status="in_progress")
        db.add(backup)
        db.flush()
        db.commit()
        db.refresh(backup)
    except Exception:
        logger.exception("failed to create backup record")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create backup record")

    try:
        await create_backup_file(owner_id, db, backup)
        db.refresh(backup)
        return backup
    except Exception:
        logger.exception("backup creation failed")
        backup.status = "failed"
        backup.error_message = "Failed to create backup"
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to create backup")


@router.get("/backups", response_model=schemas.BackupList)
async def list_backups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    backups = (
        db.query(models.Backup)
        .filter(
            models.Backup.owner_id == current_user.id,
            models.Backup.filename.isnot(None),
            models.Backup.file_path.isnot(None),
            models.Backup.size_bytes.isnot(None),
            models.Backup.item_count.isnot(None),
            models.Backup.image_count.isnot(None),
        )
        .order_by(models.Backup.created_at.desc())
        .all()
    )

    valid_backups = [
        b
        for b in backups
        if all(
            [
                b.filename,
                b.file_path,
                b.size_bytes is not None,
                b.item_count is not None,
                b.image_count is not None,
            ]
        )
    ]

    return {"backups": valid_backups}


@router.post("/backups/{backup_id}/restore", response_model=schemas.RestoreResponse)
async def restore_backup(
    backup_id: str,
    dry_run: bool = Query(
        True,
        description=(
            "When true (the default), return a non-destructive preview describing "
            "what would be restored. When false the caller MUST supply "
            "confirm_item_count in the body, matching the server-side item count."
        ),
    ),
    body: Optional[schemas.RestoreRequest] = Body(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    backup = (
        db.query(models.Backup)
        .filter(
            models.Backup.id == backup_id,
            models.Backup.owner_id == current_user.id,
        )
        .first()
    )

    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    if not backup.file_path or not os.path.exists(backup.file_path):
        logger.warning("backup file missing on disk: %s", backup.file_path)
        raise HTTPException(status_code=404, detail="Backup file not found on server")

    temp_dir = os.path.join(BACKUP_DIR, f"restore_{current_user.id}")
    try:
        os.makedirs(temp_dir, exist_ok=True)

        # Re-validate the archive on read — an on-disk backup file could have
        # been tampered with or truncated since upload.
        _inspect_backup_zip(backup.file_path)

        with zipfile.ZipFile(backup.file_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        data_file = os.path.join(temp_dir, "data.json")
        if not os.path.exists(data_file):
            raise HTTPException(status_code=400, detail="Backup is missing data.json")

        with open(data_file) as f:
            backup_data = json.load(f)
        if not isinstance(backup_data, dict) or "items" not in backup_data:
            raise HTTPException(
                status_code=400, detail="Backup data structure is invalid"
            )

        current_item_count = (
            db.query(models.Item)
            .filter(models.Item.owner_id == current_user.id)
            .count()
        )
        backup_item_count = len(backup_data["items"])
        backup_image_count = sum(
            len(it.get("images", [])) for it in backup_data["items"]
        )

        if dry_run:
            return {
                "success": True,
                "message": (
                    f"Dry run: restoring this backup will delete {current_item_count} "
                    f"existing item(s) and replace them with {backup_item_count} "
                    f"item(s) from the archive. Re-submit with dry_run=false and "
                    f"confirm_item_count={current_item_count} to proceed."
                ),
                "dry_run": True,
                "current_item_count": current_item_count,
                "backup_item_count": backup_item_count,
                "backup_image_count": backup_image_count,
            }

        # Destructive path — require explicit confirmation.
        if body is None or body.confirm_item_count is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Restore requires confirm_item_count in the request body when "
                    "dry_run is false. Run with dry_run=true first to see the "
                    "current count."
                ),
            )
        if body.confirm_item_count != current_item_count:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"confirm_item_count ({body.confirm_item_count}) does not match "
                    f"the current server-side item count ({current_item_count}). "
                    "The inventory likely changed since you previewed this restore; "
                    "fetch a fresh preview and try again."
                ),
            )

        items_restored = 0
        images_restored = 0
        errors: list[str] = []

        db.query(models.Item).filter(models.Item.owner_id == current_user.id).delete(
            synchronize_session=False
        )

        upload_dir = str(settings.upload_path)
        os.makedirs(upload_dir, exist_ok=True)

        for item_data in backup_data["items"]:
            try:
                new_item = models.Item(
                    owner_id=current_user.id,
                    name=item_data["name"],
                    category=item_data["category"],
                    location=item_data["location"],
                    brand=item_data["brand"],
                    model_number=item_data["model_number"],
                    serial_number=item_data["serial_number"],
                    purchase_date=datetime.fromisoformat(item_data["purchase_date"])
                    if item_data["purchase_date"]
                    else None,
                    purchase_price=item_data["purchase_price"],
                    current_value=item_data["current_value"],
                    warranty_expiration=datetime.fromisoformat(
                        item_data["warranty_expiration"]
                    )
                    if item_data["warranty_expiration"]
                    else None,
                    notes=item_data["notes"],
                    custom_fields=item_data["custom_fields"],
                )
                db.add(new_item)
                db.flush()

                for image_data in item_data.get("images", []):
                    backup_image_path = os.path.join(
                        temp_dir, "images", image_data["filename"]
                    )
                    if os.path.exists(backup_image_path):
                        on_disk_path = os.path.join(upload_dir, image_data["filename"])
                        shutil.copy2(backup_image_path, on_disk_path)

                        new_image = models.ItemImage(
                            item_id=new_item.id,
                            filename=image_data["filename"],
                            file_path=os.path.join("uploads", image_data["filename"]),
                        )
                        db.add(new_image)
                        images_restored += 1

                items_restored += 1
            except Exception:
                logger.exception("error restoring item %s", item_data.get("name"))
                errors.append(
                    f"Error restoring item {item_data.get('name', '<unknown>')}"
                )

        db.commit()

        return {
            "success": True,
            "message": "Backup restored successfully",
            "items_restored": items_restored,
            "images_restored": images_restored,
            "errors": errors or None,
            "dry_run": False,
            "current_item_count": current_item_count,
            "backup_item_count": backup_item_count,
            "backup_image_count": backup_image_count,
        }

    except HTTPException:
        raise
    except Exception:
        # Never leak Python exception strings into the response — they often
        # include paths, class names, or stack-relevant fragments that are
        # useful only to an attacker.
        logger.exception("error restoring backup %s", backup_id)
        raise HTTPException(status_code=500, detail="Restore failed; check server logs")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/backups/upload")
async def upload_backup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    # Extension is a cheap first filter; the real validation comes after the
    # bytes are on disk via ``_inspect_backup_zip``.
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .zip files are allowed.",
        )

    file_path = os.path.join(BACKUP_DIR, file.filename)
    temp_dir = os.path.join(BACKUP_DIR, f"upload_{current_user.id}")
    saved = False

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved = True

        # Validate the archive BEFORE doing anything else with it. This rejects
        # renamed-.exe uploads, corrupted zips, and decompression bombs.
        _inspect_backup_zip(file_path)

        os.makedirs(temp_dir, exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        data_file = os.path.join(temp_dir, "data.json")
        if not os.path.exists(data_file):
            raise HTTPException(
                status_code=400, detail="Invalid backup file: missing data.json"
            )

        with open(data_file) as f:
            backup_data = json.load(f)
        if not isinstance(backup_data, dict) or "items" not in backup_data:
            raise HTTPException(status_code=400, detail="Invalid backup data structure")

        item_count = len(backup_data["items"])
        image_count = sum(len(item.get("images", [])) for item in backup_data["items"])

        backup = models.Backup(
            owner_id=current_user.id,
            filename=file.filename,
            file_path=file_path,
            size_bytes=os.path.getsize(file_path),
            item_count=item_count,
            image_count=image_count,
            status="completed",
        )
        db.add(backup)
        db.commit()
        db.refresh(backup)
        return backup

    except HTTPException:
        if saved and os.path.exists(file_path):
            os.remove(file_path)
        raise
    except json.JSONDecodeError:
        if saved and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=400, detail="Backup data.json is not valid JSON"
        )
    except Exception:
        logger.exception("error processing uploaded backup")
        if saved and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Error processing backup file")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    backup = (
        db.query(models.Backup)
        .filter(
            models.Backup.id == backup_id,
            models.Backup.owner_id == current_user.id,
        )
        .first()
    )

    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    if backup.file_path and os.path.exists(backup.file_path):
        os.remove(backup.file_path)

    db.delete(backup)
    db.commit()
    return {"message": "Backup deleted successfully"}


@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    backup = (
        db.query(models.Backup)
        .filter(
            models.Backup.id == backup_id,
            models.Backup.owner_id == current_user.id,
        )
        .first()
    )

    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    if not os.path.exists(backup.file_path):
        logger.warning("backup file missing on disk: %s", backup.file_path)
        raise HTTPException(status_code=404, detail="Backup file not found")

    if not os.access(backup.file_path, os.R_OK):
        logger.error("backup file not readable: %s", backup.file_path)
        raise HTTPException(status_code=500, detail="Backup file is not readable")

    try:
        response = FileResponse(
            backup.file_path,
            media_type="application/zip",
            filename=backup.filename,
        )
        response.headers["Content-Disposition"] = (
            f'attachment; filename="{backup.filename}"'
        )
        return response
    except Exception:
        logger.exception("error serving backup file")
        raise HTTPException(status_code=500, detail="Error serving backup file")
