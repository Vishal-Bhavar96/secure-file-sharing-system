import pytest
from app.models.user import PasswordResetOTP

def test_forgot_password_otp_flow(client, db):
    # 1. Register a test user
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "OTP User",
        "email": "otpuser@example.com",
        "username": "otpuser",
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert reg_res.status_code == 201

    # 2. Request OTP for email
    forgot_res = client.post("/api/v1/auth/forgot-password", json={
        "email_or_username": "otpuser@example.com"
    })
    assert forgot_res.status_code == 200
    forgot_data = forgot_res.json()
    assert "otp_code" not in forgot_data  # Hidden from API payload for security

    # Query generated OTP from database session
    otp_record = db.query(PasswordResetOTP).filter(PasswordResetOTP.email == "otpuser@example.com").order_by(PasswordResetOTP.id.desc()).first()
    assert otp_record is not None
    otp_code = otp_record.otp_code

    # 3. Invalid OTP attempt
    reset_invalid = client.post("/api/v1/auth/reset-password", json={
        "email_or_username": "otpuser@example.com",
        "otp_code": "000000",
        "new_password": "NewPassword123!",
        "confirm_new_password": "NewPassword123!"
    })
    assert reset_invalid.status_code == 400

    # 4. Valid OTP reset
    reset_res = client.post("/api/v1/auth/reset-password", json={
        "email_or_username": "otpuser@example.com",
        "otp_code": otp_code,
        "new_password": "NewPassword123!",
        "confirm_new_password": "NewPassword123!"
    })
    assert reset_res.status_code == 200

    # 5. Login with old password fails
    login_old = client.post("/api/v1/auth/login", json={
        "email": "otpuser@example.com",
        "password": "Password123!"
    })
    assert login_old.status_code == 401

    # 6. Login with new password succeeds
    login_new = client.post("/api/v1/auth/login", json={
        "email": "otpuser@example.com",
        "password": "NewPassword123!"
    })
    assert login_new.status_code == 200
    assert "access_token" in login_new.json()
