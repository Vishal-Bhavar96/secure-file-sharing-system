from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.models.audit_log import AuditAction
from app.schemas.user import UserRegister, UserLogin
from app.security.password import verify_password, get_password_hash, validate_password_strength
from app.security.jwt import create_access_token
from app.services.audit_service import log_activity
from app.utils.validators import validate_email_format

def register_user(db: Session, user_in: UserRegister, ip_address: str = None) -> User:

    # 1. Email format check
    if not validate_email_format(user_in.email):
        log_activity(db, AuditAction.USER_REGISTERED, user_email=user_in.email, details="Invalid email format", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # 2. Check Password mismatch if provided
    if user_in.confirm_password is not None and user_in.password != user_in.confirm_password:
        log_activity(db, AuditAction.USER_REGISTERED, user_email=user_in.email, details="Password mismatch", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirm_password do not match"
        )

    # 3. Check Password Strength
    is_strong, pwd_err = validate_password_strength(user_in.password)
    if not is_strong:
        log_activity(db, AuditAction.USER_REGISTERED, user_email=user_in.email, details=f"Weak password: {pwd_err}", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weak password: {pwd_err}"
        )

    # 4. Handle Username
    username = user_in.username
    if not username:
        username = user_in.email.split("@")[0]

    # 5. Duplicate Email Check / Account Claiming
    existing_email = db.query(User).filter(User.email.ilike(user_in.email)).first()
    if existing_email:
        if existing_email.hashed_password:
            log_activity(db, AuditAction.USER_REGISTERED, user_email=user_in.email, details="Duplicate email", success=False, ip_address=ip_address)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered or already exists"
            )
        # Update details and password for auto-provisioned share recipient accounts (without password)
        existing_email.name = user_in.name
        existing_email.hashed_password = get_password_hash(user_in.password)
        if user_in.username and not db.query(User).filter(User.username == user_in.username, User.id != existing_email.id).first():
            existing_email.username = user_in.username
        if user_in.role:
            existing_email.role = user_in.role
        db.commit()
        db.refresh(existing_email)
        log_activity(db, AuditAction.USER_REGISTERED, user_id=existing_email.id, user_email=existing_email.email, resource=f"User:{existing_email.id}", details=f"Account claimed and password set", success=True, ip_address=ip_address)
        return existing_email

    # 6. Duplicate Username Check
    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        log_activity(db, AuditAction.USER_REGISTERED, user_email=user_in.email, details="Duplicate username", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )

    # 7. Create User
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        username=username,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role or UserRole.USER,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_activity(db, AuditAction.USER_REGISTERED, user_id=new_user.id, user_email=new_user.email, resource=f"User:{new_user.id}", details=f"User registered with role {new_user.role}", success=True, ip_address=ip_address)
    return new_user

def authenticate_user(db: Session, login_in: UserLogin, ip_address: str = None) -> tuple[User, str]:

    if not login_in.email or not login_in.email.strip() or not login_in.password:
        log_activity(db, AuditAction.LOGIN_FAILED, user_email=login_in.email, details="Empty credentials provided", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password cannot be empty"
        )

    user = db.query(User).filter((User.email == login_in.email) | (User.username == login_in.email)).first()
    if not user:
        log_activity(db, AuditAction.LOGIN_FAILED, user_email=login_in.email, details="Unknown email or username", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        log_activity(db, AuditAction.LOGIN_FAILED, user_id=user.id, user_email=user.email, details="Account disabled", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    if not verify_password(login_in.password, user.hashed_password):
        log_activity(db, AuditAction.LOGIN_FAILED, user_id=user.id, user_email=user.email, details="Incorrect password", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role.value})

    # Update last login timestamp and record session
    from datetime import datetime
    from app.models.session import UserSession

    user.last_login_at = datetime.utcnow()
    
    session_record = UserSession(
        user_id=user.id,
        session_token=token,
        user_agent="SecureShare Web Application Client",
        ip_address=ip_address or "127.0.0.1",
        is_active=True
    )
    db.add(session_record)
    db.commit()
    db.refresh(user)

    log_activity(db, AuditAction.LOGIN_SUCCESS, user_id=user.id, user_email=user.email, resource=f"User:{user.id}", details="User logged in successfully", success=True, ip_address=ip_address)
    
    return user, token
