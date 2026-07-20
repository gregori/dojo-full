from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, belts, checkin, events, exams, medical_exams, organizations, pre_checkins, students, users
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
app.include_router(checkin.router)
app.include_router(pre_checkins.router)
app.include_router(exams.router)
app.include_router(medical_exams.router)
app.include_router(organizations.router)


@app.get("/")
async def root():
    return {"message": "Dojo Admin API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
