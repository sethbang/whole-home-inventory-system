from app.database import SessionLocal, engine
from app import models, schemas, security
import uuid
from pydantic import EmailStr

# Create dev user credentials
DEV_USERNAME = "developer"
DEV_PASSWORD = "dev123456"
DEV_EMAIL = "dev@example.com"

def create_dev_user():
    # Validate input using schema
    user_data = schemas.UserCreate(
        email=DEV_EMAIL,
        username=DEV_USERNAME,
        password=DEV_PASSWORD
    )
    
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(models.User).filter(
            (models.User.email == user_data.email) | 
            (models.User.username == user_data.username)
        ).first()
        
        if existing_user:
            print(f"Developer user '{DEV_USERNAME}' already exists")
            # Print existing user details for debugging
            print(f"Existing user details:")
            print(f"ID: {existing_user.id}")
            print(f"Email: {existing_user.email}")
            print(f"Username: {existing_user.username}")
            print(f"Is Active: {existing_user.is_active}")
            return
        
        # Create new user
        hashed_password = security.get_password_hash(user_data.password)
        db_user = models.User(
            id=uuid.uuid4(),
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            is_active=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        print(f"Created developer user successfully:")
        print(f"ID: {db_user.id}")
        print(f"Email: {db_user.email}")
        print(f"Username: {db_user.username}")
        print(f"Is Active: {db_user.is_active}")
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Create tables if they don't exist
    print("Creating database tables if they don't exist...")
    models.Base.metadata.create_all(bind=engine)
    
    print("\nAttempting to create developer user...")
    create_dev_user()
