from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Float, JSON, TypeDecorator
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .database import Base

class UUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses SQLite's string type, storing as stringified hex values.
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif isinstance(value, uuid.UUID):
            return str(value)
        else:
            return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("Item", back_populates="owner")
    backups = relationship("Backup", back_populates="owner")

class Item(Base):
    __tablename__ = "items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    category = Column(String, index=True)
    location = Column(String, index=True)
    brand = Column(String)
    model_number = Column(String)
    serial_number = Column(String)
    purchase_date = Column(DateTime)
    purchase_price = Column(Float)
    current_value = Column(Float)
    warranty_expiration = Column(DateTime)
    notes = Column(String)
    custom_fields = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner_id = Column(UUID, ForeignKey("users.id"))
    owner = relationship("User", back_populates="items")
    images = relationship("ItemImage", back_populates="item", cascade="all, delete-orphan")

class ItemImage(Base):
    __tablename__ = "item_images"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID, ForeignKey("items.id"))
    filename = Column(String)
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    item = relationship("Item", back_populates="images")

class Backup(Base):
    __tablename__ = "backups"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID, ForeignKey("users.id"))
    filename = Column(String)
    file_path = Column(String)
    size_bytes = Column(Integer)
    item_count = Column(Integer)
    image_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # 'completed', 'failed', 'in_progress'
    error_message = Column(String, nullable=True)
    
    owner = relationship("User", back_populates="backups")
