from conftest import register_and_login


def create_run(
    client,
    token,
    restaurant="Common Grounds Cafe Hunt Library",
    drop="EBII",
    capacity=2,
    eta="11:00",
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


def join_run(client, token, run_id, items="1x Coffee", amount=3.5, tip=0.0):
    return client.post(
        f"/runs/{run_id}/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": items, "amount": amount, "tip": tip},
    )


def test_new_broadcast_visible_to_other_users(app_client):
    runner_token, _ = register_and_login(app_client, "broad@ncsu.edu")
    other_token, _ = register_and_login(app_client, "someone@ncsu.edu")

    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]

    r_av = app_client.get(
        "/runs/available", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert any(r["id"] == run_id for r in r_av.json())


def test_broadcast_removed_from_available_when_full(app_client):
    runner_token, _ = register_and_login(app_client, "broad2@ncsu.edu")
    other_token, _ = register_and_login(app_client, "someone2@ncsu.edu")

    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]
    rj = join_run(app_client, other_token, run_id, items="2x Latte", amount=8.0)
    assert rj.status_code in (200, 201)

    r_av2 = app_client.get(
        "/runs/available", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert all(r["id"] != run_id for r in r_av2.json())


def test_runner_can_verify_pin_and_mark_delivered(app_client):
    runner_token, _ = register_and_login(app_client, "vrunner@ncsu.edu")
    u1_token, _ = register_and_login(app_client, "vu1@ncsu.edu")

    run = create_run(app_client, runner_token, capacity=2)
    run_id = run["id"]
    j = join_run(app_client, u1_token, run_id, items="1x Mocha", amount=4.5)
    assert j.status_code in (200, 201)

    rj = app_client.get("/runs/joined", headers={"Authorization": f"Bearer {u1_token}"})
    my_run = next(x for x in rj.json() if x["id"] == run_id)
    order = my_run["my_order"]

    rv = app_client.post(
        f"/runs/{run_id}/orders/{order['id']}/verify-pin",
        headers={"Authorization": f"Bearer {runner_token}"},
        json={"pin": order["pin"]},
    )
    assert rv.status_code in (200, 204)


def test_runner_can_complete_run(app_client):
    runner_token, _ = register_and_login(app_client, "crunner@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=1)
    rc = app_client.put(
        f"/runs/{run['id']}/complete",
        headers={"Authorization": f"Bearer {runner_token}"},
    )
    assert rc.status_code == 200


def test_runner_can_cancel_run(app_client):
    runner_token, _ = register_and_login(app_client, "canrunner@ncsu.edu")
    run2 = create_run(app_client, runner_token, capacity=1)
    rcancel = app_client.put(
        f"/runs/{run2['id']}/cancel",
        headers={"Authorization": f"Bearer {runner_token}"},
    )
    assert rcancel.status_code == 200


def test_cannot_join_after_complete(app_client):
    runner_token, _ = register_and_login(app_client, "closeflow@ncsu.edu")
    u_token, _ = register_and_login(app_client, "closeuser@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=2)
    rid = run["id"]
    app_client.put(
        f"/runs/{rid}/complete", headers={"Authorization": f"Bearer {runner_token}"}
    )
    rj1 = join_run(app_client, u_token, rid)
    assert rj1.status_code == 400


def test_cannot_join_after_cancel(app_client):
    runner_token, _ = register_and_login(app_client, "closeflow2@ncsu.edu")
    u_token, _ = register_and_login(app_client, "closeuser2@ncsu.edu")
    run2 = create_run(app_client, runner_token, capacity=2)
    rid2 = run2["id"]
    app_client.put(
        f"/runs/{rid2}/cancel", headers={"Authorization": f"Bearer {runner_token}"}
    )
    rj2 = join_run(app_client, u_token, rid2)
    assert rj2.status_code == 400
