import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.database.init_db import init_db
from app.routes.health import router as health_router
from app.routes.auth import router as auth_router
from app.routes.files import router as files_router
from app.routes.shares import router as shares_router
from app.routes.audit import router as audit_router
from app.routes.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Guarantee DB tables and seed accounts are initialized on server startup
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise-grade Secure File-Sharing System with AES-256 Encryption, RBAC & Activity Audit Logging",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(health_router)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(files_router, prefix=settings.API_V1_STR)
app.include_router(shares_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)

# Mount Static Web Application Frontend
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
