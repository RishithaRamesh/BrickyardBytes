import pytest

from conftest import register_and_login


def create_run(
    client,
    token,
    restaurant="Port City Java EBII",
    drop="Wolf Ridge",
    capacity=2,
    eta="10:30",
):
    payload = {
        "restaurant": restaurant,
        "drop_point": drop,
        "capacity": capacity,
        "eta": eta,
    }
    r = client.post("/runs", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert r.status_code in (200, 201), r.text
    return r.json()


def join_run(client, token, run_id, items="1x Coffee", amount=3.50, tip=0.0):
    return client.post(
        f"/runs/{run_id}/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": items, "amount": amount, "tip": tip},
    )


def test_runner_cannot_join_own_run(app_client):
    runner_token, _ = register_and_login(app_client, "runner@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=2)
    r = join_run(app_client, runner_token, run["id"])
    assert r.status_code in (400, 403)


def test_duplicate_join_denied(app_client):
    runner_token, _ = register_and_login(app_client, "dup_runner@ncsu.edu")
    joiner_token, _ = register_and_login(app_client, "dup_user@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=3)
    run_id = run["id"]

    r1 = join_run(app_client, joiner_token, run_id)
    assert r1.status_code in (200, 201)
    r2 = join_run(app_client, joiner_token, run_id)
    assert r2.status_code == 400


def test_join_reflected_in_joined_endpoint(app_client):
    runner_token, _ = register_and_login(app_client, "owner@ncsu.edu")
    u1_token, _ = register_and_login(app_client, "u1@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]
    j1 = join_run(app_client, u1_token, run_id)
    assert j1.status_code in (200, 201)
    rj = app_client.get("/runs/joined", headers={"Authorization": f"Bearer {u1_token}"})
    assert run_id in [r["id"] for r in rj.json()]


def test_capacity_prevents_join_when_full(app_client):
    runner_token, _ = register_and_login(app_client, "owner2@ncsu.edu")
    u1_token, _ = register_and_login(app_client, "u1b@ncsu.edu")
    u2_token, _ = register_and_login(app_client, "u2b@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]
    app_client.post(
        f"/runs/{run_id}/orders",
        headers={"Authorization": f"Bearer {u1_token}"},
        json={"items": "x", "amount": 1.0},
    )
    j2 = join_run(app_client, u2_token, run_id)
    assert j2.status_code in (400, 409)


def test_unjoin_allows_another_join(app_client):
    runner_token, _ = register_and_login(app_client, "owner3@ncsu.edu")
    u1_token, _ = register_and_login(app_client, "u1c@ncsu.edu")
    u2_token, _ = register_and_login(app_client, "u2c@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]
    app_client.post(
        f"/runs/{run_id}/orders",
        headers={"Authorization": f"Bearer {u1_token}"},
        json={"items": "x", "amount": 1.0},
    )
    uj = app_client.delete(
        f"/runs/{run_id}/orders/me", headers={"Authorization": f"Bearer {u1_token}"}
    )
    assert uj.status_code in (200, 204)
    j2b = join_run(app_client, u2_token, run_id)
    assert j2b.status_code in (200, 201)


def test_joined_my_pin_visible_only_to_me_user_a(app_client):
    runner_token, _ = register_and_login(app_client, "r@ncsu.edu")
    a_token, _ = register_and_login(app_client, "a@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=3)
    ja = join_run(app_client, a_token, run["id"], items="1x Latte", amount=4.0)
    assert ja.status_code in (200, 201)
    rja = app_client.get("/runs/joined", headers={"Authorization": f"Bearer {a_token}"})
    my_run_a = next(x for x in rja.json() if x["id"] == run["id"])
    assert my_run_a.get("my_order", {}).get("pin")


def test_joined_my_pin_visible_only_to_me_user_b(app_client):
    runner_token, _ = register_and_login(app_client, "rr@ncsu.edu")
    b_token, _ = register_and_login(app_client, "bb@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=3)
    jb = join_run(app_client, b_token, run["id"], items="1x Mocha", amount=4.5)
    assert jb.status_code in (200, 201)
    rjb = app_client.get("/runs/joined", headers={"Authorization": f"Bearer {b_token}"})
    my_run_b = next(x for x in rjb.json() if x["id"] == run["id"])
    assert my_run_b.get("my_order", {}).get("pin")


def test_runner_orders_do_not_include_pins(app_client):
    runner_token, _ = register_and_login(app_client, "r3@ncsu.edu")
    a_token, _ = register_and_login(app_client, "a3@ncsu.edu")
    b_token, _ = register_and_login(app_client, "b3@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=3)
    join_run(app_client, a_token, run["id"], items="1x Latte", amount=4.0)
    join_run(app_client, b_token, run["id"], items="1x Mocha", amount=4.5)
    rm = app_client.get(
        "/runs/mine", headers={"Authorization": f"Bearer {runner_token}"}
    )
    assert rm.status_code == 200
    for r in rm.json():
        for o in r.get("orders", []):
            assert "pin" not in o


def test_join_response_includes_4digit_pin(app_client):
    runner_token, _ = register_and_login(app_client, "fmt_runner@ncsu.edu")
    user_token, _ = register_and_login(app_client, "fmt_user@ncsu.edu")
    run = create_run(app_client, runner_token)
    rj = join_run(app_client, user_token, run["id"], items="2x Drink", amount=7.0)
    assert rj.status_code in (200, 201)
    body = rj.json()
    assert (
        "pin" in body
        and isinstance(body["pin"], str)
        and len(body["pin"]) == 4
        and body["pin"].isdigit()
    )


def test_unjoin_without_existing_order_returns_404(app_client):
    runner_token, _ = register_and_login(app_client, "uo_runner@ncsu.edu")
    user_token, _ = register_and_login(app_client, "uo_user@ncsu.edu")
    run = create_run(app_client, runner_token)
    ru = app_client.delete(
        f"/runs/{run['id']}/orders/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert ru.status_code == 404


def test_available_excludes_runner_and_full_runs(app_client):
    runner_token, _ = register_and_login(app_client, "av_runner@ncsu.edu")
    other_token, _ = register_and_login(app_client, "av_user@ncsu.edu")
    # capacity 1 run
    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]
    # Runner should not see their own run in available
    r_av_runner = app_client.get(
        "/runs/available", headers={"Authorization": f"Bearer {runner_token}"}
    )
    assert all(r["id"] != run_id for r in r_av_runner.json())
    # Other joins; then run should be absent from available due to full
    rj = join_run(app_client, other_token, run_id)
    assert rj.status_code in (200, 201)
    r_av_other = app_client.get(
        "/runs/available", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert all(r["id"] != run_id for r in r_av_other.json())


def test_runner_can_view_tip_amounts(app_client):
    runner_token, _ = register_and_login(app_client, "tip_runner@ncsu.edu")
    joiner_token, _ = register_and_login(app_client, "tip_joiner@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=2)
    run_id = run["id"]
    tip_value = 2.75
    join_resp = join_run(
        app_client,
        joiner_token,
        run_id,
        items="1x Cold Brew",
        amount=6.0,
        tip=tip_value,
    )
    assert join_resp.status_code in (200, 201)
    assert join_resp.json().get("tip") == pytest.approx(tip_value)

    # Runner should see the tip when viewing their runs
    runs_resp = app_client.get("/runs/mine", headers={"Authorization": f"Bearer {runner_token}"})
    assert runs_resp.status_code == 200
    run_entry = next(r for r in runs_resp.json() if r["id"] == run_id)
    assert any(abs(o.get("tip", -1) - tip_value) < 1e-6 for o in run_entry.get("orders", []))
