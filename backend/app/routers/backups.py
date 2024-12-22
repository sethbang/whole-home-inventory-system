from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import json
import shutil
from datetime import datetime
import zipfile
from .. import models, schemas, database
from ..security import get_current_user
from fastapi.responses import FileResponse

router = APIRouter()

# Create backups directory if it doesn't exist
BACKUP_DIR = os.path.join("backend", "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_backup_file(
    user_id: str,
    db: Session,
    backup_record: models.Backup
) -> None:
    try:
        # Get all user's items with their images
        items = db.query(models.Item).filter(models.Item.owner_id == user_id).all()
        
        # Create a temporary directory for the backup
        temp_dir = os.path.join(BACKUP_DIR, f"temp_{user_id}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Prepare the data structure
        backup_data = {
            "items": [],
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
        
        # Create images directory in the temp folder
        images_dir = os.path.join(temp_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        image_count = 0
        # Process each item and its images
        for item in items:
            item_data = {
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
                "warranty_expiration": item.warranty_expiration.isoformat() if item.warranty_expiration else None,
                "notes": item.notes,
                "custom_fields": item.custom_fields,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "images": []
            }
            
            # Process images
            for image in item.images:
                image_count += 1
                # Copy image file to backup directory
                if os.path.exists(image.file_path):
                    backup_image_path = os.path.join(images_dir, image.filename)
                    shutil.copy2(image.file_path, backup_image_path)
                    item_data["images"].append({
                        "id": str(image.id),
                        "filename": image.filename,
                        "created_at": image.created_at.isoformat()
                    })
            
            backup_data["items"].append(item_data)
        
        # Write the JSON data
        with open(os.path.join(temp_dir, "data.json"), "w") as f:
            json.dump(backup_data, f, indent=2)
        
        # Create the zip file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"backup_{user_id}_{timestamp}.zip"
        zip_path = os.path.join(BACKUP_DIR, zip_filename)
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zf.write(file_path, arcname)
        
        # Update backup record
        backup_record.filename = zip_filename
        backup_record.file_path = zip_path
        backup_record.size_bytes = os.path.getsize(zip_path)
        backup_record.item_count = len(items)
        backup_record.image_count = image_count
        backup_record.status = "completed"
        db.commit()
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        backup_record.status = "failed"
        backup_record.error_message = str(e)
        db.commit()
        raise

@router.post("/backups", response_model=schemas.Backup)
async def create_backup(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Create a backup record
    backup = models.Backup(
        owner_id=current_user.id,
        status="in_progress"
    )
    db.add(backup)
    db.commit()
    db.refresh(backup)
    
    # Start the backup process in the background
    background_tasks.add_task(
        create_backup_file,
        str(current_user.id),
        db,
        backup
    )
    
    return backup

@router.get("/backups", response_model=schemas.BackupList)
async def list_backups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    backups = db.query(models.Backup).filter(
        models.Backup.owner_id == current_user.id
    ).order_by(models.Backup.created_at.desc()).all()
    
    return {"backups": backups}

@router.post("/backups/{backup_id}/restore", response_model=schemas.RestoreResponse)
async def restore_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    backup = db.query(models.Backup).filter(
        models.Backup.id == backup_id,
        models.Backup.owner_id == current_user.id
    ).first()
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    try:
        # Create a temporary directory for restoration
        temp_dir = os.path.join(BACKUP_DIR, f"restore_{current_user.id}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract the backup
        with zipfile.ZipFile(backup.file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Read the backup data
        with open(os.path.join(temp_dir, "data.json")) as f:
            backup_data = json.load(f)
        
        items_restored = 0
        images_restored = 0
        errors = []
        
        # Clear existing items
        db.query(models.Item).filter(models.Item.owner_id == current_user.id).delete()
        
        # Restore items and images
        for item_data in backup_data["items"]:
            try:
                # Create new item
                new_item = models.Item(
                    owner_id=current_user.id,
                    name=item_data["name"],
                    category=item_data["category"],
                    location=item_data["location"],
                    brand=item_data["brand"],
                    model_number=item_data["model_number"],
                    serial_number=item_data["serial_number"],
                    purchase_date=datetime.fromisoformat(item_data["purchase_date"]) if item_data["purchase_date"] else None,
                    purchase_price=item_data["purchase_price"],
                    current_value=item_data["current_value"],
                    warranty_expiration=datetime.fromisoformat(item_data["warranty_expiration"]) if item_data["warranty_expiration"] else None,
                    notes=item_data["notes"],
                    custom_fields=item_data["custom_fields"]
                )
                db.add(new_item)
                db.flush()  # Get the new item ID
                
                # Restore images
                for image_data in item_data["images"]:
                    backup_image_path = os.path.join(temp_dir, "images", image_data["filename"])
                    if os.path.exists(backup_image_path):
                        # Copy image to uploads directory
                        new_image_path = os.path.join("backend", "uploads", image_data["filename"])
                        shutil.copy2(backup_image_path, new_image_path)
                        
                        # Create image record
                        new_image = models.ItemImage(
                            item_id=new_item.id,
                            filename=image_data["filename"],
                            file_path=new_image_path
                        )
                        db.add(new_image)
                        images_restored += 1
                
                items_restored += 1
                
            except Exception as e:
                errors.append(f"Error restoring item {item_data['name']}: {str(e)}")
        
        db.commit()
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return {
            "success": True,
            "message": "Backup restored successfully",
            "items_restored": items_restored,
            "images_restored": images_restored,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error restoring backup: {str(e)}"
        )

@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    backup = db.query(models.Backup).filter(
        models.Backup.id == backup_id,
        models.Backup.owner_id == current_user.id
    ).first()
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    # Delete the backup file if it exists
    if os.path.exists(backup.file_path):
        os.remove(backup.file_path)
    
    # Delete the database record
    db.delete(backup)
    db.commit()
    
    return {"message": "Backup deleted successfully"}

@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    backup = db.query(models.Backup).filter(
        models.Backup.id == backup_id,
        models.Backup.owner_id == current_user.id
    ).first()
    
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    if not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    return FileResponse(
        backup.file_path,
        media_type="application/zip",
        filename=backup.filename
    )