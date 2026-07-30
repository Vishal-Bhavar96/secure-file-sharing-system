import pytest
from app.models.audit_log import AuditAction

def test_audit_logs_recorded_on_actions(client, token_user_a, token_admin):
    # 1. Trigger Login failure
    client.post("/api/v1/auth/login", json={"email": "nonexistent@test.com", "password": "WrongPassword123!"})

    # 2. Trigger Unauthorized access
    client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token_user_a}"})

    # 3. Fetch audit logs as Admin
    res = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {token_admin}"})
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) > 0

    actions_recorded = [l["action"] for l in logs]
    assert AuditAction.LOGIN_FAILED in actions_recorded or AuditAction.UNAUTHORIZED_ACCESS in actions_recorded
