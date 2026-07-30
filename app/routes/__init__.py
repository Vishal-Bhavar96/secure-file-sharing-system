from app.routes.health import router as health_router
from app.routes.auth import router as auth_router
from app.routes.files import router as files_router
from app.routes.shares import router as shares_router
from app.routes.audit import router as audit_router
from app.routes.admin import router as admin_router

__all__ = [
    "health_router", "auth_router", "files_router", 
    "shares_router", "audit_router", "admin_router"
]
