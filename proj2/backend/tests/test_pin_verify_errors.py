from conftest import register_and_login


def create_run(
    client, token, restaurant="Talley One Earth", drop="EBII", capacity=2, eta="12:30"
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


def join_run(client, token, run_id, items="1x Tea", amount=2.5, tip=0.0):
    return client.post(
        f"/runs/{run_id}/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": items, "amount": amount, "tip": tip},
    )


def test_non_runner_cannot_verify_pin(app_client):
    runner_token, _ = register_and_login(app_client, "pvrunner@ncsu.edu")
    user_token, _ = register_and_login(app_client, "pvuser@ncsu.edu")
    other_token, _ = register_and_login(app_client, "pvother@ncsu.edu")

    run = create_run(app_client, runner_token)
    j = join_run(app_client, user_token, run["id"]).json()

    rv = app_client.post(
        f"/runs/{run['id']}/orders/{j['id']}/verify-pin",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"pin": j["pin"]},
    )
    assert rv.status_code == 403


def test_incorrect_pin_rejected_and_cancelled_not_verifiable(app_client):
    runner_token, _ = register_and_login(app_client, "pver@ncsu.edu")
    user_token, _ = register_and_login(app_client, "pveu@ncsu.edu")

    run = create_run(app_client, runner_token)
    j = join_run(app_client, user_token, run["id"]).json()

    # wrong pin
    rv_wrong = app_client.post(
        f"/runs/{run['id']}/orders/{j['id']}/verify-pin",
        headers={"Authorization": f"Bearer {runner_token}"},
        json={"pin": "0000" if j["pin"] != "0000" else "9999"},
    )
    assert rv_wrong.status_code == 400

    # cancel order
    app_client.delete(
        f"/runs/{run['id']}/orders/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    rv_cancel = app_client.post(
        f"/runs/{run['id']}/orders/{j['id']}/verify-pin",
        headers={"Authorization": f"Bearer {runner_token}"},
        json={"pin": j["pin"]},
    )
    assert rv_cancel.status_code == 400


def test_mismatched_run_order_returns_404(app_client):
    runner_token, _ = register_and_login(app_client, "pvmr@ncsu.edu")
    user_token, _ = register_and_login(app_client, "pvmu@ncsu.edu")

    run1 = create_run(app_client, runner_token)
    run2 = create_run(app_client, runner_token)

    j = join_run(app_client, user_token, run1["id"]).json()

    rv = app_client.post(
        f"/runs/{run2['id']}/orders/{j['id']}/verify-pin",
        headers={"Authorization": f"Bearer {runner_token}"},
        json={"pin": j["pin"]},
    )
    assert rv.status_code == 404
