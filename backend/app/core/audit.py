from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User

try:
    EAST_AFRICA_TIMEZONE: tzinfo = ZoneInfo("Africa/Dar_es_Salaam")
except ZoneInfoNotFoundError:
    # Tanzania uses UTC+3 year-round; this keeps Windows installs without tzdata working.
    EAST_AFRICA_TIMEZONE = timezone(timedelta(hours=3), name="Africa/Dar_es_Salaam")


def to_east_africa_time(value: datetime) -> datetime:
    """Interpret legacy naive timestamps as UTC and return Dar es Salaam time."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(EAST_AFRICA_TIMEZONE)


def log_activity(
    db: Session,
    user: Optional[User],
    action: str,
    resource: Optional[str] = None,
    details: Optional[str] = None,
) -> AuditLog:
    timestamp = datetime.now(timezone.utc)
    local_timestamp = timestamp.astimezone(EAST_AFRICA_TIMEZONE)
    user_role = user.role.value if user and getattr(user, "role", None) else None
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        user_role=user_role,
        action=action,
        resource=resource,
        date=local_timestamp.strftime("%Y-%m-%d"),
        time=local_timestamp.strftime("%H:%M:%S"),
        timestamp=timestamp,
        details=details,
        reviewed=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
