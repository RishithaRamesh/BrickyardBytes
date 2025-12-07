import sqlite3
import random
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "dev.db"   # resolved absolute path

# -----------------------------
# CONFIG
# -----------------------------
NUM_DAYS = 30
RUNS_PER_DAY_MIN = 3
RUNS_PER_DAY_MAX = 12
ACTIVE_RUNS_TO_GENERATE = 10

RESTAURANTS = [
    "Common Grounds", "Port City Java", "Talley Market",
    "Los Lobos", "One Earth", "Hill of Beans"
]

DROP_POINTS = [
    "Hunt Library", "EB2", "EB1", "DH Hill", "Centennial Oval",
    "Talley Student Union", "SAS Hall"
]

USERS = [1, 2, 3, 4, 5]   # assume 5 users exist already


# Probability weights for posting runs by hour.
# Weekdays exhibit breakfast (7-9), lunch (11-14), and dinner (17-20) spikes,
# with a deliberate surge at 17:00 (5 PM) to simulate the evening peak.
WEEKDAY_HOUR_WEIGHTS = {
    7: 0.8, 8: 1.2, 9: 1.0,
    11: 1.2, 12: 1.4, 13: 1.2, 14: 0.9,
    17: 1.6, 18: 1.3, 19: 1.1, 20: 0.9,
}

# Weekends start later but brunch (10-13) and evening (17-20) remain popular.
WEEKEND_HOUR_WEIGHTS = {
    9: 0.4, 10: 0.9,
    11: 1.3, 12: 1.4, 13: 1.2,
    17: 1.4, 18: 1.2, 19: 1.0, 20: 0.8,
}

OFF_PEAK_WEIGHT = 0.15
MAX_WEIGHT = max(max(WEEKDAY_HOUR_WEIGHTS.values()), max(WEEKEND_HOUR_WEIGHTS.values()))


def weighted_hour_choice(day):
    """Choose an hour weighted toward typical peak hours for the given day."""
    is_weekend = day.weekday() >= 5
    hour_weights = WEEKEND_HOUR_WEIGHTS if is_weekend else WEEKDAY_HOUR_WEIGHTS
    hours = []
    weights = []
    for h in range(7, 21):  # 7 AM → 8 PM
        hours.append(h)
        weights.append(hour_weights.get(h, OFF_PEAK_WEIGHT))
    return random.choices(hours, weights=weights, k=1)[0]


def runs_for_day(day):
    """Vary the number of runs so weekdays are busier than weekends."""
    base = random.randint(RUNS_PER_DAY_MIN, RUNS_PER_DAY_MAX)
    if day.weekday() < 5:
        base += random.randint(1, 3)
    else:
        base -= random.randint(0, 2)
    return max(RUNS_PER_DAY_MIN, base)


def demand_factor_for_hour(hour):
    """
    Increase order demand during hours that were weighted as peaks.
    Scales the base utilization using the same weight map to keep
    downstream analytics anchored in plausible real-world rhythms.
    """
    weekday_weight = WEEKDAY_HOUR_WEIGHTS.get(hour, OFF_PEAK_WEIGHT)
    weekend_weight = WEEKEND_HOUR_WEIGHTS.get(hour, OFF_PEAK_WEIGHT)
    # use the higher of the two to normalize the hour's demand
    normalized = max(weekday_weight, weekend_weight) / MAX_WEIGHT
    # base demand sits between 0.35-0.6, with peak hours pushing closer to 1.0
    base = random.uniform(0.35, 0.6)
    bump = normalized * random.uniform(0.3, 0.5)
    return min(1.1, base + bump)


def recalc_runner_points(cursor):
    """
    Reset runner points based on completed runs so the dev DB matches
    what the API would do when runs are completed.
    """
    cursor.execute("UPDATE user SET points = 0")
    cursor.execute(
        """
        SELECT fr.runner_id, SUM(o.amount) AS total_amount
        FROM foodrun fr
        JOIN "order" o ON o.run_id = fr.id
        WHERE fr.status = 'completed'
        GROUP BY fr.runner_id
        """
    )
    for runner_id, total_amount in cursor.fetchall():
        total_amount = total_amount or 0
        earned_points = round(total_amount / 10)
        cursor.execute(
            "UPDATE user SET points = ? WHERE id = ?", (int(earned_points), runner_id)
        )


