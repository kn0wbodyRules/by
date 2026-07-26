"""Integration-level negative-test sweep: out-of-order calls across the real HTTP
API must return clean 4xx errors, never a raw 500. Runs against the isolated test
database (get_db is overridden), never the dev DB.
"""

import io

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from tests.conftest import _TestSessionLocal


def _override_get_db():
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client, monkeypatch):
    captured = {}

    def _fake_send(to_email, otp_code):
        captured["otp_code"] = otp_code

    monkeypatch.setattr("app.services.auth_service.send_otp_email", _fake_send)

    client.post("/auth/register", json={"email": "sweep@example.com", "password": "password123"})
    resp = client.post(
        "/auth/verify-otp", json={"email": "sweep@example.com", "otp_code": captured["otp_code"]}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_uploaded_job(client, auth_headers) -> str:
    files = {"file": ("plan.jpg", io.BytesIO(b"fake image bytes"), "image/jpeg")}
    resp = client.post(
        "/upload", headers=auth_headers, files=files, data={"project_name": "Sweep Test"}
    )
    return resp.json()["job_id"]


def test_calculate_before_rooms_confirmed_rejected(client, auth_headers):
    job_id = _create_uploaded_job(client, auth_headers)
    resp = client.post(f"/calculate/{job_id}", headers=auth_headers)
    assert resp.status_code == 409


def test_constraints_before_rooms_confirmed_rejected(client, auth_headers):
    job_id = _create_uploaded_job(client, auth_headers)
    resp = client.patch(f"/constraints/{job_id}", headers=auth_headers, json={})
    assert resp.status_code == 409


def test_boq_before_calculated_rejected(client, auth_headers):
    job_id = _create_uploaded_job(client, auth_headers)
    resp = client.get(f"/boq/{job_id}", headers=auth_headers)
    assert resp.status_code == 409


def test_export_before_calculated_rejected(client, auth_headers):
    job_id = _create_uploaded_job(client, auth_headers)
    resp = client.get(f"/export/{job_id}?format=pdf", headers=auth_headers)
    assert resp.status_code == 409


def test_confirm_rooms_before_any_rooms_exist_rejected(client, auth_headers):
    job_id = _create_uploaded_job(client, auth_headers)
    resp = client.patch(f"/confirm-rooms/{job_id}", headers=auth_headers, json={"rooms": []})
    assert resp.status_code == 409


def test_manual_rooms_twice_second_call_rejected(client, auth_headers):
    job_id = _create_uploaded_job(client, auth_headers)
    body = {
        "rooms": [
            {
                "room_name": "Bedroom",
                "length_ft": 10,
                "width_ft": 10,
                "ceiling_height_ft": 9,
                "wall_thickness_ft": 0.75,
            }
        ]
    }
    first = client.post(f"/manual-rooms/{job_id}", headers=auth_headers, json=body)
    assert first.status_code == 200

    second = client.post(f"/manual-rooms/{job_id}", headers=auth_headers, json=body)
    assert second.status_code == 409


def test_full_happy_path_reaches_calculated(client, auth_headers):
    job_id = _create_uploaded_job(client, auth_headers)
    body = {
        "rooms": [
            {
                "room_name": "Bedroom",
                "length_ft": 10,
                "width_ft": 10,
                "ceiling_height_ft": 9,
                "wall_thickness_ft": 0.75,
            }
        ]
    }
    rooms_resp = client.post(f"/manual-rooms/{job_id}", headers=auth_headers, json=body)
    assert rooms_resp.status_code == 200

    confirm_resp = client.patch(f"/confirm-rooms/{job_id}", headers=auth_headers, json={"rooms": []})
    assert confirm_resp.status_code == 200

    constraints_resp = client.patch(f"/constraints/{job_id}", headers=auth_headers, json={})
    assert constraints_resp.status_code == 200

    calc_resp = client.post(f"/calculate/{job_id}", headers=auth_headers)
    assert calc_resp.status_code == 200
    assert calc_resp.json()["total_cost"] > 0

    boq_resp = client.get(f"/boq/{job_id}", headers=auth_headers)
    assert boq_resp.status_code == 200

    chat_resp = client.post(f"/chat/{job_id}", headers=auth_headers, json={"message": "hi"})
    assert chat_resp.status_code == 200


def test_job_belonging_to_another_user_returns_404_not_403(client, auth_headers, monkeypatch):
    """Ownership must fail closed as 404 (not leak existence via 403)."""
    job_id = _create_uploaded_job(client, auth_headers)

    captured = {}
    monkeypatch.setattr(
        "app.services.auth_service.send_otp_email", lambda email, code: captured.update(otp_code=code)
    )
    client.post("/auth/register", json={"email": "other@example.com", "password": "password123"})
    other_login = client.post(
        "/auth/verify-otp", json={"email": "other@example.com", "otp_code": captured["otp_code"]}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    resp = client.get(f"/boq/{job_id}", headers=other_headers)
    assert resp.status_code == 404


def test_missing_auth_header_rejected_on_protected_route(client):
    resp = client.get("/plans")
    assert resp.status_code == 401
