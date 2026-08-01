from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    belts,
    checkin,
    contract_templates,
    contracts,
    dojos,
    event_series,
    events,
    exams,
    medical_exams,
    mensalidades,
    notifications,
    organizations,
    payments,
    plans,
    pre_checkins,
    reports,
    students,
    users,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Dojo Admin API",
    description="API for Aikido Dojo Management System",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(belts.router)
app.include_router(students.router)
app.include_router(events.router)
app.include_router(event_series.router)
app.include_router(checkin.router)
app.include_router(pre_checkins.router)
app.include_router(exams.router)
app.include_router(medical_exams.router)
app.include_router(plans.router)
app.include_router(mensalidades.router)
app.include_router(payments.router)
app.include_router(contract_templates.router)
app.include_router(contracts.router)
app.include_router(reports.router)
app.include_router(organizations.router)
app.include_router(dojos.router)
app.include_router(notifications.router)


@app.get("/")
async def root():
    return {"message": "Dojo Admin API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
