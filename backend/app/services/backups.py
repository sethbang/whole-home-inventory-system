"""Backup service — create / list / restore / upload / delete / download.

Extracted from ``routers/backups.py`` in v2.2 alongside ImageService. The
v2.1 security rewrite (magic-byte zip validation, dry-run/confirm gating,
selectinload, scrubbed error leakage) is preserved verbatim; this module
just relocates it behind a service interface so the router can be a thin
shim and so the logic is testable without the HTTP harness.

All methods enforce ownership against ``self.user``. The service is sync:
the original router handlers were ``async def`` but performed only blocking
disk / DB I/O, so there was no real concurrency benefit. FastAPI will run
sync handlers in the default threadpool.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..settings import settings

logger = logging.getLogger(__name__)

# Cap total decompressed size of an uploaded backup zip. Multiplier chosen to
# give real backups (many images + data.json) headroom while refusing the
# classic zip-bomb shape where a small zip expands to many gigabytes.
MAX_BACKUP_DECOMPRESSED_BYTES = settings.MAX_UPLOAD_BYTES * 20


def inspect_backup_zip(file_path: str) -> int:
    """Validate a backup zip and return total uncompressed size.

    Raises HTTPException(400) for malformed zips, (413) for oversized archives.
    Uses stdlib's own structural checks rather than trusting the ``.zip``
    extension — an attacker can rename any file to ``.zip``.
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


def _backup_dir() -> str:
    path = str(settings.backup_path)
    os.makedirs(path, exist_ok=True)
    return path


def _serialize_item(item: models.Item) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "name": item.name,
        "category": item.category,
        "location": item.location,
        "brand": item.brand,
        "model_number": item.model_number,
        "serial_number": item.serial_number,
        "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
        "purchase_price": item.purchase_price,
        "current_value": item.current_value,
        "warranty_expiration": (
            item.warranty_expiration.isoformat() if item.warranty_expiration else None
        ),
        "notes": item.notes,
        "custom_fields": item.custom_fields,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
        "images": [],
    }


