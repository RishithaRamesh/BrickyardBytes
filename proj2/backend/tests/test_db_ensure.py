import importlib.util
import sqlite3
import uuid
from pathlib import Path

import pytest


APP_DB_PATH = Path(__file__).resolve().parents[1] / "app" / "db.py"


def load_db_module(monkeypatch, url: str):
    module_name = f"app.db_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, APP_DB_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setenv("DATABASE_URL", url)
    spec.loader.exec_module(module)
    return module


def get_columns(db_path: Path, table: str):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(f"PRAGMA table_info('{table}')")
        return [row[1] for row in cursor.fetchall()]


def test_ensure_user_points_adds_missing_column(tmp_path, monkeypatch):
    db_path = tmp_path / "missing_points.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE user (id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT)"
        )
        conn.commit()

    module = load_db_module(monkeypatch, f"sqlite:///{db_path}")
    assert "points" not in get_columns(db_path, "user")
    module.ensure_user_points_column()
    assert "points" in get_columns(db_path, "user")


def test_ensure_foodrun_capacity_column(tmp_path, monkeypatch):
    db_path = tmp_path / "missing_capacity.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE foodrun (id INTEGER PRIMARY KEY, restaurant TEXT)"
        )
        conn.commit()

    module = load_db_module(monkeypatch, f"sqlite:///{db_path}")
    assert "capacity" not in get_columns(db_path, "foodrun")
    module.ensure_foodrun_capacity_column()
    assert "capacity" in get_columns(db_path, "foodrun")


def test_ensure_order_pin_column(tmp_path, monkeypatch):
    db_path = tmp_path / "missing_pin.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE 'order' (id INTEGER PRIMARY KEY, run_id INTEGER, items TEXT)"
        )
        conn.commit()

    module = load_db_module(monkeypatch, f"sqlite:///{db_path}")
    assert "pin" not in get_columns(db_path, "order")
    module.ensure_order_pin_column()
    assert "pin" in get_columns(db_path, "order")
