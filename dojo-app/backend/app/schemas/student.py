from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.belt import BeltResponse


class StudentBase(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[datetime] = None
    category: str
    current_belt_id: str
    dojo_id: Optional[str] = None
    contract_name: Optional[str] = None
    contract_cpf: Optional[str] = None
    address_street: Optional[str] = None
    address_neighborhood: Optional[str] = None
    address_city: Optional[str] = None
    address_zip: Optional[str] = None
    classes_per_week: Optional[int] = 2
    class_days: Optional[str] = None


class StudentCreate(StudentBase):
    pin: str
    registration_number: Optional[str] = None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[datetime] = None
    category: Optional[str] = None
    current_belt_id: Optional[str] = None
    pin: Optional[str] = None
    is_active: Optional[bool] = None
    contract_name: Optional[str] = None
    contract_cpf: Optional[str] = None
    address_street: Optional[str] = None
    address_neighborhood: Optional[str] = None
    address_city: Optional[str] = None
    address_zip: Optional[str] = None
    classes_per_week: Optional[int] = None
    class_days: Optional[str] = None


class StudentResponse(StudentBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    registration_number: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StudentWithBelt(StudentResponse):
    current_belt: Optional[BeltResponse] = None
