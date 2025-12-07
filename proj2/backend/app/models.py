from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, text


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # enforce unique via underlying SQLAlchemy Column (put index on the sa_column to avoid SQLModel conflict)
    email: str = Field(sa_column=Column(String, unique=True, index=True))
    password_hash: str
    points: int = Field(default=0, ge=0)
    created_at: Optional[str] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
        ),
    )


class FoodRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    runner_id: int = Field(foreign_key="user.id")
    restaurant: str
    drop_point: str
    eta: str
    capacity: int = Field(default=5)  # maximum number of joiners/orders
    status: str = Field(default="active")  # active, completed, cancelled
    created_at: Optional[str] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
        ),
    )


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="foodrun.id")
    user_id: int = Field(foreign_key="user.id")
    items: str  # JSON string of ordered items
    amount: float
    status: str = Field(default="pending")  # pending, paid, delivered
    pin: Optional[str] = None  # 4-digit PIN for order pickup verification
    created_at: Optional[str] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
        ),
    )


class RunnerReward(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    runner_id: int = Field(foreign_key="user.id")
    run_id: int = Field(foreign_key="foodrun.id")
    reason: str = Field(default="Peak hour bonus")
    points: int = Field(default=0, ge=0)
    awarded_at: Optional[str] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
        ),
    )
