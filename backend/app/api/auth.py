"""
Authentication API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserCreate, UserLogin, Token, UserResponse,
    ChangePassword, UserUpdate
)
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    authenticate_user, get_current_active_user, require_admin
)
from app.core.audit import log_activity

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        # Public registration must never grant elevated privileges.
        role=UserRole.VIEWER,
        is_active=True,
        is_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_activity(db, new_user, "Registered Account", resource=new_user.username, details="New account registered")
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        created_at=new_user.created_at,
        last_login=new_user.last_login
    )


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login user and return JWT token
    """
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    log_activity(db, user, "Login", resource="auth", details="User signed in")
    
    # Create access token
    token_data = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(token_data)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    log_activity(db, current_user, "Changed Password", resource="profile", details="Password changed successfully")
    
    return {"message": "Password changed successfully"}


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update editable profile fields for the authenticated user."""
    if user_data.username and user_data.username != current_user.username:
        if db.query(User).filter(User.username == user_data.username, User.id != current_user.id).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = user_data.username.strip()
    if user_data.email and str(user_data.email) != current_user.email:
        if db.query(User).filter(User.email == str(user_data.email), User.id != current_user.id).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = str(user_data.email)
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name.strip() or None
    db.commit()
    db.refresh(current_user)
    log_activity(db, current_user, "Updated Profile", resource=current_user.username, details="Profile details updated")
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Logout user (client should discard token)
    """
    log_activity(db, current_user, "Logout", resource="auth", details="User signed out")
    return {"message": "Logged out successfully"}


@router.post("/create-admin")
async def create_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create default admin user (for setup purposes)
    """
    # Check if admin exists
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        return {"message": "Admin user already exists"}
    
    # Create admin
    admin_user = User(
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("admin123"),
        full_name="System Administrator",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    
    db.add(admin_user)
    db.commit()
    
    return {"message": "Admin user created successfully. Username: admin, Password: admin123"}