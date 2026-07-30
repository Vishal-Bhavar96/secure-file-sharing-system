from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogOut
from app.security.jwt import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit & Monitoring"])

@router.get("/logs", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if current_user.role != UserRole.ADMIN:
        # Regular users only see their own audit logs
        query = query.filter(AuditLog.user_id == current_user.id)
        
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs
