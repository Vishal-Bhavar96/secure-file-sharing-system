from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.user import UserRegister, UserLogin, Token, UserOut
from app.services.auth_service import register_user, authenticate_user
from app.security.jwt import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserOut, status_code=201)
def register(user_in: UserRegister, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    return register_user(db, user_in, ip_address=ip)

@router.post("/login", response_model=Token)
def login(login_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    user, token = authenticate_user(db, login_in, ip_address=ip)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserOut.model_validate(user)
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
