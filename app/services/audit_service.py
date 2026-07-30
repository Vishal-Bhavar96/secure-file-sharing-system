from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog, AuditAction

def log_activity(
    db: Session,
    action: AuditAction,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    resource: Optional[str] = None,
    details: Optional[str] = None,
    success: bool = True,
    ip_address: Optional[str] = None
) -> AuditLog:
    try:
        log_entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource=resource,
            details=details,
            success=success,
            ip_address=ip_address
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        db.rollback()
        # Fallback print if DB commit fails
        print(f"Failed to save audit log: {e}")
        return None
