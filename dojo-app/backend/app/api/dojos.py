from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas import DojoResponse

router = APIRouter(prefix="/api/v1/dojos", tags=["dojos"])


@router.get("", response_model=list[DojoResponse])
def list_all_dojos(db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """List all dojos across every organization, for populating selection dropdowns."""
    from app.models import Dojo

    return db.query(Dojo).all()
