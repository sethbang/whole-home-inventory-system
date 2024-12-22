from app.database import SessionLocal
from app import models

def verify_dev_user():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(
            models.User.username == "developer"
        ).first()
        
        if user:
            print("Developer user exists with:")
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print("Password: [Hashed, as expected]")
            print(f"Active: {user.is_active}")
            return True
        else:
            print("Developer user not found!")
            return False
            
    finally:
        db.close()

if __name__ == "__main__":
    verify_dev_user()
