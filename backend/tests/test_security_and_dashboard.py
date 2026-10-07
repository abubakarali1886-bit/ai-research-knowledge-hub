import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.dashboard import get_dashboard_summary
from app.api.admin import export_activity_report, get_activity_history, get_activity_notifications
from app.core.security import decode_access_token, ensure_default_admin, get_password_hash, verify_password
from app.db.database import Base
from app.models.ai_question import AIQuestion
from app.models.audit_log import AuditLog
from app.models.document import Category, Document
from app.models.saved_research import SavedResearch
from app.models.user import User, UserRole
from app.services.document_processor import DocumentProcessor


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_password_hashing_and_invalid_token():
    password_hash = get_password_hash("strong-password-123")
    assert verify_password("strong-password-123", password_hash)
    assert not verify_password("wrong-password", password_hash)
    assert decode_access_token("not-a-jwt") == {}


def test_default_admin_is_bootstrapped_when_database_is_empty():
    db = make_session()

    ensure_default_admin(db)

    admin = db.query(User).filter(User.username == "admin").first()
    assert admin is not None
    assert admin.role == UserRole.ADMIN
    assert verify_password("admin123", admin.password_hash)


def test_dashboard_summary_uses_real_empty_database_values():
    db = make_session()
    user = User(
        username="viewer",
        email="viewer@example.com",
        password_hash="unused",
        role=UserRole.VIEWER,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()

    summary = asyncio.run(get_dashboard_summary(db, user))

    assert summary["stats"]["total_documents"] == 0
    assert summary["stats"]["processed_documents"] == 0
    assert summary["stats"]["research_topics"] == 0
    assert summary["stats"]["ai_questions"] == 0
    assert summary["topics"] == []


def test_dashboard_summary_reports_categories_and_topics():
    db = make_session()
    user = User(username="researcher", email="researcher@example.com", password_hash="unused", role=UserRole.RESEARCHER, is_active=True, is_verified=True)
    category = Category(name="Monetary Policy", is_active=True)
    db.add_all([user, category])
    db.commit()
    document = Document(title="Policy study", file_path="/tmp/policy.pdf", file_name="policy.pdf", category=category, is_active=True)
    db.add(document)
    db.commit()

    summary = asyncio.run(get_dashboard_summary(db, user))

    assert summary["categories"] == [{"label": "Monetary Policy", "count": 1}]


def test_dashboard_questions_are_scoped_to_current_user():
    db = make_session()
    first_user = User(username="first", email="first@example.com", password_hash="unused", role=UserRole.VIEWER, is_active=True, is_verified=True)
    second_user = User(username="second", email="second@example.com", password_hash="unused", role=UserRole.VIEWER, is_active=True, is_verified=True)
    db.add_all([first_user, second_user])
    db.commit()
    db.add_all([
        AIQuestion(question="first question", user_id=first_user.id, created_at=datetime.now(timezone.utc)),
        AIQuestion(question="second question", user_id=second_user.id, created_at=datetime.now(timezone.utc)),
    ])
    db.commit()

    summary = asyncio.run(get_dashboard_summary(db, first_user))

    assert summary["stats"]["ai_questions"] == 1


def test_opening_admin_activity_marks_notifications_reviewed():
    db = make_session()
    admin = User(username="admin", email="admin@example.com", password_hash="unused", role=UserRole.ADMIN, is_active=True, is_verified=True)
    db.add(admin)
    db.commit()
    entry = AuditLog(
        user_id=admin.id,
        username="admin",
        user_role="admin",
        action="Login",
        resource="auth",
        date="2026-09-18",
        time="08:15:00",
    )
    db.add(entry)
    db.commit()

    asyncio.run(get_activity_history(date=None, start_date=None, end_date=None, limit=200, db=db, current_user=admin))
    notifications = asyncio.run(get_activity_notifications(db=db, current_user=admin))

    assert db.query(AuditLog).filter(AuditLog.id == entry.id).one().reviewed is True
    assert notifications["unreviewed_count"] == 0


def test_admin_activity_export_returns_pdf():
    db = make_session()
    admin = User(username="admin", email="admin@example.com", password_hash="unused", role=UserRole.ADMIN, is_active=True, is_verified=True)
    db.add(admin)
    db.commit()

    response = asyncio.run(export_activity_report(
        date=None,
        start_date=None,
        end_date=None,
        db=db,
        current_user=admin,
    ))

    async def read_response():
        return b"".join([chunk async for chunk in response.body_iterator])

    pdf = asyncio.run(read_response())
    assert response.media_type == "application/pdf"
    assert pdf.startswith(b"%PDF-")


def test_audit_log_tracks_review_state_without_deleting_history():
    entry = AuditLog(
        username="admin",
        user_role="admin",
        action="Login",
        resource="auth",
        date="2026-09-18",
        time="08:15:00",
        details="Admin signed in",
    )

    assert entry.reviewed is False
    assert entry.username == "admin"
    assert entry.action == "Login"


def test_upload_cap_is_50_mb_and_audit_log_model_exists():
    processor = DocumentProcessor()
    assert processor.MAX_FILE_SIZE == 50 * 1024 * 1024
    assert processor.validate_file("example.pdf", 50 * 1024 * 1024, "application/pdf")[0]
    assert not processor.validate_file("example.pdf", 50 * 1024 * 1024 + 1, "application/pdf")[0]
    assert AuditLog.__tablename__ == "audit_logs"
