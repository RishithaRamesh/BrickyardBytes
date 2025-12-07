import os

import pytest

from conftest import register_and_login, auth_headers


@pytest.fixture(autouse=True)
def clear_ai_key(monkeypatch):
    # Ensure tests hit the deterministic fallback instead of an external provider.
    monkeypatch.setenv("AI_RUN_DESC_KEY", "")
    return


def test_run_description_fallback_returns_copy(app_client):
    token, _ = register_and_login(app_client, "ai-desc@ncsu.edu")
    resp = app_client.post(
        "/ai/run-description",
        json={
            "restaurant": "Port City Java",
            "drop_point": "EBII Lobby",
            "eta": "3 PM",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["suggestion"].startswith("Heading to Port City Java")


def test_run_load_default_for_empty_run(app_client):
    token, _ = register_and_login(app_client, "ai-load-empty@ncsu.edu")
    resp = app_client.post(
        "/ai/run-load",
        json={
            "restaurant": "Port City Java",
            "drop_point": "EBII Lobby",
            "eta": "3 PM",
            "capacity": 3,
            "seats_remaining": 3,
            "orders": [],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert (
        resp.json()["assessment"] == "No orders yet; the run is currently light."
    )


def test_run_load_flags_complex_orders(app_client):
    token, _ = register_and_login(app_client, "ai-load-heavy@ncsu.edu")
    resp = app_client.post(
        "/ai/run-load",
        json={
            "restaurant": "Talley",
            "drop_point": "Library",
            "eta": "4 PM",
            "capacity": 4,
            "seats_remaining": 1,
            "orders": [
                {"items": "Party platter with sides", "amount": 32.0},
                {"items": "Combo meal", "amount": 18.0},
            ],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert (
        resp.json()["assessment"]
        == "Almost full, but several items look prep-heavy—plan extra pickup time."
    )
