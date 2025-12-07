import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import importlib
from typing import Dict
import pytest
from fastapi.testclient import TestClient


def _reload_app(tmp_path) -> TestClient:
    # Point the app to a temp sqlite file for isolation
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"

    # reload modules so engine/app are created with the test DB
    import app.db as dbmod

    importlib.reload(dbmod)
    import app.main as mainmod

    importlib.reload(mainmod)

    # Ensure tables/columns exist in the new test database (mirrors app startup behavior)
    try:
        dbmod.create_db_and_tables()
        dbmod.ensure_user_points_column()
        dbmod.ensure_foodrun_capacity_column()
        dbmod.ensure_order_pin_column()
        dbmod.ensure_order_tip_column()
        dbmod.ensure_foodrun_status_lowercase()
    except Exception:
        # Best-effort in tests; if something goes wrong, let the test run and fail
        pass

    client = TestClient(mainmod.app)
    return client


def register(client: TestClient, email: str, password: str):
    r = client.post("/auth/register", json={"email": email, "password": password})
    return r


def login(client: TestClient, email: str, password: str):
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r


def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(tmp_path):
    client = _reload_app(tmp_path)
    yield client


def test_01_register_success(client):
    r = register(client, "alice@ncsu.edu", "Secret123")
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert body["user"]["username"] == "alice@ncsu.edu"
    assert isinstance(body["user"]["points"], int)


def test_02_register_duplicate(client):
    register(client, "bob@ncsu.edu", "pw")
    r = register(client, "bob@ncsu.edu", "pw2")
    assert r.status_code == 409


def test_03_register_invalid_email(client):
    r = register(client, "not-an-email", "pw")
    assert r.status_code == 422


def test_04_login_success(client):
    register(client, "carol@ncsu.edu", "pass123")
    r = login(client, "carol@ncsu.edu", "pass123")
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert isinstance(body["user"]["points"], int)


def test_05_login_wrong_password(client):
    register(client, "dave@ncsu.edu", "pw")
    r = login(client, "dave@ncsu.edu", "wrong")
    assert r.status_code == 401


def test_06_login_nonexistent(client):
    r = login(client, "ghost@ncsu.edu", "x")
    assert r.status_code == 401


