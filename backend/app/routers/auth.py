from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any
from .. import models, schemas, security, database

# Import development flag and user
from ..security import BYPASS_AUTH, DEV_USER

router = APIRouter(tags=["authentication"])

@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)) -> Any:
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email or username already registered"
        )
    
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
) -> Any:
    try:
        if BYPASS_AUTH:
            # In bypass mode, return a dummy token
            return {
                "access_token": "dev_token",
                "token_type": "bearer"
            }

        print(f"Login attempt for username: {form_data.username}")
        print(f"Received password length: {len(form_data.password)}")
        
        # Query user
        user = db.query(models.User).filter(models.User.username == form_data.username).first()
        
        if not user:
            print(f"User not found: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"Found user: {user.username}, checking password...")
        
        # Verify password
        is_valid = security.verify_password(form_data.password, user.hashed_password)
        print(f"Password verification result: {is_valid}")
        
        if not is_valid:
            print(f"Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"Successful login for user: {form_data.username}")
        
        # Generate token
        access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}",
        )

@router.get("/users/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(security.get_current_active_user)
) -> Any:
    if BYPASS_AUTH:
        return DEV_USER
    return current_user
