import io
import pytest
from datetime import datetime, timedelta
from app.models.audit_log import AuditLog, AuditAction
from app.models.share import FileShare

def test_valid_file_share_with_multi_factor(client, user_a, user_b, token_user_a, token_user_b, db):
    # 1. User A uploads file
    file_data = ("financial_report.pdf", io.BytesIO(b"Confidential Financials 2026"), "application/pdf")
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": file_data},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_up.status_code == 201
    file_id = res_up.json()["id"]

    # 2. User A creates multi-factor share for User B
    res_share = client.post(
        "/api/v1/shares",
        json={
            "file_id": file_id,
            "target_user_identifier": user_b.email,
            "permission": "DOWNLOAD",
            "expiry_hours": 24,
            "max_downloads": 3,
            "requires_otp": True,
            "requires_password": True,
            "password": "ShareSecretPassword123!"
        },
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_share.status_code == 201
    share_data = res_share.json()
    share_token = share_data["share_token"]
    share_id = share_data["id"]

    assert share_data["requires_otp"] is True
    assert share_data["has_password"] is True

    # 3. Recipient views token metadata (GET /api/v1/shares/token/{token})
    res_meta = client.get(f"/api/v1/shares/token/{share_token}")
    assert res_meta.status_code == 200
    meta = res_meta.json()
    assert meta["filename"] == "financial_report.pdf"
    assert meta["requires_otp"] is True
    assert meta["has_password"] is True

    # 4. Trigger OTP send
    res_otp = client.post(f"/api/v1/shares/token/{share_token}/otp")
    assert res_otp.status_code == 200
    assert res_otp.json()["otp_sent"] is True

    # Get generated OTP from database for testing verification
    share_obj = db.query(FileShare).filter(FileShare.id == share_id).first()
    assert share_obj.otp_code_hash is not None

    # 5. Verify incorrect OTP -> 400
    res_bad_otp = client.post(f"/api/v1/shares/token/{share_token}/verify-otp", json={"otp": "000000"})
    assert res_bad_otp.status_code == 400

    # 6. Verify correct OTP
    from app.security.password import get_password_hash
    test_otp = "123456"
    share_obj.otp_code_hash = get_password_hash(test_otp)
    share_obj.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    res_good_otp = client.post(f"/api/v1/shares/token/{share_token}/verify-otp", json={"otp": test_otp})
    assert res_good_otp.status_code == 200
    assert res_good_otp.json()["otp_verified"] is True

    # 7. Verify Share Password
    res_bad_pwd = client.post(f"/api/v1/shares/token/{share_token}/verify-password", json={"password": "WrongPassword"})
    assert res_bad_pwd.status_code == 401

    res_good_pwd = client.post(f"/api/v1/shares/token/{share_token}/verify-password", json={"password": "ShareSecretPassword123!"})
    assert res_good_pwd.status_code == 200
    assert res_good_pwd.json()["password_verified"] is True

    # 8. Download authorized file payload
    res_dl = client.get(f"/api/v1/shares/token/{share_token}/download?password=ShareSecretPassword123!&otp_verified=true")
    assert res_dl.status_code == 200
    assert res_dl.content == b"Confidential Financials 2026"

def test_invalid_email_and_unauthorized_share(client, user_a, user_b, token_user_a, token_user_b):
    # Upload file as User B
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("userb_doc.txt", io.BytesIO(b"userb data"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    file_id = res_up.json()["id"]

    # User A tries to share User B's file -> 403
    res_unauth = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": user_a.email},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_unauth.status_code == 403

    # User B tries to share with non-existent username -> 404
    res_invalid_email = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": "nonexistentuser_without_email_domain"},
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    assert res_invalid_email.status_code == 404

def test_invalid_expired_and_revoked_tokens(client, user_a, token_user_a, db):
    # 1. Invalid token -> 404
    res_invalid = client.get("/api/v1/shares/token/invalid_random_token_string_123")
    assert res_invalid.status_code == 404

    # 2. Upload file & Create share
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("to_expire.txt", io.BytesIO(b"expiring data"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    past_date = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    res_share = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "expiry_date": past_date},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    token = res_share.json()["share_token"]
    share_id = res_share.json()["id"]

    # Expired token download attempt -> 403
    res_exp_dl = client.get(f"/api/v1/shares/token/{token}/download?otp_verified=true")
    assert res_exp_dl.status_code == 403
    assert "expired" in res_exp_dl.json()["detail"].lower()

    # 3. Test Manual Revocation
    res_share2 = client.post(
        "/api/v1/shares",
        json={"file_id": file_id},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    token2 = res_share2.json()["share_token"]
    share_id2 = res_share2.json()["id"]

    res_revoke = client.delete(f"/api/v1/shares/{share_id2}/revoke", headers={"Authorization": f"Bearer {token_user_a}"})
    assert res_revoke.status_code == 200

    res_revoked_dl = client.get(f"/api/v1/shares/token/{token2}/download?otp_verified=true")
    assert res_revoked_dl.status_code == 403
    assert "revoked" in res_revoked_dl.json()["detail"].lower()

def test_otp_rate_limiting_and_max_attempts(client, user_a, token_user_a, db):
    # Upload & share
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("otp_test.txt", io.BytesIO(b"otp data"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    res_share = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": "test_otp_recip@secure.local", "requires_otp": True},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    token = res_share.json()["share_token"]
    share_id = res_share.json()["id"]

    # First OTP request -> 200
    res_otp1 = client.post(f"/api/v1/shares/token/{token}/otp")
    assert res_otp1.status_code == 200

    # Immediate second OTP request -> 429 Rate Limit Cooldown
    res_otp2 = client.post(f"/api/v1/shares/token/{token}/otp")
    assert res_otp2.status_code == 429
    assert "wait" in res_otp2.json()["detail"].lower()

    # Test Max OTP Attempts
    share_obj = db.query(FileShare).filter(FileShare.id == share_id).first()
    share_obj.otp_attempts = 5
    db.commit()

    res_max_otp = client.post(f"/api/v1/shares/token/{token}/verify-otp", json={"otp": "123456"})
    assert res_max_otp.status_code == 429
    assert "too many" in res_max_otp.json()["detail"].lower()

def test_view_permission_and_one_time_access(client, user_a, token_user_a, db):
    # Upload file
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("view_only_doc.pdf", io.BytesIO(b"view content only"), "application/pdf")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    # Create VIEW-only share
    res_share_view = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "permission": "VIEW", "requires_otp": False},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    token_view = res_share_view.json()["share_token"]

    # View online -> 200
    res_v = client.get(f"/api/v1/shares/token/{token_view}/view")
    assert res_v.status_code == 200
    assert res_v.content == b"view content only"

    # Attempt download on VIEW-only share -> 403
    res_dl_forbidden = client.get(f"/api/v1/shares/token/{token_view}/download")
    assert res_dl_forbidden.status_code == 403
    assert "view-only" in res_dl_forbidden.json()["detail"].lower()

    # Test One-Time Access
    res_share_onetime = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "permission": "DOWNLOAD", "requires_otp": False, "one_time_access": True},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    token_onetime = res_share_onetime.json()["share_token"]

    # 1st download -> 200
    res_dl1 = client.get(f"/api/v1/shares/token/{token_onetime}/download")
    assert res_dl1.status_code == 200

    # 2nd download -> 403 (Auto-revoked after 1st access)
    res_dl2 = client.get(f"/api/v1/shares/token/{token_onetime}/download")
    assert res_dl2.status_code == 403
    assert "revoked" in res_dl2.json()["detail"].lower()

def test_audit_logs_recorded(client, user_a, token_user_a, db):
    # Perform action to generate log
    client.post(
        "/api/v1/files/upload",
        files={"file": ("audit_sample.txt", io.BytesIO(b"sample data"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    res_logs = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {token_user_a}"})
    assert res_logs.status_code == 200
    logs = res_logs.json()
    assert len(logs) > 0
    actions = [l["action"] for l in logs]
    assert any(a in actions for a in ["FILE_SHARED", "FILE_UPLOADED", "ACCESS_GRANTED"])
