from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import User
from app.schemas import UserCreate, UserUpdate


class AuthService:
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        """Authenticate a user by email and password."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    @staticmethod
    def create_access_token(user: User) -> str:
        """Create JWT access token for user."""
        token_data = {"sub": user.id, "role": user.role}
        return create_access_token(token_data)


class UserService:
    @staticmethod
    def get_user(db: Session, user_id: str) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        # Check if email already exists
        existing = UserService.get_user_by_email(db, user_data.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        db_user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
            is_active=user_data.is_active,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_user(db: Session, user_id: str, user_data: UserUpdate) -> User:
        user = UserService.get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        update_data = user_data.model_dump(exclude_unset=True)

        # Check email uniqueness if being updated
        if "email" in update_data:
            existing = UserService.get_user_by_email(db, update_data["email"])
            if existing and existing.id != user_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        # Hash password if being updated
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: str) -> None:
        user = UserService.get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.is_active = False
        user.updated_at = datetime.now(UTC)
        db.commit()
