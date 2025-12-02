from conftest import register_and_login


def create_run(
    client,
    token,
    restaurant="Port City Java EBII",
    drop="Wolf Village",
    capacity=2,
    eta="12:00",
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


def join_run(client, token, run_id, items="1x Coffee", amount=3.5):
    return client.post(
        f"/runs/{run_id}/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": items, "amount": amount},
    )


def test_active_run_appears_in_mine(app_client):
    runner_token, _ = register_and_login(app_client, "ph_runner@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]
    mine = app_client.get(
        "/runs/mine", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    assert any(r["id"] == run_id and r["status"] == "active" for r in mine)


def test_completed_run_moves_to_runner_history(app_client):
    runner_token, _ = register_and_login(app_client, "ph_runner2@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]
    rc = app_client.put(
        f"/runs/{run_id}/complete", headers={"Authorization": f"Bearer {runner_token}"}
    )
    assert rc.status_code == 200
    mine_hist = app_client.get(
        "/runs/mine/history", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    assert any(r["id"] == run_id and r["status"] == "completed" for r in mine_hist)


def test_runner_history_sorted_newest_first(app_client):
    runner_token, _ = register_and_login(app_client, "ph_runner_sort@ncsu.edu")
    created_ids = []
    for idx in range(3):
        run = create_run(
            app_client,
            runner_token,
            restaurant=f"SortCafe {idx}",
            eta=f"12:0{idx}",
        )
        created_ids.append(run["id"])
        app_client.put(
            f"/runs/{run['id']}/complete",
            headers={"Authorization": f"Bearer {runner_token}"},
        )
    mine_hist = app_client.get(
        "/runs/mine/history", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    returned_ids = [entry["id"] for entry in mine_hist]
    assert returned_ids == list(reversed(created_ids))


def test_completed_run_appears_in_joined_history(app_client):
    runner_token, _ = register_and_login(app_client, "ph_runner3@ncsu.edu")
    u_token, _ = register_and_login(app_client, "ph_user@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]
    rj = join_run(app_client, u_token, run_id)
    assert rj.status_code in (200, 201)
    app_client.put(
        f"/runs/{run_id}/complete", headers={"Authorization": f"Bearer {runner_token}"}
    )
    joined_hist = app_client.get(
        "/runs/joined/history", headers={"Authorization": f"Bearer {u_token}"}
    ).json()
    assert any(r["id"] == run_id for r in joined_hist)


def test_joined_history_sorted_newest_first(app_client):
    runner_token, _ = register_and_login(app_client, "ph_runner_sort_join@ncsu.edu")
    u_token, _ = register_and_login(app_client, "ph_user_sort_join@ncsu.edu")
    run_ids = []
    for idx in range(3):
        run = create_run(
            app_client,
            runner_token,
            restaurant=f"JoinSort {idx}",
            eta=f"13:0{idx}",
        )
        run_ids.append(run["id"])
        join_resp = join_run(
            app_client,
            u_token,
            run["id"],
            items=f"{idx+1}x Item",
            amount=5.0 + idx,
        )
        assert join_resp.status_code in (200, 201)
        app_client.put(
            f"/runs/{run['id']}/complete",
            headers={"Authorization": f"Bearer {runner_token}"},
        )
    joined_hist = app_client.get(
        "/runs/joined/history", headers={"Authorization": f"Bearer {u_token}"}
    ).json()
    returned_ids = [entry["id"] for entry in joined_hist]
    assert returned_ids == list(reversed(run_ids))


def test_points_visible_after_completion(app_client):
    runner_token, _ = register_and_login(app_client, "pointsrunner@ncsu.edu")
    u_token, _ = register_and_login(app_client, "pointsuser@ncsu.edu")
    run = create_run(app_client, runner_token)
    j = join_run(app_client, u_token, run["id"], amount=30.0)
    assert j.status_code in (200, 201)
    app_client.put(
        f"/runs/{run['id']}/complete",
        headers={"Authorization": f"Bearer {runner_token}"},
    )
    gp = app_client.get("/points", headers={"Authorization": f"Bearer {runner_token}"})
    assert gp.status_code == 200
    body = gp.json()
    assert "points" in body and "points_value" in body


def test_points_rounding_behavior_and_redeem_edges(app_client):
    runner_token, _ = register_and_login(app_client, "roundrunner@ncsu.edu")
    u_token, _ = register_and_login(app_client, "rounduser@ncsu.edu")

    # 35.0 -> 3.5 -> round() -> 4 points
    r1 = create_run(app_client, runner_token)
    j1 = join_run(app_client, u_token, r1["id"], amount=35.0)
    assert j1.status_code in (200, 201)
    app_client.put(
        f"/runs/{r1['id']}/complete",
        headers={"Authorization": f"Bearer {runner_token}"},
    )

    gp1 = app_client.get(
        "/points", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    assert gp1["points"] == 4
    assert gp1["points_value"] == 0  # < 10 points -> $0 value

    # Add 30.0 -> +3 => total 7 points; still can't redeem
    r2 = create_run(app_client, runner_token)
    j2 = join_run(app_client, u_token, r2["id"], amount=30.0)
    assert j2.status_code in (200, 201)
    app_client.put(
        f"/runs/{r2['id']}/complete",
        headers={"Authorization": f"Bearer {runner_token}"},
    )

    gp2 = app_client.get(
        "/points", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    assert gp2["points"] == 7
    assert gp2["points_value"] == 0
    rd_fail = app_client.post(
        "/points/redeem", headers={"Authorization": f"Bearer {runner_token}"}
    )
    assert rd_fail.status_code == 400

    # Add 45.0 -> 4.5 -> round() -> 4 => total 11 -> redeem 10 -> $5 value, 1 remaining
    r3 = create_run(app_client, runner_token)
    j3 = join_run(app_client, u_token, r3["id"], amount=45.0)
    assert j3.status_code in (200, 201)
    app_client.put(
        f"/runs/{r3['id']}/complete",
        headers={"Authorization": f"Bearer {runner_token}"},
    )

    gp3 = app_client.get(
        "/points", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    assert gp3["points"] == 11
    assert gp3["points_value"] == 5

    rd_ok = app_client.post(
        "/points/redeem", headers={"Authorization": f"Bearer {runner_token}"}
    )
    assert rd_ok.status_code == 200
    rd_json = rd_ok.json()
    assert rd_json["points_redeemed"] == 10
    assert rd_json["value_redeemed"] == 5
    assert rd_json["remaining_points"] == 1


def test_joined_history_includes_my_pin_and_runner_details_hide_pins(app_client):
    runner_token, _ = register_and_login(app_client, "privrunner@ncsu.edu")
    u_token, _ = register_and_login(app_client, "privuser@ncsu.edu")

    run = create_run(app_client, runner_token, capacity=2)
    rj = join_run(app_client, u_token, run["id"], amount=12.0)
    assert rj.status_code in (200, 201)

    # Joined history contains my_order.pin after completion
    app_client.put(
        f"/runs/{run['id']}/complete",
        headers={"Authorization": f"Bearer {runner_token}"},
    )
    jhist = app_client.get(
        "/runs/joined/history", headers={"Authorization": f"Bearer {u_token}"}
    ).json()
    entry = next(x for x in jhist if x["id"] == run["id"])
    assert entry.get("my_order", {}).get("pin")

    # Runner details never expose pin in orders
    run2 = create_run(app_client, runner_token)
    u2_token, _ = register_and_login(app_client, "privuser2@ncsu.edu")
    join_run(app_client, u_token, run2["id"], amount=5.0)
    join_run(app_client, u2_token, run2["id"], amount=6.0)
    details = app_client.get(
        f"/runs/id/{run2['id']}", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    for o in details.get("orders", []):
        assert "pin" not in o


def test_runner_sees_uppercase_active_runs_and_can_complete(app_client):
    runner_token, _ = register_and_login(app_client, "case_runner@ncsu.edu")
    run = create_run(app_client, runner_token, capacity=1)
    run_id = run["id"]

    # Simulate legacy data with mixed-case status
    from sqlalchemy import text
    from app import db as dbmod

    with dbmod.engine.begin() as conn:
        conn.execute(
            text("UPDATE foodrun SET status=' Active  ' WHERE id=:rid"), {"rid": run_id}
        )

    mine = app_client.get(
        "/runs/mine", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    assert any(r["id"] == run_id for r in mine)

    complete = app_client.put(
        f"/runs/{run_id}/complete", headers={"Authorization": f"Bearer {runner_token}"}
    )
    assert complete.status_code == 200

    history = app_client.get(
        "/runs/mine/history", headers={"Authorization": f"Bearer {runner_token}"}
    ).json()
    assert any(
        r["id"] == run_id and r["status"] == "completed"
        for r in history
    )
