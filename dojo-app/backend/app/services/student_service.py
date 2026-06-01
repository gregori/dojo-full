from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models import Attendance, Belt, BeltPromotion, Dojo, Exam, ExamParticipant, Student
from app.schemas import StudentCreate, StudentUpdate


class StudentService:
    @staticmethod
    def _generate_registration_number(db: Session, dojo_id: str | None = None) -> str:
        """Generate next registration number in format <seq:03d><year:02d><dojo_code>."""
        current_year = datetime.now(UTC).year
        year_suffix = str(current_year)[-2:]

        total_students = db.query(Student).count()
        next_seq = total_students + 1

        dojo_code = 1
        if dojo_id:
            dojo = db.query(Dojo).filter(Dojo.id == dojo_id).first()
            if dojo:
                dojo_code = dojo.code

        return f"{next_seq:03d}{year_suffix}{dojo_code}"

    @staticmethod
    def get_student(db: Session, student_id: str) -> Student | None:
        return db.query(Student).filter(Student.id == student_id).first()

    @staticmethod
    def get_student_by_registration(db: Session, registration_number: str) -> Student | None:
        return db.query(Student).filter(Student.registration_number == registration_number).first()

    @staticmethod
    def get_students(
        db: Session, category: str | None = None, is_active: bool | None = None, skip: int = 0, limit: int = 100
    ) -> list[Student]:
        query = db.query(Student)
        if category:
            query = query.filter(Student.category == category)
        if is_active is not None:
            query = query.filter(Student.is_active == is_active)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create_student(db: Session, student_data: StudentCreate, created_by: str | None = None) -> Student:
        # Validate belt exists
        belt = db.query(Belt).filter(Belt.id == student_data.current_belt_id).first()
        if not belt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid belt_id")

        if student_data.registration_number:
            existing = db.query(Student).filter(Student.registration_number == student_data.registration_number).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Registration number {student_data.registration_number} already in use",
                )
            registration_number = student_data.registration_number
        else:
            registration_number = StudentService._generate_registration_number(db, student_data.dojo_id)

        db_student = Student(
            registration_number=registration_number,
            full_name=student_data.full_name,
            email=student_data.email,
            phone=student_data.phone,
            birth_date=student_data.birth_date,
            category=student_data.category,
            current_belt_id=student_data.current_belt_id,
            dojo_id=student_data.dojo_id,
            pin=get_password_hash(student_data.pin),
            is_active=True,
            contract_name=student_data.contract_name,
            contract_cpf=student_data.contract_cpf,
            address_street=student_data.address_street,
            address_neighborhood=student_data.address_neighborhood,
            address_city=student_data.address_city,
            address_zip=student_data.address_zip,
            classes_per_week=student_data.classes_per_week,
            class_days=student_data.class_days,
        )
        db.add(db_student)
        db.flush()

        promotion = BeltPromotion(
            student_id=db_student.id,
            belt_id=belt.id,
            promoted_at=datetime.now(UTC),
            promoted_by=created_by,
            notes="Initial belt assignment",
        )
        db.add(promotion)

        db.commit()
        db.refresh(db_student)
        return db_student

    @staticmethod
    def update_student(db: Session, student_id: str, student_data: StudentUpdate) -> Student:
        student = StudentService.get_student(db, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        update_data = student_data.model_dump(exclude_unset=True)

        # Hash PIN if being updated
        if "pin" in update_data:
            update_data["pin"] = get_password_hash(update_data["pin"])

        for field, value in update_data.items():
            setattr(student, field, value)

        student.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def deactivate_student(db: Session, student_id: str) -> Student:
        return StudentService.update_student(db, student_id, StudentUpdate(is_active=False))

    @staticmethod
    def get_last_promotion(db: Session, student_id: str) -> BeltPromotion | None:
        """Get the most recent belt promotion for a student."""
        return (
            db.query(BeltPromotion)
            .filter(BeltPromotion.student_id == student_id)
            .order_by(BeltPromotion.promoted_at.desc())
            .first()
        )

    @staticmethod
    def get_student_progress(db: Session, student_id: str) -> dict:
        """Calculate student's progress towards next belt (filtered by last promotion)."""
        student = StudentService.get_student(db, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        current_belt = student.current_belt
        if not current_belt:
            return {"error": "No belt assigned"}

        last_promotion = StudentService.get_last_promotion(db, student_id)
        cutoff_date = last_promotion.promoted_at if last_promotion else student.created_at

        # Get next belt
        next_belt = (
            db.query(Belt)
            .filter(Belt.category == current_belt.category, Belt.sort_order > current_belt.sort_order)
            .order_by(Belt.sort_order)
            .first()
        )

        if not next_belt:
            return {
                "current_belt": current_belt.name,
                "next_belt": None,
                "message": "Você está na faixa mais alta!",
                "requirements": [],
                "last_promotion_date": cutoff_date.isoformat() if cutoff_date else None,
            }

        requirements = []
        for req in next_belt.requirements:
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

            requirements.append(
                {
                    "description": req.description or req.event_type.name,
                    "required": req.required_count,
                    "completed": attendance_count,
                    "remaining": max(0, req.required_count - attendance_count),
                    "is_complete": attendance_count >= req.required_count,
                }
            )

        total_required = len(requirements)
        total_complete = sum(1 for r in requirements if r["is_complete"])

        return {
            "current_belt": current_belt.name,
            "next_belt": next_belt.name,
            "requirements": requirements,
            "last_promotion_date": cutoff_date.isoformat() if cutoff_date else None,
            "overall_progress": {
                "total_required": total_required,
                "total_complete": total_complete,
                "percentage": (total_complete / total_required * 100) if total_required > 0 else 0,
            },
        }

    @staticmethod
    def get_student_exam_history(db: Session, student_id: str) -> list[dict]:
        """Get exam history for a student."""
        student = StudentService.get_student(db, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        participations = db.query(ExamParticipant).filter(ExamParticipant.student_id == student_id).all()

        result = []
        for p in participations:
            exam = db.query(Exam).filter(Exam.id == p.exam_id).first()
            result.append(
                {
                    "exam_id": p.exam_id,
                    "student_id": p.student_id,
                    "role": p.role,
                    "status": p.status,
                    "notes": p.notes,
                    "is_eligible": p.is_eligible,
                    "exam_date": exam.exam_date.isoformat() if exam else None,
                    "belt_name": exam.belt.name if exam and exam.belt else None,
                    "event_title": exam.event.title if exam and exam.event else None,
                }
            )
        return result
