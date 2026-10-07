from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from datetime import date, datetime, timedelta, timezone
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape
from sqlalchemy import cast, Date, func
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.database import get_db
from app.models.ai_question import AIQuestion
from app.models.document import Category, Document, DocumentType, ResearchTopic, document_topic
from app.models.saved_research import SavedResearch
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.core.audit import log_activity
from app.core.audit import EAST_AFRICA_TIMEZONE, to_east_africa_time

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    is_active: bool


class AdminUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    role: UserRole = UserRole.VIEWER


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == payload.username.strip()).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    if db.query(User).filter(User.email == str(payload.email)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    from app.core.security import get_password_hash

    user = User(
        username=payload.username.strip(),
        email=str(payload.email),
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        role=payload.role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_activity(db, current_user, "Created User", resource=user.username, details=f"Created {user.role.value} user account")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }


@router.get("/dashboard")
async def admin_dashboard_summary(
    days: int = Query(30, ge=1, le=3650),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    active_documents = Document.is_active.is_(True)
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    role_breakdown = (
        db.query(User.role, func.count(User.id))
        .group_by(User.role)
        .all()
    )
    recent_users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .limit(5)
        .all()
    )
    total_documents = db.query(func.count(Document.id)).filter(active_documents).scalar() or 0
    processed_documents = db.query(func.count(Document.id)).filter(active_documents, Document.processing_status == "completed").scalar() or 0
    pending_documents = db.query(func.count(Document.id)).filter(active_documents, Document.processing_status.in_(["pending", "processing"])).scalar() or 0
    failed_documents = db.query(func.count(Document.id)).filter(active_documents, Document.processing_status == "failed").scalar() or 0
    total_topics = db.query(func.count(ResearchTopic.id)).scalar() or 0
    total_ai_questions = db.query(func.count(AIQuestion.id)).scalar() or 0
    total_saved_research = db.query(func.count(SavedResearch.id)).scalar() or 0
    processing_statuses = (
        db.query(Document.processing_status, func.count(Document.id))
        .filter(active_documents)
        .group_by(Document.processing_status)
        .order_by(Document.processing_status.asc())
        .all()
    )

    documents_by_year = (
        db.query(Document.publication_year, func.count(Document.id))
        .filter(active_documents)
        .group_by(Document.publication_year)
        .order_by(Document.publication_year.asc())
        .all()
    )
    documents_by_type = (
        db.query(DocumentType.name, func.count(Document.id))
        .join(Document, Document.document_type_id == DocumentType.id)
        .filter(active_documents, DocumentType.is_active.is_(True))
        .group_by(DocumentType.id, DocumentType.name)
        .order_by(func.count(Document.id).desc(), DocumentType.name.asc())
        .all()
    )
    documents_by_topic = (
        db.query(ResearchTopic.name, func.count(Document.id))
        .join(document_topic, document_topic.c.topic_id == ResearchTopic.id)
        .join(Document, Document.id == document_topic.c.document_id)
        .filter(active_documents)
        .group_by(ResearchTopic.id, ResearchTopic.name)
        .order_by(func.count(Document.id).desc(), ResearchTopic.name.asc())
        .all()
    )
    documents_by_category = (
        db.query(Category.name, func.count(Document.id))
        .join(Document, Document.category_id == Category.id)
        .filter(active_documents, Category.is_active.is_(True))
        .group_by(Category.id, Category.name)
        .order_by(func.count(Document.id).desc(), Category.name.asc())
        .all()
    )
    east_africa_today = datetime.now(EAST_AFRICA_TIMEZONE).date()
    question_start = east_africa_today - timedelta(days=days - 1)
    question_history = (
        db.query(cast(AIQuestion.created_at, Date), func.count(AIQuestion.id))
        .filter(cast(AIQuestion.created_at, Date) >= question_start)
        .group_by(cast(AIQuestion.created_at, Date))
        .order_by(cast(AIQuestion.created_at, Date).asc())
        .all()
    )
    question_counts = {day: count for day, count in question_history}
    today = east_africa_today
    questions_over_time = [
        {"date": str(today - timedelta(days=offset)), "count": question_counts.get(today - timedelta(days=offset), 0)}
        for offset in range(days - 1, -1, -1)
    ]
    recent_documents = (
        db.query(Document)
        .filter(active_documents)
        .order_by(Document.created_at.desc())
        .limit(5)
        .all()
    )

    utc_start = datetime.combine(question_start, datetime.min.time(), tzinfo=EAST_AFRICA_TIMEZONE).astimezone(timezone.utc)
    activity_entries = db.query(AuditLog).filter(AuditLog.timestamp >= utc_start).all()
    activity_counts = {}
    for entry in activity_entries:
        activity_date = to_east_africa_time(entry.timestamp).date().isoformat()
        activity_counts[activity_date] = activity_counts.get(activity_date, 0) + 1
    activity_per_day = [
        {"date": str(today - timedelta(days=offset)), "count": activity_counts.get(str(today - timedelta(days=offset)), 0)}
        for offset in range(days - 1, -1, -1)
    ]

    return {
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "admins": sum(count for role, count in role_breakdown if role == UserRole.ADMIN),
            "researchers": sum(count for role, count in role_breakdown if role == UserRole.RESEARCHER),
            "viewers": sum(count for role, count in role_breakdown if role == UserRole.VIEWER),
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "pending_documents": pending_documents,
            "failed_documents": failed_documents,
            "research_topics": total_topics,
            "ai_questions": total_ai_questions,
            "saved_research": total_saved_research,
        },
        "role_breakdown": [
            {"role": role.value if hasattr(role, 'value') else str(role), "count": count}
            for role, count in role_breakdown
        ],
        "recent_users": [
            {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "last_login": user.last_login,
            }
            for user in recent_users
        ],
        "documents_by_year": [
            {"label": str(year) if year else "Unknown", "count": count}
            for year, count in documents_by_year
        ],
        "documents_by_type": [
            {"label": name, "count": count}
            for name, count in documents_by_type
        ],
        "documents_by_topic": [
            {"label": name, "count": count}
            for name, count in documents_by_topic
        ],
        "categories": [
            {"label": name, "count": count}
            for name, count in documents_by_category
        ],
        "questions_over_time": questions_over_time,
        "activity_per_day": activity_per_day,
        "processing_status": [
            {"label": status or "unknown", "count": count}
            for status, count in processing_statuses
        ],
        "recent_documents": [
            {
                "id": document.id,
                "title": document.title or document.file_name,
                "author": document.author,
                "authors": json.loads(document.authors_json) if document.authors_json else ([document.author] if document.author else []),
                "author_type": document.author_type or "unknown",
                "author_confidence": document.author_confidence,
                "author_source": document.author_source,
                "publication_year": document.publication_year,
                "file_type": document.file_type,
                "category": document.category.name if document.category else None,
                "department": document.category.name if document.category else None,
                "document_type": document.file_type.upper() if document.file_type else None,
                "topics": [topic.name for topic in document.topics],
                "processing_status": document.processing_status,
                "processing_error": document.processing_error,
                "uploaded_by": document.uploader.username if document.uploader else None,
                "uploader_email": document.uploader.email if document.uploader else None,
                "created_at": document.created_at,
            }
            for document in recent_documents
        ],
        "recent_activity": [
            {
                "kind": "activity",
                "text": f"{entry.username or 'System'} - {entry.action} - {entry.resource or 'Resource'}",
                "timestamp": to_east_africa_time(entry.timestamp).isoformat(),
                "date": to_east_africa_time(entry.timestamp).strftime("%Y-%m-%d"),
                "time": to_east_africa_time(entry.timestamp).strftime("%H:%M:%S"),
            }
            for entry in db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(10)
            .all()
        ],
    }