class BackupService:
    def __init__(self, db: Session, user: models.User):
        self.db = db
        self.user = user

    # -- internal helpers ---------------------------------------------------

    def _owned_backup(self, backup_id: str) -> models.Backup:
        stmt = select(models.Backup).where(
            models.Backup.id == backup_id,
            models.Backup.owner_id == self.user.id,
        )
        backup = self.db.execute(stmt).scalar_one_or_none()
        if backup is None:
            raise HTTPException(status_code=404, detail="Backup not found")
        return backup

    def _own_items(self):
        stmt = (
            select(models.Item)
            .options(selectinload(models.Item.images))
            .where(models.Item.owner_id == self.user.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    # -- create -------------------------------------------------------------

    def create(self) -> models.Backup:
        """Snapshot the user's items + images into a zip and persist a Backup."""
        owner_id = (
            str(self.user.id) if not isinstance(self.user.id, str) else self.user.id
        )
        backup = models.Backup(owner_id=owner_id, status="in_progress")
        self.db.add(backup)
        self.db.flush()
        self.db.commit()
        self.db.refresh(backup)

        try:
            self._write_backup_file(owner_id, backup)
            self.db.refresh(backup)
            return backup
        except Exception:
            logger.exception("backup creation failed for user %s", owner_id)
            backup.status = "failed"
            backup.error_message = "Failed to create backup"
            self.db.commit()
            raise HTTPException(status_code=500, detail="Failed to create backup")

    def _write_backup_file(self, owner_id: str, backup_record: models.Backup) -> None:
        logger.info("starting backup for user %s", owner_id)
        items = self._own_items()

        backup_dir = _backup_dir()
        temp_dir = os.path.join(backup_dir, f"temp_{owner_id}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            backup_data = {
                "items": [],
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0",
            }
            images_dir = os.path.join(temp_dir, "images")
            os.makedirs(images_dir, exist_ok=True)

            # Images on disk live at ``settings.upload_path / filename``
            # (absolute, e.g. ``/app/backend/uploads/foo.jpg``). The
            # ``ItemImage.file_path`` column stores a *relative* URL-style
            # path ``uploads/foo.jpg`` for the frontend to consume via the
            # ``/uploads`` static mount — it isn't directly resolvable from
            # the backend's CWD. Resolving via ``settings.upload_path`` here
            # is what actually copies the bytes into the zip.
            upload_dir = str(settings.upload_path)
            image_count = 0
            for item in items:
                item_data = _serialize_item(item)
                for image in item.images:
                    image_count += 1
                    on_disk = os.path.join(upload_dir, image.filename)
                    if os.path.exists(on_disk):
                        backup_image_path = os.path.join(images_dir, image.filename)
                        shutil.copy2(on_disk, backup_image_path)
                        item_data["images"].append(
                            {
                                "id": str(image.id),
                                "filename": image.filename,
                                "created_at": image.created_at.isoformat(),
                            }
                        )
                    else:
                        logger.warning(
                            "image file missing on disk, skipping from backup: "
                            "item=%s image=%s expected_at=%s",
                            item.id,
                            image.id,
                            on_disk,
                        )
                backup_data["items"].append(item_data)

            with open(os.path.join(temp_dir, "data.json"), "w") as f:
                json.dump(backup_data, f, indent=2)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"backup_{owner_id}_{timestamp}.zip"
            zip_path = os.path.join(backup_dir, zip_filename)

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
            self.db.commit()
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # -- list ---------------------------------------------------------------

    def list(self) -> list[models.Backup]:
        """Return this user's completed backups (newest first)."""
        stmt = (
            select(models.Backup)
            .where(
                models.Backup.owner_id == self.user.id,
                models.Backup.filename.isnot(None),
                models.Backup.file_path.isnot(None),
                models.Backup.size_bytes.isnot(None),
                models.Backup.item_count.isnot(None),
                models.Backup.image_count.isnot(None),
            )
            .order_by(models.Backup.created_at.desc())
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return [
            b
            for b in rows
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

    # -- restore ------------------------------------------------------------

    def preview_restore(self, backup_id: str) -> dict[str, Any]:
        """Non-destructive: return the restore plan without touching DB state."""
        backup, backup_data = self._prepare_restore(backup_id)
        current_item_count = self._current_item_count()
        backup_item_count = len(backup_data["items"])
        backup_image_count = sum(
            len(it.get("images", [])) for it in backup_data["items"]
        )
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

    def validate_restore_request(
        self, backup_id: str, confirm_item_count: int | None
    ) -> None:
        """Fail-fast preflight checks for a commit_restore call.

        Runs cheaply (ownership lookup + a SELECT COUNT) so the router
        can reject bad requests before enqueueing a worker job. The
        same checks still run inside ``commit_restore`` in case anyone
        calls the service directly — ARQ task, test fixture, etc.
        """
        self._owned_backup(backup_id)  # 404 if not found / not owned
        current_item_count = self._current_item_count()

        if confirm_item_count is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Restore requires confirm_item_count in the request body when "
                    "dry_run is false. Run with dry_run=true first to see the "
                    "current count."
                ),
            )
        if confirm_item_count != current_item_count:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"confirm_item_count ({confirm_item_count}) does not match the "
                    f"current server-side item count ({current_item_count}). The "
                    "inventory likely changed since you previewed this restore; "
                    "fetch a fresh preview and try again."
                ),
            )

    def commit_restore(
        self, backup_id: str, confirm_item_count: int | None
    ) -> dict[str, Any]:
        """Destructive: wipe the user's items and restore from the backup."""
        # Validation runs up-front in the router too, but re-checking here
        # keeps the service safe against direct callers (worker tasks, tests).
        self.validate_restore_request(backup_id, confirm_item_count)
        current_item_count = self._current_item_count()
        backup, backup_data = self._prepare_restore(backup_id)

        backup_dir = _backup_dir()
        temp_dir = os.path.join(backup_dir, f"restore_{self.user.id}")
        os.makedirs(temp_dir, exist_ok=True)

        items_restored = 0
        images_restored = 0
        errors: list[str] = []
        try:
            with zipfile.ZipFile(backup.file_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Delete child ``item_images`` rows before the parent ``items``
            # rows. The 20260423_0008 migration promoted the FK to
            # ``ON DELETE CASCADE`` at the DB level so this is defensive —
            # but it also means the delete path no longer depends on
            # SQLite's by-default FK-disabled behavior to hide a bug, and
            # stays correct on Postgres even if a future revert of the
            # migration lands.
            item_id_subq = (
                select(models.Item.id)
                .where(models.Item.owner_id == self.user.id)
                .scalar_subquery()
            )
            self.db.query(models.ItemImage).filter(
                models.ItemImage.item_id.in_(item_id_subq)
            ).delete(synchronize_session=False)
            self.db.query(models.Item).filter(
                models.Item.owner_id == self.user.id
            ).delete(synchronize_session=False)

            upload_dir = str(settings.upload_path)
            os.makedirs(upload_dir, exist_ok=True)

            for item_data in backup_data["items"]:
                try:
                    new_item = models.Item(
                        owner_id=self.user.id,
                        name=item_data["name"],
                        category=item_data["category"],
                        location=item_data["location"],
                        brand=item_data.get("brand"),
                        model_number=item_data.get("model_number"),
                        serial_number=item_data.get("serial_number"),
                        purchase_date=(
                            datetime.fromisoformat(item_data["purchase_date"])
                            if item_data.get("purchase_date")
                            else None
                        ),
                        purchase_price=item_data.get("purchase_price"),
                        current_value=item_data.get("current_value"),
                        warranty_expiration=(
                            datetime.fromisoformat(item_data["warranty_expiration"])
                            if item_data.get("warranty_expiration")
                            else None
                        ),
                        notes=item_data.get("notes"),
                        custom_fields=item_data.get("custom_fields"),
                    )
                    self.db.add(new_item)
                    self.db.flush()

                    for image_data in item_data.get("images", []):
                        backup_image_path = os.path.join(
                            temp_dir, "images", image_data["filename"]
                        )
                        if os.path.exists(backup_image_path):
                            on_disk_path = os.path.join(
                                upload_dir, image_data["filename"]
                            )
                            shutil.copy2(backup_image_path, on_disk_path)
                            new_image = models.ItemImage(
                                item_id=new_item.id,
                                filename=image_data["filename"],
                                file_path=os.path.join(
                                    "uploads", image_data["filename"]
                                ),
                            )
                            self.db.add(new_image)
                            images_restored += 1

                    items_restored += 1
                except Exception:
                    logger.exception("error restoring item %s", item_data.get("name"))
                    errors.append(
                        f"Error restoring item {item_data.get('name', '<unknown>')}"
                    )

            self.db.commit()
            return {
                "success": True,
                "message": "Backup restored successfully",
                "items_restored": items_restored,
                "images_restored": images_restored,
                "errors": errors or None,
                "dry_run": False,
                "current_item_count": current_item_count,
                "backup_item_count": len(backup_data["items"]),
                "backup_image_count": sum(
                    len(it.get("images", [])) for it in backup_data["items"]
                ),
            }
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _current_item_count(self) -> int:
        stmt = select(models.Item).where(models.Item.owner_id == self.user.id)
        return len(list(self.db.execute(stmt).scalars().all()))

    def _prepare_restore(self, backup_id: str) -> tuple[models.Backup, dict[str, Any]]:
        """Validate backup + extract data.json without mutating the DB."""
        backup = self._owned_backup(backup_id)
        if not backup.file_path or not os.path.exists(backup.file_path):
            logger.warning("backup file missing on disk: %s", backup.file_path)
            raise HTTPException(
                status_code=404, detail="Backup file not found on server"
            )

        # Re-validate the archive on read — an on-disk file could have been
        # tampered with or truncated since upload.
        inspect_backup_zip(backup.file_path)

        backup_dir = _backup_dir()
        temp_dir = os.path.join(backup_dir, f"prepare_{self.user.id}")
        os.makedirs(temp_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(backup.file_path, "r") as zip_ref:
                zip_ref.extract("data.json", temp_dir)
            data_file = os.path.join(temp_dir, "data.json")
            if not os.path.exists(data_file):
                raise HTTPException(
                    status_code=400, detail="Backup is missing data.json"
                )
            with open(data_file) as f:
                backup_data = json.load(f)
            if not isinstance(backup_data, dict) or "items" not in backup_data:
                raise HTTPException(
                    status_code=400, detail="Backup data structure is invalid"
                )
            return backup, backup_data
        except KeyError:
            raise HTTPException(status_code=400, detail="Backup is missing data.json")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # -- upload -------------------------------------------------------------

    def upload(self, filename: str, source_path: str) -> models.Backup:
        """Accept a pre-saved zip file on disk as a restorable backup."""
        if not filename or not filename.lower().endswith(".zip"):
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. Only .zip files are allowed.",
            )

        # Move the staged file to its final backup location and validate.
        backup_dir = _backup_dir()
        final_path = os.path.join(backup_dir, filename)
        if source_path != final_path:
            shutil.move(source_path, final_path)

        temp_dir = os.path.join(backup_dir, f"upload_{self.user.id}")
        try:
            inspect_backup_zip(final_path)

            os.makedirs(temp_dir, exist_ok=True)
            with zipfile.ZipFile(final_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            data_file = os.path.join(temp_dir, "data.json")
            if not os.path.exists(data_file):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid backup file: missing data.json",
                )
            with open(data_file) as f:
                backup_data = json.load(f)
            if not isinstance(backup_data, dict) or "items" not in backup_data:
                raise HTTPException(
                    status_code=400, detail="Invalid backup data structure"
                )

            item_count = len(backup_data["items"])
            image_count = sum(
                len(item.get("images", [])) for item in backup_data["items"]
            )

            backup = models.Backup(
                owner_id=self.user.id,
                filename=filename,
                file_path=final_path,
                size_bytes=os.path.getsize(final_path),
                item_count=item_count,
                image_count=image_count,
                status="completed",
            )
            self.db.add(backup)
            self.db.commit()
            self.db.refresh(backup)
            return backup
        except HTTPException:
            if os.path.exists(final_path):
                os.remove(final_path)
            raise
        except json.JSONDecodeError:
            if os.path.exists(final_path):
                os.remove(final_path)
            raise HTTPException(
                status_code=400, detail="Backup data.json is not valid JSON"
            )
        except Exception:
            logger.exception("error processing uploaded backup")
            if os.path.exists(final_path):
                os.remove(final_path)
            raise HTTPException(status_code=500, detail="Error processing backup file")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    # -- delete / download --------------------------------------------------

    def delete(self, backup_id: str) -> None:
        backup = self._owned_backup(backup_id)
        if backup.file_path and os.path.exists(backup.file_path):
            try:
                os.remove(backup.file_path)
            except OSError as exc:
                logger.warning("could not remove backup file: %s", exc)
        self.db.delete(backup)
        self.db.commit()

    def get_download_path(self, backup_id: str) -> tuple[models.Backup, Path]:
        backup = self._owned_backup(backup_id)
        if not backup.file_path or not os.path.exists(backup.file_path):
            logger.warning("backup file missing on disk: %s", backup.file_path)
            raise HTTPException(status_code=404, detail="Backup file not found")
        if not os.access(backup.file_path, os.R_OK):
            logger.error("backup file not readable: %s", backup.file_path)
            raise HTTPException(status_code=500, detail="Backup file is not readable")
        return backup, Path(backup.file_path)
