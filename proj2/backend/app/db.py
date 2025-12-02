import os
from contextlib import contextmanager
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


# Lightweight, startup-time safety check for SQLite dev DBs.
# If the 'points' column was added to the User model after the DB was created,
# make sure the column exists to avoid runtime errors without requiring a manual reset.
def ensure_user_points_column() -> None:
    try:
        # Only applicable for SQLite; other engines should use proper migrations.
        if not DATABASE_URL.startswith("sqlite"):
            return
        # Use a transaction so ALTER + UPDATE are committed together
        with engine.begin() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info('user')"))]
            if "points" not in cols:
                conn.execute(
                    text("ALTER TABLE user ADD COLUMN points INTEGER DEFAULT 0")
                )
                conn.execute(text("UPDATE user SET points = 0 WHERE points IS NULL"))
    except Exception:
        # Best-effort safeguard; if anything goes wrong here, don't block startup.
        # Users can still delete dev.db manually. Intentionally swallow to avoid crash.
        pass


def ensure_foodrun_capacity_column() -> None:
    try:
        if not DATABASE_URL.startswith("sqlite"):
            return
        with engine.begin() as conn:
            cols = [
                row[1] for row in conn.execute(text("PRAGMA table_info('foodrun')"))
            ]
            if "capacity" not in cols:
                conn.execute(
                    text("ALTER TABLE foodrun ADD COLUMN capacity INTEGER DEFAULT 5")
                )
                conn.execute(
                    text("UPDATE foodrun SET capacity = 5 WHERE capacity IS NULL")
                )
    except Exception:
        # Same best-effort approach
        pass


def ensure_foodrun_description_column() -> None:
    try:
        if not DATABASE_URL.startswith("sqlite"):
            return
        with engine.begin() as conn:
            cols = [
                row[1] for row in conn.execute(text("PRAGMA table_info('foodrun')"))
            ]
            if "description" not in cols:
                conn.execute(
                    text("ALTER TABLE foodrun ADD COLUMN description TEXT DEFAULT ''")
                )
            conn.execute(
                text(
                    "UPDATE foodrun SET description = '' "
                    "WHERE description IS NULL"
                )
            )
    except Exception:
        # Same best-effort posture as other ensure helpers
        pass


def ensure_order_pin_column() -> None:
    try:
        if not DATABASE_URL.startswith("sqlite"):
            return
        with engine.begin() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info('order')"))]
            if "pin" not in cols:
                conn.execute(text("ALTER TABLE 'order' ADD COLUMN pin TEXT"))
    except Exception:
        # Best-effort; ignore failures in dev
        pass


def ensure_foodrun_status_lowercase() -> None:
    """Normalize legacy rows so status comparisons behave consistently."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE foodrun "
                    "SET status = LOWER(TRIM(status)) "
                    "WHERE status IS NOT NULL AND status != LOWER(TRIM(status))"
                )
            )
    except Exception:
        # Same posture as other ensure_* helpers: never block startup
        pass


# Dependency for FastAPI routes


def get_session():
    with Session(engine) as session:
        yield session