def _serialize_activity(entry: AuditLog) -> dict:
    timestamp = to_east_africa_time(entry.timestamp)
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "user": entry.username or "System",
        "role": entry.user_role or "system",
        "activity": entry.action,
        "resource": entry.resource or "—",
        "details": entry.details or "—",
        "date": entry.date or timestamp.strftime("%Y-%m-%d"),
        "time": entry.time or timestamp.strftime("%H:%M:%S"),
        "timestamp": timestamp.isoformat(),
        "status": "Viewed" if entry.reviewed else "New",
        "reviewed": bool(entry.reviewed),
    }


@router.get("/activity")
async def get_activity_history(
    date: str | None = Query(default=None, alias="date"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    db.query(AuditLog).filter(AuditLog.reviewed.is_(False)).update(
        {AuditLog.reviewed: True}, synchronize_session=False
    )
    db.commit()
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if date:
        query = query.filter(AuditLog.date == date)
    elif start_date or end_date:
        if start_date:
            query = query.filter(AuditLog.date >= start_date)
        if end_date:
            query = query.filter(AuditLog.date <= end_date)
    rows = query.all() if date else query.limit(limit).all()
    return {
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(rows),
        "items": [_serialize_activity(entry) for entry in rows],
    }


@router.get("/activity/notifications")
async def get_activity_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    unreviewed_query = db.query(AuditLog).filter(AuditLog.reviewed.is_(False))
    unreviewed_count = unreviewed_query.with_entities(func.count(AuditLog.id)).scalar() or 0
    notifications = (
        unreviewed_query
        .order_by(AuditLog.timestamp.desc())
        .limit(100)
        .all()
    )
    return {
        "count": unreviewed_count,
        "unreviewed_count": unreviewed_count,
        "items": [_serialize_activity(entry) for entry in notifications],
    }


@router.patch("/activity/{activity_id}/review")
async def mark_activity_reviewed(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    activity = db.query(AuditLog).filter(AuditLog.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    activity.reviewed = True
    db.commit()
    return {"message": "Activity marked as reviewed", "activity_id": activity.id, "reviewed": True}


def _build_system_report(db: Session, rows: list[AuditLog], date: str | None, start_date: str | None, end_date: str | None):
    """Build a readable system-wide report from live database statistics."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    verified_users = db.query(func.count(User.id)).filter(User.is_verified.is_(True)).scalar() or 0
    role_totals = dict(db.query(User.role, func.count(User.id)).group_by(User.role).all())
    total_documents = db.query(func.count(Document.id)).scalar() or 0
    active_documents = db.query(func.count(Document.id)).filter(Document.is_active.is_(True)).scalar() or 0
    processed_documents = db.query(func.count(Document.id)).filter(Document.processing_status == "completed").scalar() or 0
    pending_documents = db.query(func.count(Document.id)).filter(Document.processing_status.in_(["pending", "processing"])).scalar() or 0
    failed_documents = db.query(func.count(Document.id)).filter(Document.processing_status == "failed").scalar() or 0
    total_topics = db.query(func.count(ResearchTopic.id)).scalar() or 0
    total_categories = db.query(func.count(Category.id)).filter(Category.is_active.is_(True)).scalar() or 0
    total_types = db.query(func.count(DocumentType.id)).filter(DocumentType.is_active.is_(True)).scalar() or 0
    total_questions = db.query(func.count(AIQuestion.id)).scalar() or 0
    total_saved = db.query(func.count(SavedResearch.id)).scalar() or 0
    unreviewed = db.query(func.count(AuditLog.id)).filter(AuditLog.reviewed.is_(False)).scalar() or 0

    processing_totals = dict(
        db.query(Document.processing_status, func.count(Document.id))
        .group_by(Document.processing_status)
        .all()
    )
    category_totals = db.query(Category.name, func.count(Document.id)).join(
        Document, Document.category_id == Category.id, isouter=True
    ).group_by(Category.id, Category.name).order_by(func.count(Document.id).desc()).limit(12).all()
    topic_totals = db.query(ResearchTopic.name, func.count(document_topic.c.document_id)).join(
        document_topic, document_topic.c.topic_id == ResearchTopic.id, isouter=True
    ).group_by(ResearchTopic.id, ResearchTopic.name).order_by(func.count(document_topic.c.document_id).desc()).limit(12).all()

    activity_totals = {}
    activity_roles = {}
    activity_users = {}
    daily_totals = {}
    reviewed_count = 0
    for record in rows:
        activity_totals[record.action] = activity_totals.get(record.action, 0) + 1
        activity_roles[record.user_role or "system"] = activity_roles.get(record.user_role or "system", 0) + 1
        activity_users[record.username or "System"] = activity_users.get(record.username or "System", 0) + 1
        activity_day = record.date or to_east_africa_time(record.timestamp).strftime("%Y-%m-%d")
        daily_totals[activity_day] = daily_totals.get(activity_day, 0) + 1
        reviewed_count += int(bool(record.reviewed))

    period = date or (f"{start_date or 'Beginning'} to {end_date or 'Present'}" if start_date or end_date else "All available audit history")
    generated_at = datetime.now(EAST_AFRICA_TIMEZONE).strftime("%d %B %Y, %H:%M:%S")
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=34, leftMargin=34, topMargin=48, bottomMargin=42,
                                 title="AI Research Knowledge Hub - System Report", author="AI Research Knowledge Hub")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, alignment=1, textColor=colors.HexColor("#17324d"), spaceAfter=5)
    subtitle_style = ParagraphStyle("ReportSubtitle", parent=styles["Normal"], fontSize=10, leading=14, alignment=1, textColor=colors.HexColor("#68747d"), spaceAfter=16)
    heading_style = ParagraphStyle("ReportHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#17324d"), spaceBefore=12, spaceAfter=7, keepWithNext=True)
    body_style = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontSize=8.8, leading=13, textColor=colors.HexColor("#30383d"), spaceAfter=5)
    small_style = ParagraphStyle("ReportSmall", parent=styles["BodyText"], fontSize=7.2, leading=9.5, textColor=colors.HexColor("#39444b"))

    def text(value):
        return escape(str(value if value is not None else "-"))

    def metric_table(metrics):
        rows_data = [[Paragraph(f"<b>{text(label)}</b>", small_style), Paragraph(text(value), small_style)] for label, value in metrics]
        return _build_table([["Metric", "Value"]] + rows_data, widths=[300, 180])

    story = [
        Paragraph("AI RESEARCH KNOWLEDGE HUB", title_style),
        Paragraph("COMPREHENSIVE SYSTEM STATISTICS REPORT", subtitle_style),
        Table([[Paragraph("Reporting period", small_style), Paragraph(text(period), small_style), Paragraph("Generated", small_style), Paragraph(text(generated_at), small_style)]], colWidths=[82, 170, 62, 170], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3f5")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8d4da")), ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d8e0e4")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7)])),
        Spacer(1, 14),
        Paragraph("1. Executive Summary", heading_style),
        Paragraph(text(f"This report presents a consolidated view of the knowledge hub. It covers {total_users} registered users, {active_documents} active research documents, {total_questions} AI questions, {total_saved} saved research items, and {len(rows)} audit activities in the selected reporting period. Audit records are historical and are not removed when reviewed."), body_style),
        metric_table([["Registered users", total_users], ["Active users", active_users], ["Verified users", verified_users], ["Active documents", active_documents], ["Completed processing", processed_documents], ["AI questions", total_questions], ["Saved research items", total_saved], ["Unreviewed audit activities", unreviewed]]),
        Spacer(1, 12),
        Paragraph("2. User and Access Statistics", heading_style),
        metric_table([["Administrators", role_totals.get(UserRole.ADMIN, 0)], ["Researchers", role_totals.get(UserRole.RESEARCHER, 0)], ["Viewers", role_totals.get(UserRole.VIEWER, 0)], ["Inactive accounts", total_users - active_users]]),
        Spacer(1, 12),
        Paragraph("3. Research Document and Processing Statistics", heading_style),
        metric_table([["All documents", total_documents], ["Active documents", active_documents], ["Completed", processed_documents], ["Pending / processing", pending_documents], ["Failed", failed_documents], ["Active categories", total_categories], ["Active document types", total_types], ["Research topics", total_topics]]),
        Spacer(1, 8),
        Paragraph("Document processing status", heading_style),
        _build_table([["Status", "Documents"]] + [[text(key or "Unknown"), str(value)] for key, value in sorted(processing_totals.items())], widths=[300, 180]),
        PageBreak(),
        Paragraph("4. Knowledge Base Classification", heading_style),
        Paragraph("The following tables show how active documents are distributed across the system's categories and research topics.", body_style),
        _build_table([["Category", "Documents"]] + [[text(name), str(count)] for name, count in category_totals] or [["Category", "Documents"]], widths=[300, 180]),
        Spacer(1, 12),
        _build_table([["Research topic", "Documents"]] + [[text(name), str(count)] for name, count in topic_totals] or [["Research topic", "Documents"]], widths=[300, 180]),
        Spacer(1, 12),
        Paragraph("5. AI and Research Usage", heading_style),
        Paragraph(text(f"The system has recorded {total_questions} AI-assisted questions and {total_saved} saved research items. These figures represent persisted records in the database and provide an overview of research engagement."), body_style),
        metric_table([["AI questions recorded", total_questions], ["Saved research records", total_saved], ["Audit action types in period", len(activity_totals)], ["Users represented in audit period", len(activity_users)]]),
        Paragraph("6. Audit and Activity Analytics", heading_style),
        Paragraph(text(f"The selected period contains {len(rows)} activities. {reviewed_count} are reviewed and {len(rows) - reviewed_count} remain new. The notification count is based only on unreviewed database records."), body_style),
        _build_table([["Activity metric", "Value"]] + [["Activities in period", len(rows)], ["Reviewed activities", reviewed_count], ["New / unreviewed in period", len(rows) - reviewed_count], ["Unique activity types", len(activity_totals)], ["Days with activity", len(daily_totals)]], widths=[300, 180]),
        Spacer(1, 10),
        _build_table([["Activity type", "Count"]] + [[text(key), str(value)] for key, value in sorted(activity_totals.items(), key=lambda item: (-item[1], item[0]))[:20]], widths=[300, 180]),
        Spacer(1, 10),
        _build_table([["Role", "Count"]] + [[text(key), str(value)] for key, value in sorted(activity_roles.items(), key=lambda item: (-item[1], item[0]))], widths=[300, 180]),
        PageBreak(),
        Paragraph("7. Daily Activity Summary", heading_style),
        _build_table([["Date", "Activities"]] + [[text(day), str(count)] for day, count in sorted(daily_totals.items(), reverse=True)], widths=[300, 180]),
        Spacer(1, 14),
        Paragraph("8. Detailed Audit Record", heading_style),
        Paragraph("This appendix contains the actual audit records returned for the selected period. Review status changes do not delete or replace these records.", body_style),
    ]
    detail_rows = [["Date", "Time", "User", "Role", "Activity", "Resource", "Details", "Status"]]
    for record in rows:
        detail_rows.append([text(record.date or to_east_africa_time(record.timestamp).strftime("%Y-%m-%d")), text(record.time or to_east_africa_time(record.timestamp).strftime("%H:%M:%S")), text(record.username or "System"), text(record.user_role or "system"), text(record.action), text(record.resource or "-"), Paragraph(text(record.details or "-"), small_style), text("Reviewed" if record.reviewed else "New")])
    story.append(_build_table(detail_rows, widths=[48, 45, 62, 42, 62, 70, 108, 42]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Report conclusion", heading_style))
    story.append(Paragraph(text("This report is generated from live database records. Historical audit activities remain available for future review, and reviewing an activity changes only its review status."), body_style))
    document.build(story, onFirstPage=_page_header_footer, onLaterPages=_page_header_footer)
    pdf_data = buffer.getvalue()
    buffer.close()
    return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=system_statistics_report.pdf"})


@router.get("/activity/export-report")
async def export_activity_report(
    date: str | None = Query(default=None, alias="date"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if date:
        query = query.filter(AuditLog.date == date)
    elif start_date or end_date:
        if start_date:
            query = query.filter(AuditLog.date >= start_date)
        if end_date:
            query = query.filter(AuditLog.date <= end_date)
    rows = query.all()

    report_period = date or (f"{start_date or 'Beginning'} to {end_date or 'Present'}" if start_date or end_date else "All available audit history")
    log_activity(
        db,
        current_user,
        "Exported System Report",
        resource="system_statistics_report.pdf",
        details=f"Reporting period: {report_period}",
    )
    return _build_system_report(db, rows, date, start_date, end_date)


def _build_table(rows, widths=None):
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d8b15c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('FONTSIZE', (0, 0), (-1, -1), 7.2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return table


def _page_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setTitle('AI Research Knowledge Hub - Admin Activity & Audit Report')
    canvas.setFont('Helvetica', 8)
    canvas.drawString(36, 806, 'AI Research Knowledge Hub')
    canvas.drawRightString(556, 806, f'Page {doc.page}')
    canvas.drawString(36, 28, 'Confidential institutional report')
    canvas.restoreState()


@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
                "last_login": user.last_login,
            }
            for user in users
        ]
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable your own access.")
    user.is_active = payload.is_active
    db.commit()
    log_activity(db, current_user, "Updated User Status", resource=user.username, details=f"Set active={payload.is_active}")
    return {"message": "User status updated", "user_id": user.id, "is_active": user.is_active}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role.")
    user.role = payload.role
    db.commit()
    log_activity(db, current_user, "Updated User Role", resource=user.username, details=f"Set role={user.role.value}")
    return {"message": "User role updated", "user_id": user.id, "role": user.role.value}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")
    deleted_username = user.username
    db.delete(user)
    db.commit()
    log_activity(db, current_user, "Deleted User", resource=deleted_username, details=f"Deleted user {user_id}")
    return {"message": "User deleted successfully", "user_id": user.id}
