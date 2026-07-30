def test_health_check(client):

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_database_connection(db):

    from sqlalchemy import text
    result = db.execute(text("SELECT 1")).scalar()
    assert result == 1
