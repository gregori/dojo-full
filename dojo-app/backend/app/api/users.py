from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_admin
from app.schemas import UserCreate, UserResponse, UserUpdate
from app.services import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """List all users (admin only)."""
    return UserService.get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Get user by ID (admin only)."""
    return UserService.get_user(db, user_id)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Create a new user (admin only)."""
    return UserService.create_user(db, user_data)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str, user_data: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)
):
    """Update user (admin only)."""
    return UserService.update_user(db, user_id, user_data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Deactivate user (admin only)."""
    UserService.delete_user(db, user_id)
