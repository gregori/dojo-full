from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import (
    get_current_admin,
    get_current_instructor_or_admin,
)
from app.schemas import (
    ExamBoardMemberCreate,
    ExamBoardMemberResponse,
    ExamCreate,
    ExamParticipantCreate,
    ExamParticipantResponse,
    ExamParticipantUpdate,
    ExamResponse,
    ExamUpdate,
    ExamWithDetails,
)
from app.services import ExamService

router = APIRouter(prefix="/api/v1/exams", tags=["exams"])


@router.get("", response_model=list[ExamResponse])
def list_exams(
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """List all exams."""
    return ExamService.get_exams(db, status=status, skip=skip, limit=limit)


@router.get("/{exam_id}", response_model=ExamWithDetails)
def get_exam(exam_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """Get exam by ID with participants and board members."""
    return ExamService.get_exam(db, exam_id)


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(exam_data: ExamCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Create a new exam (admin only)."""
    return ExamService.create_exam(db, exam_data, current_user.id)


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: str, exam_data: ExamUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)
):
    """Update exam (admin only)."""
    return ExamService.update_exam(db, exam_id, exam_data)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Delete exam (admin only)."""
    ExamService.delete_exam(db, exam_id)


# Participants
@router.post("/{exam_id}/participants", response_model=ExamParticipantResponse, status_code=status.HTTP_201_CREATED)
def add_participant(
    exam_id: str,
    participant_data: ExamParticipantCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Add participant to exam (admin only)."""
    participant_data.exam_id = exam_id
    return ExamService.add_participant(
        db,
        participant_data,
        current_user_id=current_user.id,
        current_user_role=current_user.role,
    )


@router.put("/participants/{participant_id}", response_model=ExamParticipantResponse)
def update_participant(
    participant_id: str,
    participant_data: ExamParticipantUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Update participant notes (instructor/admin) or status (admin only)."""
    update_data = participant_data.model_dump(exclude_unset=True)
    if "status" in update_data and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change participant status",
        )
    return ExamService.update_participant(db, participant_id, participant_data)


@router.delete("/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_participant(participant_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Remove participant from exam (admin only)."""
    ExamService.remove_participant(db, participant_id)


# Board Members
@router.post("/{exam_id}/board-members", response_model=ExamBoardMemberResponse, status_code=status.HTTP_201_CREATED)
def add_board_member(
    exam_id: str,
    member_data: ExamBoardMemberCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Add board member to exam (admin only)."""
    member_data.exam_id = exam_id
    return ExamService.add_board_member(db, member_data)


@router.delete("/board-members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_board_member(member_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Remove board member from exam (admin only)."""
    ExamService.remove_board_member(db, member_id)


@router.post("/participants/{participant_id}/promote", response_model=ExamParticipantResponse)
def promote_candidate(
    participant_id: str, new_belt_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)
):
    """Promote a candidate after successful exam (admin only)."""
    return ExamService.promote_candidate(db, participant_id, new_belt_id, promoted_by=current_user.id)
