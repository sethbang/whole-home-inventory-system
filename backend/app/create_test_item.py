from .database import SessionLocal, engine, SQLALCHEMY_DATABASE_URL
from . import models, security
from datetime import datetime
import uuid
import os

def create_test_item():
    print(f"Database URL: {SQLALCHEMY_DATABASE_URL}")
    db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')
    print(f"Database path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    # Use the fixed DEV_USER_ID
    dev_user_id = security.DEV_USER_ID
    print(f"Using DEV_USER ID: {dev_user_id}")
    
    db = SessionLocal()
    try:
        print("Checking database connection...")
        # Check if item already exists
        existing_item = db.query(models.Item).filter(
            models.Item.barcode == "9780262529846"
        ).first()
        
        if existing_item:
            print(f"Test item with barcode '9780262529846' exists with owner_id: {existing_item.owner_id}")
            print(f"Updating owner_id to match DEV_USER: {dev_user_id}")
            existing_item.owner_id = dev_user_id
            db.commit()
            db.refresh(existing_item)
            print(f"Updated test item owner_id to: {existing_item.owner_id}")
            return
        
        print("Creating new test item...")
        
        # Create new item (this appears to be an ISBN for a book)
        db_item = models.Item(
            id=uuid.uuid4(),
            name="Deep Learning (Adaptive Computation and Machine Learning series)",
            category="Books",
            location="Office",
            brand="MIT Press",
            barcode="9780262529846",
            purchase_date=datetime.utcnow(),
            purchase_price=59.99,
            current_value=59.99,
            notes="An introduction to a broad range of topics in deep learning by Ian Goodfellow, Yoshua Bengio, and Aaron Courville",
            owner_id=dev_user_id  # Use the DEV_USER's ID so they can see the item
        )
        
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        print(f"Created test item with barcode: 9780262529846 and owner_id: {db_item.owner_id}")
        
    finally:
        db.close()

if __name__ == "__main__":
    # Create tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    create_test_item()
