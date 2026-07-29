from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Belt, BeltPromotion, BeltRequirement, Exam, Student
from app.schemas import BeltCreate, BeltRequirementCreate, BeltRequirementUpdate, BeltUpdate


class BeltService:
    @staticmethod
    def get_belt(db: Session, belt_id: str) -> Belt | None:
        return db.query(Belt).filter(Belt.id == belt_id).first()

    @staticmethod
    def get_belts(db: Session, category: str | None = None, skip: int = 0, limit: int = 100) -> list[Belt]:
        query = db.query(Belt)
        if category:
            query = query.filter(Belt.category == category)
        return query.order_by(Belt.sort_order).offset(skip).limit(limit).all()

    @staticmethod
    def create_belt(db: Session, belt_data: BeltCreate) -> Belt:
        db_belt = Belt(**belt_data.model_dump())
        db.add(db_belt)
        db.commit()
        db.refresh(db_belt)
        return db_belt

    @staticmethod
    def update_belt(db: Session, belt_id: str, belt_data: BeltUpdate) -> Belt:
        belt = BeltService.get_belt(db, belt_id)
        if not belt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Belt not found")

        update_data = belt_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(belt, field, value)

        db.commit()
        db.refresh(belt)
        return belt

    @staticmethod
    def delete_belt(db: Session, belt_id: str) -> None:
        belt = BeltService.get_belt(db, belt_id)
        if not belt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Belt not found")

        if db.query(Student).filter(Student.current_belt_id == belt_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Belt is assigned to one or more students and cannot be deleted",
            )
        if db.query(BeltPromotion).filter(BeltPromotion.belt_id == belt_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Belt has promotion history and cannot be deleted",
            )
        if db.query(Exam).filter(Exam.belt_id == belt_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Belt has exams associated with it and cannot be deleted",
            )
        if db.query(BeltRequirement).filter(BeltRequirement.belt_id == belt_id).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Belt has requirements defined and cannot be deleted",
            )

        db.delete(belt)
        db.commit()

    # Belt Requirements
    @staticmethod
    def create_requirement(db: Session, req_data: BeltRequirementCreate) -> BeltRequirement:
        db_req = BeltRequirement(**req_data.model_dump())
        db.add(db_req)
        db.commit()
        db.refresh(db_req)
        return db_req

    @staticmethod
    def get_requirements_by_belt(db: Session, belt_id: str) -> list[BeltRequirement]:
        return db.query(BeltRequirement).filter(BeltRequirement.belt_id == belt_id).all()

    @staticmethod
    def delete_requirement(db: Session, requirement_id: str) -> None:
        req = db.query(BeltRequirement).filter(BeltRequirement.id == requirement_id).first()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
        db.delete(req)
        db.commit()

    @staticmethod
    def update_requirement(db: Session, requirement_id: str, req_data: BeltRequirementUpdate) -> BeltRequirement:
        req = db.query(BeltRequirement).filter(BeltRequirement.id == requirement_id).first()
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")

        update_data = req_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(req, field, value)

        db.commit()
        db.refresh(req)
        return req
