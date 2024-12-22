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
UPLOAD_DIR = os.path.join("/app", "backend", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
print(f"Images upload directory: {UPLOAD_DIR}")
print(f"Directory exists: {os.path.exists(UPLOAD_DIR)}")
print(f"Directory permissions: {oct(os.stat(UPLOAD_DIR).st_mode)[-3:]}")

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
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{timestamp}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    print(f"Generated filename: {filename}")
    print(f"Full file path: {file_path}")
    
    # Save file
    try:
        print(f"Saving file to: {file_path}")
        save_upload_file(file, file_path)
        print(f"File saved successfully")
        print(f"File exists: {os.path.exists(file_path)}")
        print(f"File size: {os.path.getsize(file_path)} bytes")
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not upload file: {str(e)}"
        )
    
    # Create database record
    try:
        db_image = models.ItemImage(
            item_id=item_id,
            filename=filename,
            file_path=os.path.join('uploads', filename)  # Store relative path in database
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        print(f"Database record created: {db_image.id}")
        return db_image
    except Exception as e:
        print(f"Error creating database record: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)  # Clean up file if database insert fails
        raise HTTPException(
            status_code=500,
            detail=f"Could not create image record: {str(e)}"
        )

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
