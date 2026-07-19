from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Attendance,
    Belt,
    BeltPromotion,
    Exam,
    ExamBoardMember,
    ExamParticipant,
    Student,
)
from app.schemas import (
    ExamBoardMemberCreate,
    ExamCreate,
    ExamParticipantCreate,
    ExamParticipantUpdate,
    ExamUpdate,
)
from app.services.event_service import EventService
from app.services.student_service import StudentService


class ExamService:
    @staticmethod
    def get_exam(db: Session, exam_id: str) -> Exam | None:
        return db.query(Exam).filter(Exam.id == exam_id).first()

    @staticmethod
    def get_exams(db: Session, status: str | None = None, skip: int = 0, limit: int = 100) -> list[Exam]:
        query = db.query(Exam)
        if status:
            query = query.filter(Exam.status == status)
        return query.order_by(Exam.exam_date.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create_exam(db: Session, exam_data: ExamCreate, created_by: str) -> Exam:
        event = EventService.get_event(db, exam_data.event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event not found")

        belt = db.query(Belt).filter(Belt.id == exam_data.belt_id).first()
        if not belt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Belt not found")

        db_exam = Exam(
            **exam_data.model_dump(),
            created_by=created_by,
            status="scheduled",
        )
        db.add(db_exam)
        db.commit()
        db.refresh(db_exam)
        return db_exam

    @staticmethod
    def update_exam(db: Session, exam_id: str, exam_data: ExamUpdate) -> Exam:
        exam = ExamService.get_exam(db, exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        update_data = exam_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(exam, field, value)

        exam.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(exam)
        return exam

    @staticmethod
    def delete_exam(db: Session, exam_id: str) -> None:
        exam = ExamService.get_exam(db, exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        db.delete(exam)
        db.commit()

    @staticmethod
    def _check_eligibility(db: Session, student_id: str, target_belt_id: str) -> tuple[bool, list[str]]:
        """Check if student meets requirements to test for the target belt.
        Returns (is_eligible, list_of_reasons_if_not_eligible).
        """
        student = StudentService.get_student(db, student_id)
        if not student:
            return False, ["Student not found"]

        target_belt = db.query(Belt).filter(Belt.id == target_belt_id).first()
        if not target_belt:
            return False, ["Target belt not found"]

        last_promotion = StudentService.get_last_promotion(db, student_id)
        cutoff_date = last_promotion.promoted_at if last_promotion else student.created_at

        reasons: list[str] = []

        for req in target_belt.requirements:
            attendance_count = (
                db.query(Attendance)
                .join(Student, Attendance.student_id == Student.id)
                .filter(
                    Student.id == student_id,
                    Attendance.event.has(event_type_id=req.event_type_id),
                    Attendance.check_in_at >= cutoff_date,
                )
                .count()
            )

            if attendance_count < req.required_count:
                reasons.append(
                    f"Required {req.required_count}x '{req.description or req.event_type.name}', "
                    f"only {attendance_count} since last promotion"
                )

        return len(reasons) == 0, reasons

    # Participants
    @staticmethod
    def add_participant(
        db: Session,
        participant_data: ExamParticipantCreate,
        current_user_id: str,
        current_user_role: str,
    ) -> ExamParticipant:
        exam = ExamService.get_exam(db, participant_data.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        student = db.query(Student).filter(Student.id == participant_data.student_id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student not found")

        # Check for duplicate participant (same student + exam + role)
        existing_participant = (
            db.query(ExamParticipant)
            .filter(
                ExamParticipant.exam_id == participant_data.exam_id,
                ExamParticipant.student_id == participant_data.student_id,
                ExamParticipant.role == participant_data.role,
            )
            .first()
        )
        if existing_participant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student is already registered as a participant with this role in this exam",
            )

        is_eligible = True
        override_eligibility = participant_data.override_eligibility
        override_reason = participant_data.override_reason
        overridden_by: str | None = None

        if participant_data.role == "candidate":
            is_eligible, reasons = ExamService._check_eligibility(db, participant_data.student_id, exam.belt_id)

            if not is_eligible and not override_eligibility:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Student does not meet exam requirements",
                        "reasons": reasons,
                        "tip": "Set override_eligibility=true and override_reason to bypass",
                    },
                )

            if override_eligibility:
                if current_user_role not in ("admin", "instructor"):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only admins and instructors can override eligibility",
                    )
                if not override_reason:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="override_reason is required when override_eligibility=true",
                    )
                overridden_by = current_user_id

        participant_dict = participant_data.model_dump(exclude={"override_eligibility", "override_reason"})
        db_participant = ExamParticipant(
            **participant_dict,
            is_eligible=is_eligible,
            override_eligibility=override_eligibility,
            override_reason=override_reason if override_eligibility else None,
            overridden_by=overridden_by,
        )
        db.add(db_participant)
        db.commit()
        db.refresh(db_participant)
        return db_participant

    @staticmethod
    def update_participant(
        db: Session, participant_id: str, participant_data: ExamParticipantUpdate
    ) -> ExamParticipant:
        participant = db.query(ExamParticipant).filter(ExamParticipant.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

        update_data = participant_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(participant, field, value)

        participant.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(participant)
        return participant

    @staticmethod
    def remove_participant(db: Session, participant_id: str) -> None:
        participant = db.query(ExamParticipant).filter(ExamParticipant.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
        db.delete(participant)
        db.commit()

    # Board Members
    @staticmethod
    def add_board_member(db: Session, member_data: ExamBoardMemberCreate) -> ExamBoardMember:
        exam = ExamService.get_exam(db, member_data.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        from app.models import User

        user = db.query(User).filter(User.id == member_data.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

        db_member = ExamBoardMember(**member_data.model_dump())
        db.add(db_member)
        db.commit()
        db.refresh(db_member)
        return db_member

    @staticmethod
    def remove_board_member(db: Session, member_id: str) -> None:
        member = db.query(ExamBoardMember).filter(ExamBoardMember.id == member_id).first()
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board member not found")
        db.delete(member)
        db.commit()

    @staticmethod
    def promote_candidate(db: Session, participant_id: str, new_belt_id: str, promoted_by: str) -> ExamParticipant:
        """Promote a candidate after successful exam, creating BeltPromotion record."""
        participant = db.query(ExamParticipant).filter(ExamParticipant.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

        if participant.role != "candidate":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only candidates can be promoted")

        student = participant.student
        student.current_belt_id = new_belt_id

        promotion = BeltPromotion(
            student_id=student.id,
            belt_id=new_belt_id,
            promoted_at=datetime.now(UTC),
            promoted_by=promoted_by,
            exam_id=participant.exam_id,
            notes="Promoted via exam",
        )
        db.add(promotion)

        participant.status = "approved"
        participant.updated_at = datetime.now(UTC)

        db.commit()
        db.refresh(participant)
        return participant
