from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    user_role = Column(String(30), nullable=True, index=True)
    action = Column(String(120), nullable=False, index=True)
    resource = Column(String(255), nullable=True, index=True)
    date = Column(String(20), nullable=False, index=True)
    time = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    details = Column(Text, nullable=True)
    reviewed = Column(Boolean, nullable=False, default=False, server_default="false", index=True)

    user = relationship("User", foreign_keys=[user_id])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.reviewed is None:
            self.reviewed = False

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', username='{self.username}')>"
