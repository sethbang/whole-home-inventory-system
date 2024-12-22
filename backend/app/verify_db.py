import os
import sys
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, SQLALCHEMY_DATABASE_URL
from app import models, security
from sqlalchemy import inspect

def verify_database():
    print(f"\nDatabase URL: {SQLALCHEMY_DATABASE_URL}")
    db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')
    print(f"Database path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")

    # Get database inspector
    inspector = inspect(engine)
    
    # Print all tables
    print("\nDatabase tables:")
    tables = inspector.get_table_names()
    for table in tables:
        print(f"\nTable: {table}")
        columns = inspector.get_columns(table)
        for column in columns:
            print(f"  - {column['name']}: {column['type']}")

    # Check dev user
    db = SessionLocal()
    try:
        print("\nChecking dev user...")
        dev_user = db.query(models.User).filter(
            models.User.id == security.DEV_USER_ID
        ).first()
        
        if dev_user:
            print(f"Dev user found:")
            print(f"  ID: {dev_user.id}")
            print(f"  Email: {dev_user.email}")
            print(f"  Username: {dev_user.username}")
            print(f"  Is active: {dev_user.is_active}")
        else:
            print("Dev user not found!")
            print("Creating dev user...")
            dev_user = models.User(
                id=security.DEV_USER_ID,
                email="admin@example.com",
                username="admin",
                hashed_password="",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(dev_user)
            db.commit()
            print("Dev user created successfully")

        # Check if backups table exists and has correct schema
        print("\nVerifying backups table...")
        if 'backups' in tables:
            backup_columns = {col['name']: col['type'] for col in inspector.get_columns('backups')}
            required_columns = {
                'id': 'UUID',
                'owner_id': 'UUID',
                'filename': 'String',
                'file_path': 'String',
                'size_bytes': 'Integer',
                'item_count': 'Integer',
                'image_count': 'Integer',
                'created_at': 'DateTime',
                'status': 'String',
                'error_message': 'String'
            }
            
            missing_columns = []
            for col, type_ in required_columns.items():
                if col not in backup_columns:
                    missing_columns.append(col)
                else:
                    print(f"  Column {col} exists with type {backup_columns[col]}")
            
            if missing_columns:
                print(f"Missing columns in backups table: {missing_columns}")
                print("Recreating backups table...")
                models.Base.metadata.tables['backups'].drop(engine)
                models.Base.metadata.tables['backups'].create(engine)
                print("Backups table recreated successfully")
        else:
            print("Backups table does not exist!")
            print("Creating backups table...")
            models.Base.metadata.tables['backups'].create(engine)
            print("Backups table created successfully")

    finally:
        db.close()

if __name__ == "__main__":
    verify_database()