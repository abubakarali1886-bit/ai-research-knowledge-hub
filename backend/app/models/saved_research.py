"""User-to-document saved research relationships."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from app.db.database import Base


class SavedResearch(Base):
    __tablename__ = "saved_research"
    __table_args__ = (UniqueConstraint("user_id", "document_id", name="uq_saved_research_user_document"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
