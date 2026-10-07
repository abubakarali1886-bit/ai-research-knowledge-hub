"""
AI Research Knowledge Hub - Main Application Entry Point
"""
from fastapi import FastAPI
from sqlalchemy import inspect, text
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents
from app.api import search
from app.api import chat
from app.api import summarization
from app.api import auth
from app.api import dashboard
from app.api import admin
from app.db.database import Base, engine, SessionLocal
from app.core.security import ensure_default_admin
from app.models import ai_question, audit_log, document, user

app = FastAPI(
    title="AI Research Knowledge Hub",
    description="Central Banking Research Knowledge Management System",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(summarization.router)
app.include_router(dashboard.router)


@app.on_event("startup")
async def create_missing_tables():
    Base.metadata.create_all(bind=engine)
    tables = inspect(engine).get_table_names()
    if "audit_logs" in tables:
        audit_columns = {column["name"] for column in inspect(engine).get_columns("audit_logs")}
        if "reviewed" not in audit_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE audit_logs ADD COLUMN reviewed BOOLEAN DEFAULT false NOT NULL"))
    # Additive compatibility for databases created before publication periods.
    if "documents" in tables:
        columns = {column["name"] for column in inspect(engine).get_columns("documents")}
        if "publication_period" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE documents ADD COLUMN publication_period VARCHAR(32)"))
        if "uploader_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE documents ADD COLUMN uploader_id INTEGER REFERENCES users(id) ON DELETE SET NULL"))
        additive_columns = {
            "authors_json": "TEXT",
            "author_type": "VARCHAR(30) DEFAULT 'unknown'",
            "author_confidence": "DOUBLE PRECISION",
            "author_source": "VARCHAR(255)",
            "metadata_review_status": "VARCHAR(30) DEFAULT 'needs_review'",
        }
        for column_name, column_type in additive_columns.items():
            if column_name not in columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE documents ADD COLUMN {column_name} {column_type}"))

    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()

@app.get("/")
async def root():
    return {
        "message": "AI Research Knowledge Hub API",
        "status": "running",
        "version": "0.1.0"
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "backend",
        "database": "connected"
    }