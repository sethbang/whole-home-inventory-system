from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: UUID4
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    barcode: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None
    warranty_expiration: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None
    warranty_expiration: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ItemImage(BaseModel):
    id: UUID4
    item_id: UUID4
    filename: str
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Item(ItemBase):
    id: UUID4
    owner_id: UUID4
    created_at: datetime
    updated_at: datetime
    images: List[ItemImage] = []

    model_config = ConfigDict(from_attributes=True)


class SearchFilter(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    sort_by: Optional[str] = None
    sort_desc: bool = False
    page: int = 1
    page_size: int = 10


class ItemList(BaseModel):
    items: List[Item]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class BackupList(BaseModel):
    backups: List[Backup]


class ImportResult(BaseModel):
    success: bool
    message: str
    items_imported: int
    errors: Optional[List[str]] = None


class ExportFormat(BaseModel):
    format: str  # "csv" or "json"


class Error(BaseModel):
    detail: str


class RestoreRequest(BaseModel):
    """Body schema for POST /backups/{id}/restore when committing a restore.

    When ``dry_run=true`` is set on the query string the body is ignored and a
    preview is returned instead. When ``dry_run=false`` (or omitted) the caller
    MUST provide ``confirm_item_count`` that matches the current server-side
    count of their items; a mismatch is rejected with 409 to guard against
    accidental data loss from a stale UI.
    """

    confirm_item_count: Optional[int] = None


class RestoreResponse(BaseModel):
    success: bool
    message: str
    # Populated on a committed restore.
    items_restored: Optional[int] = None
    images_restored: Optional[int] = None
    errors: Optional[List[str]] = None
    # Populated on a dry-run preview.
    dry_run: bool = False
    current_item_count: Optional[int] = None
    backup_item_count: Optional[int] = None
    backup_image_count: Optional[int] = None
