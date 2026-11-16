import pytest

from app import create_app
from app.fraud import is_flagged, score_transaction
from app.models import User, db


@pytest.fixture()
def client():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                      "SQLALCHEMY_ENGINE_OPTIONS": {}, "LOG_DIR": "/tmp/audit-test"})
    with app.app_context():
        db.create_all()
        admin = User(username="admin", is_admin=True)
        admin.set_password("pw12345")
        user = User(username="bob", is_admin=False)
        user.set_password("bobpw")
        db.session.add_all([admin, user])
        db.session.commit()
    return app.test_client()


def login(client, username, password):
    client.get("/login")
    with client.session_transaction() as s:
        token = s["_csrf"]
    return client.post("/login", data={"username": username, "password": password, "_csrf": token})


def test_fraud_rules():
    assert score_transaction(20000, "IN", 12, 0)[0] == 50
    score, reasons = score_transaction(6000, "IR", 2, 4)
    assert is_flagged(score) and "high-risk country" in reasons
    assert not is_flagged(score_transaction(50, "IN", 12, 0)[0])


def test_health(client):
    assert client.get("/health").json == {"status": "ok"}


def test_requires_login(client):
    assert client.get("/").status_code == 302


def test_csrf_enforced(client):
    assert client.post("/login", data={"username": "admin", "password": "pw12345"}).status_code == 400


def test_admin_only(client):
    login(client, "bob", "bobpw")
    assert client.get("/admin").status_code == 403
    client.get("/logout")


def test_admin_dashboard(client):
    login(client, "admin", "pw12345")
    assert client.get("/admin").status_code == 200


def test_lockout(client):
    for _ in range(5):
        login(client, "bob", "wrong")
    assert login(client, "bob", "bobpw").status_code == 429


def test_stress_endpoint_disabled_by_default(client):
    assert client.get("/stress").status_code == 404
