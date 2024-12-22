from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Any, List
from .. import models, schemas, security, database
import uuid
import os
import shutil
from datetime import datetime

router = APIRouter(tags=["images"])

# Create images directory if it doesn't exist
UPLOAD_DIR = os.path.join("backend", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()

@router.post("/items/{item_id}/images", response_model=schemas.ItemImage)
async def upload_item_image(
    item_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    # Check if item exists and belongs to user
    item = db.query(models.Item).filter(
        and_(
            models.Item.id == item_id,
            models.Item.owner_id == current_user.id
        )
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPEG or PNG)"
        )
    
    # Create user-specific upload directory
    user_upload_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
    os.makedirs(user_upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{timestamp}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(user_upload_dir, filename)
    
    # Save file
    try:
        save_upload_file(file, file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not upload file: {str(e)}"
        )
    
    # Create database record
    db_image = models.ItemImage(
        item_id=item_id,
        filename=filename,
        file_path=file_path
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    
    return db_image

@router.get("/items/{item_id}/images", response_model=List[schemas.ItemImage])
def list_item_images(
    item_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    # Check if item exists and belongs to user
    item = db.query(models.Item).filter(
        and_(
            models.Item.id == item_id,
            models.Item.owner_id == current_user.id
        )
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return item.images

@router.delete("/images/{image_id}")
def delete_image(
    image_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    # Get image and verify ownership
    image = db.query(models.ItemImage).join(models.Item).filter(
        and_(
            models.ItemImage.id == image_id,
            models.Item.owner_id == current_user.id
        )
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete file from filesystem
    try:
        if os.path.exists(image.file_path):
            os.remove(image.file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not delete file: {str(e)}"
        )
    
    # Delete database record
    db.delete(image)
    db.commit()
    
    return {"status": "success"}
