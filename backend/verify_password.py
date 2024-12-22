from app.database import SessionLocal
from app import models, security
import os

def verify_db_and_password():
    # Print database location
    db_path = os.path.abspath("backend/database/whis.db")
    print(f"Database path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    
    db = SessionLocal()
    try:
        # Get the developer user
        user = db.query(models.User).filter(
            models.User.username == "developer"
        ).first()
        
        if not user:
            print("Developer user not found in database!")
            return
            
        print("\nUser details:")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Hashed password length: {len(user.hashed_password)}")
        
        # Test password verification
        test_password = "dev123456"
        is_valid = security.verify_password(test_password, user.hashed_password)
        print(f"\nPassword verification test:")
        print(f"Testing password: {test_password}")
        print(f"Password valid: {is_valid}")
        
    finally:
        db.close()

if __name__ == "__main__":
    verify_db_and_password()
