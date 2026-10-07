"""Dashboard data assembled from the existing database models."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from collections import Counter

from app.db.database import get_db
from app.models.document import Category, Document, DocumentType, ResearchTopic, document_topic
from app.models.ai_question import AIQuestion
from app.core.security import get_current_active_user
from app.core.audit import to_east_africa_time
from app.models.user import User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return only dashboard values that are backed by persisted data."""
    active_documents = Document.is_active.is_(True)
    total_documents = db.query(func.count(Document.id)).filter(active_documents).scalar() or 0
    processed_documents = (
        db.query(func.count(Document.id))
        .filter(active_documents, Document.is_processed.is_(True))
        .scalar()
        or 0
    )
    ai_question_count = db.query(func.count(AIQuestion.id)).filter(AIQuestion.user_id == current_user.id).scalar() or 0
    topic_count = (
        db.query(func.count(func.distinct(ResearchTopic.id)))
        .join(document_topic, document_topic.c.topic_id == ResearchTopic.id)
        .join(Document, Document.id == document_topic.c.document_id)
        .filter(active_documents)
        .scalar()
        or 0
    )

    document_types = (
        db.query(Document.document_type_id, func.count(Document.id))
        .filter(active_documents)
        .group_by(Document.document_type_id)
        .all()
    )
    type_names = {document_type.id: document_type.name for document_type in db.query(DocumentType).all()}

    topics = (
        db.query(ResearchTopic.name, func.count(Document.id))
        .join(document_topic, document_topic.c.topic_id == ResearchTopic.id)
        .join(Document, Document.id == document_topic.c.document_id)
        .filter(active_documents)
        .group_by(ResearchTopic.id, ResearchTopic.name)
        .order_by(func.count(Document.id).desc(), ResearchTopic.name.asc())
        .all()
    )
    categories = (
        db.query(Category.name, func.count(Document.id))
        .join(Document, Document.category_id == Category.id)
        .filter(active_documents, Category.is_active.is_(True))
        .group_by(Category.id, Category.name)
        .order_by(func.count(Document.id).desc(), Category.name.asc())
        .all()
    )

    recent_documents = (
        db.query(Document)
        .filter(active_documents)
        .order_by(Document.created_at.desc())
        .limit(5)
        .all()
    )

    question_timestamps = (
        db.query(AIQuestion.created_at)
        .filter(AIQuestion.user_id == current_user.id)
        .all()
    )
    question_counts = Counter(
        to_east_africa_time(created_at).date().isoformat()
        for (created_at,) in question_timestamps
        if created_at
    )
    today = to_east_africa_time(datetime.now(timezone.utc)).date()
    recent_question_history = [
        {"date": today - timedelta(days=offset), "count": question_counts.get(str(today - timedelta(days=offset)), 0)}
        for offset in range(13, -1, -1)
    ]

    return {
        "stats": {
            "total_documents": total_documents,
            "research_topics": topic_count,
            "ai_questions": ai_question_count,
            "processed_documents": processed_documents,
        },
        "document_types": [
            {"label": type_names.get(type_id, "Uncategorized"), "count": count}
            for type_id, count in document_types
        ],
        "topics": [{"label": name, "count": count} for name, count in topics],
        "categories": [{"label": name, "count": count} for name, count in categories],
        "departments": [{"label": name, "count": count} for name, count in categories],
        "questions_per_day": [
            {"date": str(point["date"]), "count": point["count"]}
            for point in recent_question_history
        ],
        "recent_activity": [
            {
                "text": f'Document "{document.title or document.file_name}" {document.processing_status or "created"}',
                "time": document.created_at,
            }
            for document in recent_documents
        ],
    }