from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_admin
from app.schemas import (
    DojoCreate,
    DojoResponse,
    DojoUpdate,
    OrganizationCreate,
    OrganizationResponse,
)

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    from app.models import Organization

    return db.query(Organization).all()


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_data: OrganizationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)
):
    from app.models import Organization

    db_org = Organization(**org_data.model_dump())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org


@router.get("/{org_id}/dojos", response_model=list[DojoResponse])
def list_dojos(org_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    from app.models import Dojo

    return db.query(Dojo).filter(Dojo.organization_id == org_id).all()


@router.post("/{org_id}/dojos", response_model=DojoResponse, status_code=status.HTTP_201_CREATED)
def create_dojo(
    org_id: str, dojo_data: DojoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)
):
    from app.models import Dojo

    dojo_data.organization_id = org_id
    db_dojo = Dojo(**dojo_data.model_dump())
    db.add(db_dojo)
    db.commit()
    db.refresh(db_dojo)
    return db_dojo


@router.put("/{org_id}/dojos/{dojo_id}", response_model=DojoResponse)
def update_dojo(
    org_id: str,
    dojo_id: str,
    dojo_data: DojoUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    from app.models import Dojo

    db_dojo = db.query(Dojo).filter(Dojo.id == dojo_id, Dojo.organization_id == org_id).first()
    if not db_dojo:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Dojo not found")
    for key, value in dojo_data.model_dump(exclude_unset=True).items():
        setattr(db_dojo, key, value)
    db.commit()
    db.refresh(db_dojo)
    return db_dojo


@router.delete("/{org_id}/dojos/{dojo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dojo(org_id: str, dojo_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    from app.models import Dojo

    db_dojo = db.query(Dojo).filter(Dojo.id == dojo_id, Dojo.organization_id == org_id).first()
    if not db_dojo:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Dojo not found")
    db.delete(db_dojo)
    db.commit()
