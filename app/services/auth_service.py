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

import random
from datetime import datetime, timedelta
from app.models.user import PasswordResetOTP
from app.schemas.user import ResetPasswordOTPVerify

def request_password_reset_otp(db: Session, email_or_username: str, ip_address: str = None) -> dict:
    identifier = email_or_username.strip()
    user = db.query(User).filter(
        (User.email.ilike(identifier)) | (User.username.ilike(identifier))
    ).first()

    if not user:
        return {
            "message": "If account exists, OTP has been sent to the registered email address.",
            "email_masked": "u***@example.com",
            "otp_code": None
        }

    # Invalidate previous unexpired OTPs
    db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user.id,
        PasswordResetOTP.is_used == False
    ).update({"is_used": True})

    # Generate 6-digit random code
    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    otp_record = PasswordResetOTP(
        user_id=user.id,
        email=user.email,
        otp_code=otp_code,
        expires_at=expires_at,
        is_used=False
    )
    db.add(otp_record)
    db.commit()

    log_activity(
        db,
        action=AuditAction.PASSWORD_CHANGED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details=f"Requested password reset OTP (Expires in 10 mins)",
        success=True,
        ip_address=ip_address
    )

    email_parts = user.email.split("@")
    name_part = email_parts[0]
    domain_part = email_parts[1]
    if len(name_part) <= 2:
        masked_name = name_part[0] + "*"
    else:
        masked_name = name_part[:2] + "*" * (len(name_part) - 2)
    email_masked = f"{masked_name}@{domain_part}"
    
    from app.services.email_service import send_otp_email
    email_sent = send_otp_email(user.email, otp_code)

    return {
        "message": f"OTP sent to official mail {email_masked}",
        "email": user.email,
        "email_masked": email_masked,
        "email_sent": email_sent
    }

def reset_password_with_otp(db: Session, reset_in: ResetPasswordOTPVerify, ip_address: str = None) -> dict:
    identifier = reset_in.email_or_username.strip()
    user = db.query(User).filter(
        (User.email.ilike(identifier)) | (User.username.ilike(identifier))
    ).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")

    if reset_in.new_password != reset_in.confirm_new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    is_strong, pwd_err = validate_password_strength(reset_in.new_password)
    if not is_strong:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Weak password: {pwd_err}")

    now = datetime.utcnow()
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.user_id == user.id,
        PasswordResetOTP.otp_code == reset_in.otp_code.strip(),
        PasswordResetOTP.is_used == False,
        PasswordResetOTP.expires_at > now
    ).order_by(PasswordResetOTP.created_at.desc()).first()

    if not otp_record:
        log_activity(
            db,
            action=AuditAction.PASSWORD_CHANGED,
            user_id=user.id,
            user_email=user.email,
            details="Invalid or expired OTP entered during password reset",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP code")

    user.hashed_password = get_password_hash(reset_in.new_password)
    user.last_password_change_at = datetime.utcnow()
    otp_record.is_used = True
    db.commit()

    log_activity(
        db,
        action=AuditAction.PASSWORD_CHANGED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details="Password successfully reset via OTP verification",
        success=True,
        ip_address=ip_address
    )

    return {"message": "Password reset successful! You can now log in with your new password."}

