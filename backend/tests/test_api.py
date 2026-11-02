"""Isolated integration tests for the logistics API."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Configure the database before importing the application. Tests must never use
# the developer's bea.db file or records created through the running website.
_db_fd, _db_path = tempfile.mkstemp(prefix="bea-tests-", suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path.replace(os.sep, '/')}"

from app.main import app, engine


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
    Path(_db_path).unlink(missing_ok=True)


def login(client: TestClient, email: str = "admin@bea.local", password: str = "Admin123!") -> str:
    response = client.post("/auth/token", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_shipment(client: TestClient, token: str, suffix: str) -> dict:
    response = client.post(
        "/shipments",
        headers=auth(token),
        json={
            "customer_name": f"Test Customer {suffix}",
            "origin": "Bengaluru",
            "destination": "Mysuru",
            "description": "Automated test shipment",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_vehicle(client: TestClient, token: str, suffix: str) -> dict:
    response = client.post(
        "/vehicles",
        headers=auth(token),
        json={"plate_number": f"TEST-{suffix}", "model": "Test van", "capacity_kg": 900},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_driver(client: TestClient, token: str, suffix: str) -> dict:
    response = client.post(
        "/drivers",
        headers=auth(token),
        json={"name": f"Test Driver {suffix}", "license_number": f"LIC-{suffix}", "phone": "9000000000"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_trip(client: TestClient, token: str, shipment_id: int) -> dict:
    response = client.post("/trips", headers=auth(token), json={"shipment_id": shipment_id})
    assert response.status_code == 201, response.text
    return response.json()


def test_demo_login_returns_admin_token(client: TestClient) -> None:
    response = client.post("/auth/token", data={"username": "admin@bea.local", "password": "Admin123!"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["role"] == "admin"


def test_shipment_creation_generates_tracking_number(client: TestClient) -> None:
    shipment = create_shipment(client, login(client), "shipment")
    assert shipment["tracking_number"].startswith("BEA-")
    assert shipment["status"] == "pending"


def test_vehicle_capacity_must_be_positive(client: TestClient) -> None:
    response = client.post(
        "/vehicles",
        headers=auth(login(client)),
        json={"plate_number": "TEST-ZERO", "model": "Test van", "capacity_kg": 0},
    )
    assert response.status_code == 422


def test_trip_for_unknown_shipment_returns_not_found(client: TestClient) -> None:
    response = client.post("/trips", headers=auth(login(client)), json={"shipment_id": 999999})
    assert response.status_code == 404


def test_unavailable_resources_cannot_be_assigned_twice(client: TestClient) -> None:
    token = login(client)
    first_shipment = create_shipment(client, token, "assign-a")
    second_shipment = create_shipment(client, token, "assign-b")
    first_trip = create_trip(client, token, first_shipment["id"])
    second_trip = create_trip(client, token, second_shipment["id"])
    vehicle = create_vehicle(client, token, "ASSIGN")
    driver = create_driver(client, token, "ASSIGN")

    assigned = client.post(
        f"/trips/{first_trip['id']}/assign",
        headers=auth(token),
        json={"vehicle_id": vehicle["id"], "driver_id": driver["id"]},
    )
    assert assigned.status_code == 200

    conflict = client.post(
        f"/trips/{second_trip['id']}/assign",
        headers=auth(token),
        json={"vehicle_id": vehicle["id"], "driver_id": driver["id"]},
    )
    assert conflict.status_code == 409


def test_delivery_updates_shipment_and_releases_resources(client: TestClient) -> None:
    token = login(client)
    shipment = create_shipment(client, token, "delivery")
    vehicle = create_vehicle(client, token, "DELIVERY")
    driver = create_driver(client, token, "DELIVERY")
    trip = create_trip(client, token, shipment["id"])
    assignment = client.post(
        f"/trips/{trip['id']}/assign",
        headers=auth(token),
        json={"vehicle_id": vehicle["id"], "driver_id": driver["id"]},
    )
    assert assignment.status_code == 200
    started = client.patch(f"/trips/{trip['id']}/status", headers=auth(token), json={"status": "in_transit"})
    assert started.status_code == 200
    delivered = client.patch(f"/trips/{trip['id']}/status", headers=auth(token), json={"status": "delivered"})
    assert delivered.status_code == 200

    shipments = client.get("/shipments", headers=auth(token)).json()
    vehicles = client.get("/vehicles", headers=auth(token)).json()
    drivers = client.get("/drivers", headers=auth(token)).json()
    assert next(row for row in shipments if row["id"] == shipment["id"])["status"] == "delivered"
    assert next(row for row in vehicles if row["id"] == vehicle["id"])["status"] == "available"
    assert next(row for row in drivers if row["id"] == driver["id"])["status"] == "available"


def test_completing_maintenance_restores_vehicle_availability(client: TestClient) -> None:
    token = login(client)
    vehicle = create_vehicle(client, token, "SERVICE")
    response = client.post(
        "/maintenance",
        headers=auth(token),
        json={"vehicle_id": vehicle["id"], "description": "Routine inspection", "cost": 250, "status": "in_progress"},
    )
    assert response.status_code == 201
    maintenance_id = response.json()["id"]

    completed = client.patch(f"/maintenance/{maintenance_id}/complete", headers=auth(token))
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    vehicles = client.get("/vehicles", headers=auth(token)).json()
    assert next(row for row in vehicles if row["id"] == vehicle["id"])["status"] == "available"


def test_role_without_fleet_permission_is_forbidden(client: TestClient) -> None:
    admin_token = login(client)
    response = client.post(
        "/users",
        headers=auth(admin_token),
        json={"email": "test-manager@example.com", "name": "Test Manager", "role": "logistics_manager", "password": "TestManager123!"},
    )
    assert response.status_code == 201
    manager_token = login(client, "test-manager@example.com", "TestManager123!")
    forbidden = client.post(
        "/vehicles",
        headers=auth(manager_token),
        json={"plate_number": "TEST-FORBIDDEN", "model": "Test van", "capacity_kg": 900},
    )
    assert forbidden.status_code == 403
