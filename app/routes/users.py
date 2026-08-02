import os
from typing import List
from fastapi import APIRouter, Depends, Request, UploadFile, File as FastAPIFile, status, Response
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserOut, UserProfileUpdate, UserEmailChange, UserPasswordChange,
    UserPreferencesUpdate, UserSessionOut
)
from app.security.jwt import get_current_user, oauth2_scheme
from app.services.user_service import (
    update_profile_name, upload_avatar, remove_avatar,
    change_email, change_password, update_preferences,
    get_active_sessions, revoke_other_sessions
)

router = APIRouter(prefix="/users", tags=["Users Profile & Settings"])

def build_user_out(user: User) -> UserOut:
    has_avatar = bool(user.avatar_path and os.path.exists(user.avatar_path))
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        has_avatar=has_avatar,
        theme_preference=user.theme_preference or "dark",
        default_file_sort=user.default_file_sort or "date_desc",
        items_per_page=user.items_per_page or 10,
        last_login_at=user.last_login_at,
        last_password_change_at=user.last_password_change_at
    )

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return build_user_out(current_user)

@router.put("/me/profile", response_model=UserOut)
def update_profile(
    profile_in: UserProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    user = update_profile_name(db, user=current_user, name=profile_in.name, ip_address=ip)
    return build_user_out(user)

@router.post("/me/avatar", response_model=UserOut)
def update_avatar(
    request: Request,
    file: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    user = upload_avatar(db, user=current_user, file=file, ip_address=ip)
    return build_user_out(user)

@router.delete("/me/avatar", response_model=UserOut)
def delete_avatar(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    user = remove_avatar(db, user=current_user, ip_address=ip)
    return build_user_out(user)

@router.get("/me/avatar")
def get_avatar(current_user: User = Depends(get_current_user)):
    if current_user.avatar_path and os.path.exists(current_user.avatar_path):
        return FileResponse(current_user.avatar_path)
    return Response(status_code=status.HTTP_404_NOT_FOUND, content="Avatar image not set")

@router.post("/me/email", response_model=UserOut)
def update_email(
    email_in: UserEmailChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    user = change_email(
        db, user=current_user, current_password=email_in.current_password,
        new_email=email_in.new_email, confirm_new_email=email_in.confirm_new_email, ip_address=ip
    )
    return build_user_out(user)

@router.post("/me/password", response_model=UserOut)
def update_password(
    password_in: UserPasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    user = change_password(
        db, user=current_user, current_password=password_in.current_password,
        new_password=password_in.new_password, confirm_new_password=password_in.confirm_new_password, ip_address=ip
    )
    return build_user_out(user)

@router.put("/me/preferences", response_model=UserOut)
def update_user_preferences(
    prefs_in: UserPreferencesUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    user = update_preferences(
        db, user=current_user, theme=prefs_in.theme_preference,
        sort=prefs_in.default_file_sort, items_per_page=prefs_in.items_per_page, ip_address=ip
    )
    return build_user_out(user)

@router.get("/me/sessions", response_model=List[UserSessionOut])
def get_user_sessions(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_active_sessions(db, user=current_user, current_token=token)

@router.post("/me/sessions/revoke-others", status_code=status.HTTP_200_OK)
def revoke_other_user_sessions(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    count = revoke_other_sessions(db, user=current_user, current_token=token, ip_address=ip)
    return {"message": f"Successfully revoked {count} other active session(s)", "count": count}
