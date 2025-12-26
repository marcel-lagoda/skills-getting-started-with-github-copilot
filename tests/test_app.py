import copy
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the src directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from app import app, activities  # noqa: E402


def make_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def restore_activities_state():
    snapshot = copy.deepcopy(activities)
    try:
        yield
    finally:
        activities.clear()
        activities.update(copy.deepcopy(snapshot))


def test_get_activities_returns_initial_data():
    client = make_client()
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert "Basketball Club" in data
    assert data["Basketball Club"]["participants"] == ["alex@mergington.edu"]


def test_signup_adds_participant():
    client = make_client()
    email = "newstudent@mergington.edu"
    response = client.post(
        "/activities/Basketball%20Club/signup",
        params={"email": email},
    )
    assert response.status_code == 200
    assert "Signed up" in response.json()["message"]

    refreshed = client.get("/activities").json()
    assert email in refreshed["Basketball Club"]["participants"]


def test_signup_rejects_duplicates():
    client = make_client()
    response = client.post(
        "/activities/Basketball%20Club/signup",
        params={"email": "alex@mergington.edu"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Student is already signed up"


def test_signup_requires_existing_activity():
    client = make_client()
    response = client.post(
        "/activities/Unknown/signup",
        params={"email": "student@mergington.edu"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_enforces_capacity():
    activities["Tiny Club"] = {
        "description": "A very small club",
        "schedule": "Mondays",
        "max_participants": 1,
        "participants": [],
    }
    client = make_client()

    first = client.post(
        "/activities/Tiny%20Club/signup",
        params={"email": "first@mergington.edu"},
    )
    assert first.status_code == 200

    second = client.post(
        "/activities/Tiny%20Club/signup",
        params={"email": "second@mergington.edu"},
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "Activity is full"


def test_unregister_removes_participant():
    client = make_client()
    response = client.delete(
        "/activities/Basketball%20Club/unregister",
        params={"email": "alex@mergington.edu"},
    )
    assert response.status_code == 200
    refreshed = client.get("/activities").json()
    assert "alex@mergington.edu" not in refreshed["Basketball Club"]["participants"]


def test_unregister_requires_existing_participant():
    client = make_client()
    response = client.delete(
        "/activities/Basketball%20Club/unregister",
        params={"email": "ghost@mergington.edu"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not registered"