def generate_active_runs(cursor, count):
    """Seed a set of active runs so the UI always has fresh data to show."""
    now = datetime.now()
    for _ in range(count):
        runner = random.choice(USERS)
        restaurant = random.choice(RESTAURANTS)
        drop = random.choice(DROP_POINTS)
        capacity = random.randint(2, 6)
        eta = f"{random.randint(10, 25)} mins"
        created_at = now - timedelta(minutes=random.randint(5, 90))
        run_id = insert_foodrun(
            cursor,
            runner,
            restaurant,
            drop,
            eta,
            capacity,
            "active",
            created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
        pending_orders = random.randint(0, max(1, capacity - 1))
        for _ in range(pending_orders):
            user = random.choice(USERS)
            order_time = created_at + timedelta(minutes=random.randint(1, 20))
            items = json.dumps(
                {
                    "item": random.choice(["Latte", "Bagel", "Pizza Slice", "Wrap"]),
                    "qty": random.randint(1, 2),
                }
            )
            insert_order(
                cursor,
                run_id,
                user,
                items,
                round(random.uniform(4.0, 14.0), 2),
                "pending",
                str(random.randint(1000, 9999)),
                order_time.strftime("%Y-%m-%d %H:%M:%S"),
            )


# -----------------------------
# INSERT HELPERS
# -----------------------------

def insert_foodrun(cursor, runner_id, restaurant, drop_point, eta, capacity, status, created_at):
    cursor.execute("""
        INSERT INTO foodrun (runner_id, restaurant, drop_point, eta, capacity, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (runner_id, restaurant, drop_point, eta, capacity, status, created_at))
    return cursor.lastrowid


def insert_order(cursor, run_id, user_id, items, amount, status, pin, created_at):
    cursor.execute("""
        INSERT INTO "order" (run_id, user_id, items, amount, status, pin, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (run_id, user_id, items, amount, status, pin, created_at))


# -----------------------------
# MAIN GENERATOR
# -----------------------------
def generate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # -------------------------------------
    # AUTO-RESET (Wipe old synthetic data)
    # -------------------------------------
    print("Resetting foodrun and order tables...")

    cur.execute('DELETE FROM "order";')
    cur.execute('DELETE FROM foodrun;')
    conn.commit()

    print("Tables cleared. Generating new synthetic data...")

    base_date = datetime.now() - timedelta(days=NUM_DAYS)

    for day_offset in range(NUM_DAYS):
        day = base_date + timedelta(days=day_offset)

        runs_today = runs_for_day(day)

        for _ in range(runs_today):
            hour = weighted_hour_choice(day)
            minute = random.randint(0, 59)
            run_created = day.replace(hour=hour, minute=minute, second=0)

            runner = random.choice(USERS)
            restaurant = random.choice(RESTAURANTS)
            drop = random.choice(DROP_POINTS)
            capacity = random.randint(1, 5)
            eta = f"{random.randint(5, 20)} mins"
            status = "completed"  # <-- forced completed

            run_id = insert_foodrun(
                cur, runner, restaurant, drop, eta, capacity, status,
                run_created.strftime("%Y-%m-%d %H:%M:%S")
            )

            # Orders
            demand_factor = demand_factor_for_hour(hour)
            num_orders = min(capacity, max(1, int(round(capacity * demand_factor))))

            for _ in range(num_orders):
                user = random.choice(USERS)
                order_time = run_created + timedelta(minutes=random.randint(1, 12))

                items = json.dumps({
                    "item": random.choice(["Latte", "Bagel", "Pizza Slice", "Wrap"]),
                    "qty": 1
                })

                insert_order(
                    cur,
                    run_id,
                    user,
                    items,
                    round(random.uniform(4.0, 14.0), 2),
                    "completed",
                    str(random.randint(1000, 9999)),
                    order_time.strftime("%Y-%m-%d %H:%M:%S")
                )

    print(f"Seeding {ACTIVE_RUNS_TO_GENERATE} active runs...")
    generate_active_runs(cur, ACTIVE_RUNS_TO_GENERATE)

    print("Recalculating runner points based on completed runs...")
    recalc_runner_points(cur)

    conn.commit()
    conn.close()
    print("Done! Synthetic completed run history generated.")


if __name__ == "__main__":
    generate()
