from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine
from app.models import Base
from app.api import auth, users, belts, students, events, checkin, exams, organizations

settings = get_settings()

Base.metadata.create_all(bind=engine)

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
app.include_router(exams.router)
app.include_router(organizations.router)


@app.get("/")
async def root():
    return {"message": "Dojo Admin API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