def test_07_auth_me_valid_token(client):
    register(client, "erin@ncsu.edu", "pw")
    r = login(client, "erin@ncsu.edu", "pw")
    token = r.json()["token"]
    me = client.get("/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["username"] == "erin@ncsu.edu"


def test_08_auth_me_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer bad"})
    assert r.status_code in (401, 422)


def test_09_create_run_success(client):
    register(client, "runner1@ncsu.edu", "pw")
    token = login(client, "runner1@ncsu.edu", "pw").json()["token"]
    payload = {
        "restaurant": "Taco Place",
        "drop_point": "Bldg A",
        "eta": "12:00",
        "capacity": 4,
    }
    r = client.post("/runs", json=payload, headers=auth_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert body["restaurant"] == "Taco Place"
    assert isinstance(body["seats_remaining"], int)


def test_10_create_run_unauthenticated(client):
    payload = {"restaurant": "NoAuth", "drop_point": "X", "eta": "now"}
    r = client.post("/runs", json=payload)
    assert r.status_code == 401


def test_11_create_run_missing_fields(client):
    register(client, "runner2@ncsu.edu", "pw")
    token = login(client, "runner2@ncsu.edu", "pw").json()["token"]
    r = client.post("/runs", json={"restaurant": "R"}, headers=auth_headers(token))
    assert r.status_code == 422


def test_12_list_runs(client):
    # create a run first
    register(client, "r3@ncsu.edu", "pw")
    token = login(client, "r3@ncsu.edu", "pw").json()["token"]
    client.post(
        "/runs",
        json={"restaurant": "A", "drop_point": "B", "eta": "1pm", "capacity": 3},
        headers=auth_headers(token),
    )
    r = client.get("/runs", headers=auth_headers(token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_13_get_run_details_authorized(client):
    register(client, "r4@ncsu.edu", "pw")
    token = login(client, "r4@ncsu.edu", "pw").json()["token"]
    create = client.post(
        "/runs",
        json={"restaurant": "X", "drop_point": "Y", "eta": "t", "capacity": 2},
        headers=auth_headers(token),
    )
    run_id = create.json()["id"]
    r = client.get(f"/runs/id/{run_id}", headers=auth_headers(token))
    assert r.status_code == 200


def test_14_get_run_details_unauthorized(client):
    register(client, "owner@ncsu.edu", "pw")
    owner_token = login(client, "owner@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "Z", "drop_point": "D", "eta": "t", "capacity": 2},
        headers=auth_headers(owner_token),
    ).json()
    run_id = run["id"]
    register(client, "other@ncsu.edu", "pw")
    other_token = login(client, "other@ncsu.edu", "pw").json()["token"]
    r = client.get(f"/runs/id/{run_id}", headers=auth_headers(other_token))
    assert r.status_code == 403


def test_15_join_run_success(client):
    register(client, "owner2@ncsu.edu", "pw")
    owner_token = login(client, "owner2@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "J", "drop_point": "K", "eta": "t", "capacity": 3},
        headers=auth_headers(owner_token),
    ).json()
    run_id = run["id"]
    register(client, "joiner@ncsu.edu", "pw")
    join_token = login(client, "joiner@ncsu.edu", "pw").json()["token"]
    r = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 15.5},
        headers=auth_headers(join_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert "pin" in body and len(str(body["pin"])) >= 4


def test_16_join_run_full(client):
    register(client, "o3@ncsu.edu", "pw")
    owner_token = login(client, "o3@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "F", "drop_point": "G", "eta": "t", "capacity": 1},
        headers=auth_headers(owner_token),
    ).json()
    run_id = run["id"]
    # one joiner fills capacity
    register(client, "j1@ncsu.edu", "pw")
    t1 = login(client, "j1@ncsu.edu", "pw").json()["token"]
    client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 5.0},
        headers=auth_headers(t1),
    )
    # second join attempt
    register(client, "j2@ncsu.edu", "pw")
    t2 = login(client, "j2@ncsu.edu", "pw").json()["token"]
    r = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 7.0},
        headers=auth_headers(t2),
    )
    assert r.status_code == 400


def test_17_runner_cannot_join_own_run(client):
    register(client, "selfjoin@ncsu.edu", "pw")
    token = login(client, "selfjoin@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "S", "drop_point": "P", "eta": "t", "capacity": 2},
        headers=auth_headers(token),
    ).json()
    r = client.post(
        f"/runs/{run['id']}/orders",
        json={"items": "[]", "amount": 10},
        headers=auth_headers(token),
    )
    assert r.status_code == 400


def test_18_verify_pin_success(client):
    register(client, "owner4@ncsu.edu", "pw")
    owner_token = login(client, "owner4@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "V", "drop_point": "Q", "eta": "t", "capacity": 3},
        headers=auth_headers(owner_token),
    ).json()
    run_id = run["id"]
    register(client, "u5@ncsu.edu", "pw")
    t5 = login(client, "u5@ncsu.edu", "pw").json()["token"]
    order = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 8.0},
        headers=auth_headers(t5),
    ).json()
    order_id = order["id"]
    pin = order["pin"]
    r = client.post(
        f"/runs/{run_id}/orders/{order_id}/verify-pin",
        json={"pin": pin},
        headers=auth_headers(owner_token),
    )
    assert r.status_code == 200


def test_19_verify_pin_wrong(client):
    register(client, "owner5@ncsu.edu", "pw")
    owner_token = login(client, "owner5@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "W", "drop_point": "R", "eta": "t", "capacity": 3},
        headers=auth_headers(owner_token),
    ).json()
    run_id = run["id"]
    register(client, "u6@ncsu.edu", "pw")
    t6 = login(client, "u6@ncsu.edu", "pw").json()["token"]
    order = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 9.0},
        headers=auth_headers(t6),
    ).json()
    order_id = order["id"]
    r = client.post(
        f"/runs/{run_id}/orders/{order_id}/verify-pin",
        json={"pin": "0000"},
        headers=auth_headers(owner_token),
    )
    assert r.status_code == 400


