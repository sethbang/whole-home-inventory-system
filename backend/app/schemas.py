from pydantic import BaseModel, EmailStr, UUID4, Field, validator
from typing import Optional, List, Dict, Union
from datetime import datetime

# User schemas
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

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Image schemas
class ItemImageBase(BaseModel):
    filename: str
    file_path: str

class ItemImageCreate(ItemImageBase):
    pass

class ItemImage(ItemImageBase):
    id: UUID4
    item_id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

# Item schemas
class ItemBase(BaseModel):
    model_config = {
        'protected_namespaces': ()
    }
    
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
    custom_fields: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default_factory=dict)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    name: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None

class Item(ItemBase):
    id: UUID4
    owner_id: UUID4
    created_at: datetime
    updated_at: datetime
    images: List[ItemImage] = []

    class Config:
        from_attributes = True

# Response schemas
class ItemList(BaseModel):
    items: List[Item]
    total: int
    page: int
    page_size: int

class SearchFilter(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    sort_by: Optional[str] = "created_at"
    sort_desc: bool = True
    page: int = 1
    page_size: int = 20
