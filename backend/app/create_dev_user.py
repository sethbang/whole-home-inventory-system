from .database import SessionLocal, engine
from . import models
from .security import get_password_hash
import uuid

# Create dev user credentials
DEV_USERNAME = "developer"
DEV_PASSWORD = "dev123456"
DEV_EMAIL = "dev@example.com"

def create_dev_user():
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(models.User).filter(
            models.User.username == DEV_USERNAME
        ).first()
        
        if existing_user:
            print(f"Developer user '{DEV_USERNAME}' already exists")
            return
        
        # Create new user
        hashed_password = get_password_hash(DEV_PASSWORD)
        db_user = models.User(
            id=uuid.uuid4(),
            email=DEV_EMAIL,
            username=DEV_USERNAME,
            hashed_password=hashed_password,
            is_active=True
        )
        
        db.add(db_user)
        db.commit()
        print(f"Created developer user: {DEV_USERNAME}")
        
    finally:
        db.close()

if __name__ == "__main__":
    # Create tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    create_dev_user()
