from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import (
    get_current_admin,
    get_current_instructor_or_admin,
)
from app.schemas import StudentCreate, StudentResponse, StudentUpdate, StudentWithBelt
from app.services import StudentService

router = APIRouter(prefix="/api/v1/students", tags=["students"])


@router.get("", response_model=list[StudentResponse])
def list_students(
    category: str | None = None,
    is_active: bool | None = True,
    include_inactive: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """List students. Defaults to active only. Use include_inactive=true to include inactive students."""
    if include_inactive:
        is_active = None
    return StudentService.get_students(db, category=category, is_active=is_active, skip=skip, limit=limit)


@router.get("/{student_id}", response_model=StudentWithBelt)
def get_student(student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """Get student by ID."""
    return StudentService.get_student(db, student_id)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student_data: StudentCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Create a new student (admin only)."""
    return StudentService.create_student(db, student_data, created_by=current_user.id)


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: str, student_data: StudentUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)
):
    """Update student (admin only)."""
    return StudentService.update_student(db, student_id, student_data)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_student(student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Deactivate student (admin only)."""
    StudentService.deactivate_student(db, student_id)


@router.get("/{student_id}/progress")
def get_student_progress(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Get student's progress towards next belt."""
    return StudentService.get_student_progress(db, student_id)


@router.get("/{student_id}/exam-history")
def get_student_exam_history(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Get student's exam history."""
    return StudentService.get_student_exam_history(db, student_id)