def test_20_cancel_my_order(client):
    register(client, "r7@ncsu.edu", "pw")
    owner_tok = login(client, "r7@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "C", "drop_point": "D", "eta": "t", "capacity": 3},
        headers=auth_headers(owner_tok),
    ).json()
    run_id = run["id"]
    register(client, "canceler@ncsu.edu", "pw")
    t = login(client, "canceler@ncsu.edu", "pw").json()["token"]
    client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 6.0},
        headers=auth_headers(t),
    )
    r = client.delete(f"/runs/{run_id}/orders/me", headers=auth_headers(t))
    assert r.status_code == 200


def test_21_runner_remove_order(client):
    register(client, "r8@ncsu.edu", "pw")
    owner_tok = login(client, "r8@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "L", "drop_point": "M", "eta": "t", "capacity": 3},
        headers=auth_headers(owner_tok),
    ).json()
    run_id = run["id"]
    register(client, "o9@ncsu.edu", "pw")
    t9 = login(client, "o9@ncsu.edu", "pw").json()["token"]
    order = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 3.0},
        headers=auth_headers(t9),
    ).json()
    r = client.delete(
        f"/runs/{run_id}/orders/{order['id']}", headers=auth_headers(owner_tok)
    )
    assert r.status_code == 200


def test_22_complete_run_awards_integer_points(client):
    register(client, "r10@ncsu.edu", "pw")
    owner_tok = login(client, "r10@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "P", "drop_point": "Z", "eta": "t", "capacity": 5},
        headers=auth_headers(owner_tok),
    ).json()
    run_id = run["id"]
    # two orders totaling 42.75 => 4.275 -> rounded to integer (4)
    register(client, "u10@ncsu.edu", "pw")
    t10 = login(client, "u10@ncsu.edu", "pw").json()["token"]
    client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 20.25},
        headers=auth_headers(t10),
    )
    register(client, "u11@ncsu.edu", "pw")
    t11 = login(client, "u11@ncsu.edu", "pw").json()["token"]
    client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 22.5},
        headers=auth_headers(t11),
    )
    r = client.put(f"/runs/{run_id}/complete", headers=auth_headers(owner_tok))
    assert r.status_code == 200
    earned = r.json().get("points_earned")
    assert isinstance(earned, int)
    # user points reflect integer
    pts = client.get("/points", headers=auth_headers(owner_tok)).json()
    assert isinstance(pts["points"], int)


def test_23_complete_run_unauthorized(client):
    register(client, "r11@ncsu.edu", "pw")
    owner_tok = login(client, "r11@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "Q", "drop_point": "R", "eta": "t", "capacity": 2},
        headers=auth_headers(owner_tok),
    ).json()
    run_id = run["id"]
    register(client, "attacker@ncsu.edu", "pw")
    t = login(client, "attacker@ncsu.edu", "pw").json()["token"]
    r = client.put(f"/runs/{run_id}/complete", headers=auth_headers(t))
    assert r.status_code == 403


def test_24_list_available_runs_filters(client):
    register(client, "r12@ncsu.edu", "pw")
    owner_tok = login(client, "r12@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "Avail", "drop_point": "Here", "eta": "t", "capacity": 1},
        headers=auth_headers(owner_tok),
    ).json()
    run_id = run["id"]
    register(client, "j12@ncsu.edu", "pw")
    t = login(client, "j12@ncsu.edu", "pw").json()["token"]
    # join to make it full
    client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 4.0},
        headers=auth_headers(t),
    )
    # list available for a new user should not include the full run
    register(client, "observer@ncsu.edu", "pw")
    obs_t = login(client, "observer@ncsu.edu", "pw").json()["token"]
    r = client.get("/runs/available", headers=auth_headers(obs_t))
    assert r.status_code == 200
    runs = r.json()
    assert all(r["seats_remaining"] > 0 for r in runs)


def test_25_get_points_returns_ints(client):
    register(client, "p1@ncsu.edu", "pw")
    t = login(client, "p1@ncsu.edu", "pw").json()["token"]
    res = client.get("/points", headers=auth_headers(t))
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["points"], int)
    assert isinstance(body["points_value"], int)


