from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.belt import BeltResponse


class StudentBase(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    birth_date: datetime | None = None
    category: str
    current_belt_id: str
    dojo_id: str | None = None
    contract_name: str | None = None
    contract_cpf: str | None = None
    address_street: str | None = None
    address_neighborhood: str | None = None
    address_city: str | None = None
    address_zip: str | None = None
    classes_per_week: int | None = 2
    class_days: str | None = None


class StudentCreate(StudentBase):
    pin: str
    registration_number: str | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: datetime | None = None
    category: str | None = None
    current_belt_id: str | None = None
    pin: str | None = None
    is_active: bool | None = None
    registration_number: str | None = None
    contract_name: str | None = None
    contract_cpf: str | None = None
    address_street: str | None = None
    address_neighborhood: str | None = None
    address_city: str | None = None
    address_zip: str | None = None
    classes_per_week: int | None = None
    class_days: str | None = None


class StudentResponse(StudentBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    registration_number: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StudentWithBelt(StudentResponse):
    current_belt: BeltResponse | None = None
