from pydantic import BaseModel, UUID4, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: UUID4
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ItemBase(BaseModel):
    name: str
    category: str
    location: str
    brand: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None
    warranty_expiration: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: UUID4
    owner_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ItemImage(BaseModel):
    id: UUID4
    item_id: UUID4
    filename: str
    file_path: str
    created_at: datetime

    class Config:
        from_attributes = True

class BackupBase(BaseModel):
    pass

class BackupCreate(BackupBase):
    pass

class Backup(BackupBase):
    id: UUID4
    owner_id: UUID4
    filename: str
    file_path: str
    size_bytes: int
    item_count: int
    image_count: int
    created_at: datetime
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class BackupList(BaseModel):
    backups: List[Backup]

class RestoreResponse(BaseModel):
    success: bool
    message: str
    items_restored: Optional[int] = None
    images_restored: Optional[int] = None
    errors: Optional[List[str]] = None