def test_26_redeem_points_success(client):
    register(client, "redeemer@ncsu.edu", "pw")
    t = login(client, "redeemer@ncsu.edu", "pw").json()["token"]
    # artificially bump points via creating and completing a run
    # create run as user
    run = client.post(
        "/runs",
        json={"restaurant": "X", "drop_point": "Y", "eta": "t", "capacity": 1},
        headers=auth_headers(t),
    ).json()
    run_id = run["id"]
    # join as another user
    register(client, "payer@ncsu.edu", "pw")
    tp = login(client, "payer@ncsu.edu", "pw").json()["token"]
    client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 100.0},
        headers=auth_headers(tp),
    )
    # complete run (awards 10 points)
    r = client.put(f"/runs/{run_id}/complete", headers=auth_headers(t))
    assert r.status_code == 200
    # redeem
    r2 = client.post("/points/redeem", headers=auth_headers(t))
    assert r2.status_code == 200
    body = r2.json()
    assert body["points_redeemed"] % 10 == 0


def test_27_redeem_insufficient_points(client):
    register(client, "low@ncsu.edu", "pw")
    t = login(client, "low@ncsu.edu", "pw").json()["token"]
    r = client.post("/points/redeem", headers=auth_headers(t))
    assert r.status_code == 400


def test_28_joined_runs_pin_exposure(client):
    register(client, "owner6@ncsu.edu", "pw")
    owner_tok = login(client, "owner6@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "Pin", "drop_point": "PP", "eta": "t", "capacity": 3},
        headers=auth_headers(owner_tok),
    ).json()
    run_id = run["id"]
    register(client, "joinx@ncsu.edu", "pw")
    tx = login(client, "joinx@ncsu.edu", "pw").json()["token"]
    order = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 2.0},
        headers=auth_headers(tx),
    ).json()
    # joined runs for joiner should expose my_order.pin
    r = client.get("/runs/joined", headers=auth_headers(tx))
    assert r.status_code == 200
    joined = r.json()
    assert any(
        (entry.get("my_order") and entry["my_order"].get("pin") is not None)
        for entry in joined
    )


def test_29_runs_history_for_runner(client):
    register(client, "hist_owner@ncsu.edu", "pw")
    tok = login(client, "hist_owner@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "H", "drop_point": "I", "eta": "t", "capacity": 2},
        headers=auth_headers(tok),
    ).json()
    run_id = run["id"]
    register(client, "hjoin@ncsu.edu", "pw")
    th = login(client, "hjoin@ncsu.edu", "pw").json()["token"]
    client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 3.0},
        headers=auth_headers(th),
    )
    client.put(f"/runs/{run_id}/complete", headers=auth_headers(tok))
    r = client.get("/runs/mine/history", headers=auth_headers(tok))
    assert r.status_code == 200
    assert any(item["id"] == run_id for item in r.json())


def test_30_create_order_invalid_amount(client):
    register(client, "invalid_orderer@ncsu.edu", "pw")
    to = login(client, "invalid_orderer@ncsu.edu", "pw").json()["token"]
    # create a run by another user
    register(client, "ownerX@ncsu.edu", "pw")
    xo = login(client, "ownerX@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "Bad", "drop_point": "B", "eta": "t", "capacity": 2},
        headers=auth_headers(xo),
    ).json()
    run_id = run["id"]
    # invalid type
    r1 = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": "nope"},
        headers=auth_headers(to),
    )
    assert r1.status_code == 422
    # negative amount (should be rejected or handled)
    r2 = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": -5},
        headers=auth_headers(to),
    )
    assert r2.status_code in (400, 422)


def test_31_join_run_invalid_tip(client):
    register(client, "tipowner@ncsu.edu", "pw")
    owner_token = login(client, "tipowner@ncsu.edu", "pw").json()["token"]
    run = client.post(
        "/runs",
        json={"restaurant": "Tip", "drop_point": "Desk", "eta": "soon", "capacity": 2},
        headers=auth_headers(owner_token),
    ).json()
    run_id = run["id"]
    register(client, "tipjoiner@ncsu.edu", "pw")
    join_token = login(client, "tipjoiner@ncsu.edu", "pw").json()["token"]

    bad_type = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 5.0, "tip": "ten"},
        headers=auth_headers(join_token),
    )
    assert bad_type.status_code == 422

    negative = client.post(
        f"/runs/{run_id}/orders",
        json={"items": "[]", "amount": 5.0, "tip": -1},
        headers=auth_headers(join_token),
    )
    assert negative.status_code == 422
