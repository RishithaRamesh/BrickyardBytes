import os
from typing import List
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from contextlib import asynccontextmanager
import httpx

from .db import (
    create_db_and_tables,
    get_session,
    ensure_user_points_column,
    ensure_foodrun_capacity_column,
    ensure_foodrun_description_column,
    ensure_order_pin_column,
    ensure_order_tip_column,
    ensure_foodrun_status_lowercase,
)
from .models import User, FoodRun, Order
from .schemas import (
    AuthRequest,
    AuthResponse,
    UserOut,
    FoodRunCreate,
    FoodRunResponse,
    JoinedRunResponse,
    OrderCreate,
    OrderResponse,
    OrderJoinResponse,
    PointsResponse,
    PinVerifyRequest,
    RunDescriptionRequest,
    RunDescriptionResponse,
)
from .auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user_claims,
)

load_dotenv()


ACTIVE_STATUS = "active"


def normalize_status(value: str | None) -> str:
    cleaned = (value or "").strip().lower()
    return cleaned or ACTIVE_STATUS


def is_active_status(value: str | None) -> bool:
    return normalize_status(value) == ACTIVE_STATUS


def active_status_expr():
    return func.lower(func.trim(FoodRun.status))


def build_default_run_description(restaurant: str, drop_point: str, eta: str) -> str:
    """Fallback copy when AI is unavailable."""
    restaurant_text = restaurant.strip() if restaurant else "the dining hall"
    drop_text = drop_point.strip() if drop_point else "the usual spot"
    eta_text = eta.strip() if eta else "soon"
    return (
        f"Heading to {restaurant_text} around {eta_text}; "
        f"meet me at {drop_text} if you want me to grab something."
    )


def resolve_run_description(
    restaurant: str | None, drop_point: str | None, eta: str | None, description: str | None
) -> str:
    text = (description or "").strip()
    if text:
        return text
    return build_default_run_description(restaurant or "", drop_point or "", eta or "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables on startup
    create_db_and_tables()
    # Ensure SQLite dev DBs have newly added columns (e.g., 'points')
    ensure_user_points_column()
    ensure_foodrun_capacity_column()
    ensure_foodrun_description_column()
    ensure_order_pin_column()
    ensure_order_tip_column()
    ensure_foodrun_status_lowercase()
    yield


origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173")
origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app = FastAPI(title="CSC510 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/ai/run-description", response_model=RunDescriptionResponse)
def generate_run_description(
    payload: RunDescriptionRequest, claims=Depends(get_current_user_claims)
):
    # require auth but we only need the fact that the token was valid
    _ = claims
    default_suggestion = build_default_run_description(
        payload.restaurant, payload.drop_point, payload.eta
    )
    api_key = os.getenv("AI_RUN_DESC_KEY")
    api_url = os.getenv(
        "AI_RUN_DESC_URL", "https://api.openai.com/v1/chat/completions"
    )
    model = os.getenv("AI_RUN_DESC_MODEL", "gpt-4o-mini")
    if not api_key:
        return {"suggestion": default_suggestion}
    try:
        response = httpx.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You create short, friendly, single-sentence blurbs advertising a campus food run.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Write a concise (<=25 words) invitation for this run:\n"
                            f"Restaurant: {payload.restaurant}\n"
                            f"Drop point: {payload.drop_point}\n"
                            f"ETA: {payload.eta}"
                        ),
                    },
                ],
                "temperature": 0.4,
                "max_tokens": 80,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        suggestion = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not suggestion:
            raise ValueError("Empty AI response")
        return {"suggestion": suggestion}
    except Exception:
        # gracefully fallback to deterministic copy
        return {"suggestion": default_suggestion}


@app.post("/auth/register", response_model=AuthResponse)
def register(payload: AuthRequest, session: Session = Depends(get_session)):
    # Enforce NCSU email domain for registration
    if not str(payload.email).lower().endswith("@ncsu.edu"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only NCSU accounts are allowed to register/login",
        )
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists"
        )

    user = User(email=payload.email, password_hash=get_password_hash(payload.password))
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists"
        )

    token = create_access_token(sub=user.id, email=user.email)
    return {
        "user": {"id": user.id, "username": user.email, "points": user.points},
        "token": token,
    }


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest, session: Session = Depends(get_session)):
    # Enforce NCSU email domain for login
    if not str(payload.email).lower().endswith("@ncsu.edu"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only NCSU accounts are allowed to register/login",
        )
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = create_access_token(sub=user.id, email=user.email)
    return {
        "user": {"id": user.id, "username": user.email, "points": int(user.points)},
        "token": token,
    }


@app.get("/auth/me", response_model=UserOut)
def me(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.id == int(claims["sub"]))).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"id": user.id, "username": user.email, "points": user.points}


@app.post("/runs", response_model=FoodRunResponse)
def create_run(
    run: FoodRunCreate,
    claims=Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    user_id = int(claims["sub"])
    payload = run.model_dump()
    payload["description"] = resolve_run_description(
        payload.get("restaurant"),
        payload.get("drop_point"),
        payload.get("eta"),
        payload.get("description"),
    )
    food_run = FoodRun(**payload, runner_id=user_id)
    food_run.status = normalize_status(food_run.status)
    session.add(food_run)
    session.commit()
    session.refresh(food_run)
    # respond with seats_remaining derived from capacity - current orders
    orders_count = session.exec(
        select(Order).where(Order.run_id == food_run.id, Order.status != "cancelled")
    ).all()
    seats_remaining = max(food_run.capacity - len(orders_count), 0)
    base = food_run.model_dump(
        include={
            "id",
            "runner_id",
            "restaurant",
            "drop_point",
            "eta",
            "capacity",
            "status",
            "description",
        }
    )
    base["status"] = normalize_status(base.get("status"))
    base["description"] = resolve_run_description(
        base.get("restaurant"), base.get("drop_point"), base.get("eta"), base.get("description")
    )
    return {
        **base,
        "runner_username": claims.get("email", str(user_id)),
        "seats_remaining": seats_remaining,
        "orders": [],
    }


@app.get("/runs", response_model=List[FoodRunResponse])
def list_runs(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    runs = session.exec(select(FoodRun)).all()
    # attach seats_remaining for each run
    responses = []
    for r in runs:
        count = session.exec(
            select(Order).where(Order.run_id == r.id, Order.status != "cancelled")
        ).all()
        seats_remaining = max(r.capacity - len(count), 0)
        # fetch runner email
        runner = session.get(User, r.runner_id)
        base = r.model_dump(
            include={
                "id",
                "runner_id",
                "restaurant",
                "drop_point",
                "eta",
                "capacity",
                "status",
                "description",
            }
        )
        base["status"] = normalize_status(base.get("status"))
        base["description"] = resolve_run_description(
            base.get("restaurant"), base.get("drop_point"), base.get("eta"), base.get("description")
        )
        responses.append(
            {
                **base,
                "runner_username": runner.email if runner else str(r.runner_id),
                "seats_remaining": seats_remaining,
                "orders": [],
            }
        )
    return responses


@app.post("/runs/{run_id}/orders", response_model=OrderJoinResponse)
def create_order(
    run_id: int,
    order: OrderCreate,
    claims=Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    user_id = int(claims["sub"])
    food_run = session.get(FoodRun, run_id)
    if not food_run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not is_active_status(food_run.status):
        raise HTTPException(status_code=400, detail="Run is not active")
    if food_run.runner_id == user_id:
        raise HTTPException(status_code=400, detail="Runner cannot join own run")
    # enforce capacity and prevent duplicate join
    existing = session.exec(
        select(Order).where(
            Order.run_id == run_id,
            Order.user_id == user_id,
            Order.status != "cancelled",
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already joined this run")
    current_count = session.exec(
        select(Order).where(Order.run_id == run_id, Order.status != "cancelled")
    ).all()
    if len(current_count) >= food_run.capacity:
        raise HTTPException(status_code=400, detail="Run is full")

    # ensure a 4-digit PIN
    pin = (
        order.pin if order.pin else f"{int(os.urandom(2).hex(), 16) % 9000 + 1000:04d}"
    )
    order_row = Order(
        **{**order.model_dump(), "pin": pin}, run_id=run_id, user_id=user_id
    )
    session.add(order_row)
    session.commit()
    session.refresh(order_row)
    u = session.get(User, user_id)
    return {
        "id": order_row.id,
        "run_id": order_row.run_id,
        "user_id": order_row.user_id,
        "status": order_row.status,
        "items": order_row.items,
        "amount": order_row.amount,
        "tip": order_row.tip,
        "user_email": u.email if u else str(user_id),
        "pin": pin,
    }


@app.post("/runs/{run_id}/orders/{order_id}/verify-pin")
def verify_order_pin(
    run_id: int,
    order_id: int,
    payload: PinVerifyRequest,
    claims=Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    user_id = int(claims["sub"])
    run = session.get(FoodRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.runner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    order = session.get(Order, order_id)
    if not order or order.run_id != run_id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Order cancelled")
    if not order.pin:
        raise HTTPException(status_code=400, detail="No PIN set for this order")
    if str(order.pin) != str(payload.pin):
        raise HTTPException(status_code=400, detail="Incorrect PIN")
    order.status = "delivered"
    session.commit()
    return {"message": "PIN verified. Order marked delivered."}


@app.delete("/runs/{run_id}/orders/me")
def cancel_my_order(
    run_id: int,
    claims=Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    user_id = int(claims["sub"])
    ord = session.exec(
        select(Order).where(
            Order.run_id == run_id,
            Order.user_id == user_id,
            Order.status != "cancelled",
        )
    ).first()
    if not ord:
        raise HTTPException(status_code=404, detail="No active order to cancel")
    ord.status = "cancelled"
    session.commit()
    return {"message": "Order cancelled"}


@app.get("/runs/available", response_model=List[FoodRunResponse])
def list_available_runs(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    user_id = int(claims["sub"])
    runs = session.exec(
        select(FoodRun).where(
            active_status_expr() == ACTIVE_STATUS, FoodRun.runner_id != user_id
        )
    ).all()
    responses = []
    for r in runs:
        count = session.exec(
            select(Order).where(Order.run_id == r.id, Order.status != "cancelled")
        ).all()
        seats_remaining = max(r.capacity - len(count), 0)
        if seats_remaining > 0:
            runner = session.get(User, r.runner_id)
            base = r.model_dump(
                include={
                    "id",
                    "runner_id",
                    "restaurant",
                    "drop_point",
                    "eta",
                    "capacity",
                    "status",
                    "description",
                }
            )
            base["status"] = normalize_status(base.get("status"))
            base["description"] = resolve_run_description(
                base.get("restaurant"), base.get("drop_point"), base.get("eta"), base.get("description")
            )
            responses.append(
                {
                    **base,
                    "runner_username": runner.email if runner else str(r.runner_id),
                    "seats_remaining": seats_remaining,
                    "orders": [],
                }
            )
    return responses


@app.get("/runs/mine", response_model=List[FoodRunResponse])
def list_my_runs(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    user_id = int(claims["sub"])
    runs = session.exec(
        select(FoodRun).where(
            FoodRun.runner_id == user_id,
            active_status_expr() == ACTIVE_STATUS,
        )
    ).all()
    responses = []
    for r in runs:
        orders = session.exec(
            select(Order).where(Order.run_id == r.id, Order.status != "cancelled")
        ).all()
        seats_remaining = max(r.capacity - len(orders), 0)
        runner = session.get(User, r.runner_id)
        # build orders payload with user emails
        order_payload = []
        for o in orders:
            u = session.get(User, o.user_id)
            order_payload.append(
                {
                    "id": o.id,
                    "run_id": o.run_id,
                    "user_id": o.user_id,
                    "status": o.status,
                    "items": o.items,
                    "amount": o.amount,
                    "tip": o.tip,
                    "user_email": u.email if u else str(o.user_id),
                }
            )
        base = r.model_dump(
            include={
                "id",
                "runner_id",
                "restaurant",
                "drop_point",
                "eta",
                "capacity",
                "status",
                "description",
            }
        )
        base["status"] = normalize_status(base.get("status"))
        base["description"] = resolve_run_description(
            base.get("restaurant"), base.get("drop_point"), base.get("eta"), base.get("description")
        )
        responses.append(
            {
                **base,
                "runner_username": runner.email if runner else str(r.runner_id),
                "seats_remaining": seats_remaining,
                "orders": order_payload,
            }
        )
    return responses


@app.get("/runs/id/{run_id}", response_model=FoodRunResponse)
def get_run_details(
    run_id: int,
    claims=Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    user_id = int(claims["sub"])
    run = session.get(FoodRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.runner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    orders = session.exec(
        select(Order).where(Order.run_id == run.id, Order.status != "cancelled")
    ).all()
    seats_remaining = max(run.capacity - len(orders), 0)
    runner = session.get(User, run.runner_id)

    order_payload = []
    for o in orders:
        u = session.get(User, o.user_id)
        order_payload.append(
            {
                "id": o.id,
                "run_id": o.run_id,
                "user_id": o.user_id,
                "status": o.status,
                "items": o.items,
                "amount": o.amount,
                "tip": o.tip,
                "user_email": u.email if u else str(o.user_id),
            }
        )

    base = run.model_dump(
        include={
            "id",
            "runner_id",
            "restaurant",
            "drop_point",
            "eta",
            "capacity",
            "status",
            "description",
        }
    )
    base["status"] = normalize_status(base.get("status"))
    base["description"] = resolve_run_description(
        base.get("restaurant"), base.get("drop_point"), base.get("eta"), base.get("description")
    )
    return {
        **base,
        "runner_username": runner.email if runner else str(run.runner_id),
        "seats_remaining": seats_remaining,
        "orders": order_payload,
    }


@app.get("/runs/joined", response_model=List[JoinedRunResponse])
def list_joined_runs(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    user_id = int(claims["sub"])
    # Find runs that have a non-cancelled order by this user
    stmt = (
        select(Order.run_id)
        .where(
            Order.user_id == user_id,
            Order.status != "cancelled",
        )
        .distinct()
    )
    # Some SQLModel/SQLAlchemy versions return scalars directly; others return 1-tuples.
    rows = session.exec(stmt).all()
    run_ids = [row[0] if isinstance(row, (list, tuple)) else row for row in rows]
    if not run_ids:
        return []
    runs = session.exec(
        select(FoodRun).where(
            FoodRun.id.in_(run_ids), active_status_expr() == ACTIVE_STATUS
        )
    ).all()
    responses = []
    for r in runs:
        count = session.exec(
            select(Order).where(Order.run_id == r.id, Order.status != "cancelled")
        ).all()
        cap = r.capacity or 0
        seats_remaining = max(cap - len(count), 0)
        runner = session.get(User, r.runner_id)
        # find my order for this run (expose pin to the owner of the order only)
        mine = session.exec(
            select(Order).where(
                Order.run_id == r.id,
                Order.user_id == user_id,
                Order.status != "cancelled",
            )
        ).first()
        # Build explicit payload to avoid any None values breaking response validation
        description = resolve_run_description(r.restaurant, r.drop_point, r.eta, r.description)
        payload = {
            "id": r.id,
            "runner_id": r.runner_id,
            "restaurant": r.restaurant or "",
            "drop_point": r.drop_point or "",
            "eta": r.eta or "",
            "capacity": cap,
            "status": normalize_status(r.status),
            "runner_username": runner.email if runner else str(r.runner_id),
            "seats_remaining": seats_remaining,
            "orders": [],
            "description": description,
        }
        if mine:
            payload["my_order"] = {
                "id": mine.id,
                "run_id": mine.run_id,
                "items": mine.items,
                "amount": mine.amount,
                "tip": mine.tip,
                "status": mine.status,
                "pin": mine.pin or "",
            }
        responses.append(payload)
    return responses


@app.get("/runs/mine/history", response_model=List[FoodRunResponse])
def list_my_runs_history(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    user_id = int(claims["sub"])
    runs = session.exec(
        select(FoodRun).where(
            FoodRun.runner_id == user_id,
            active_status_expr() != ACTIVE_STATUS,
        ).order_by(FoodRun.created_at.desc(), FoodRun.id.desc())
    ).all()
    responses = []
    for r in runs:
        orders = session.exec(select(Order).where(Order.run_id == r.id)).all()
        runner = session.get(User, r.runner_id)
        order_payload = []
        for o in orders:
            u = session.get(User, o.user_id)
            order_payload.append(
                {
                    "id": o.id,
                    "run_id": o.run_id,
                    "user_id": o.user_id,
                    "status": o.status,
                    "items": o.items,
                    "amount": o.amount,
                    "tip": o.tip,
                    "user_email": u.email if u else str(o.user_id),
                }
            )
        base = r.model_dump(
            include={
                "id",
                "runner_id",
                "restaurant",
                "drop_point",
                "eta",
                "capacity",
                "status",
                "description",
            }
        )
        base["status"] = normalize_status(base.get("status"))
        base["description"] = resolve_run_description(
            base.get("restaurant"), base.get("drop_point"), base.get("eta"), base.get("description")
        )
        responses.append(
            {
                **base,
                "runner_username": runner.email if runner else str(r.runner_id),
                "seats_remaining": 0,
                "orders": order_payload,
            }
        )
    return responses


@app.get("/runs/joined/history", response_model=List[JoinedRunResponse])
def list_joined_runs_history(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    user_id = int(claims["sub"])
    stmt = select(Order.run_id).where(Order.user_id == user_id).distinct()
    rows = session.exec(stmt).all()
    run_ids = [row[0] if isinstance(row, (list, tuple)) else row for row in rows]
    if not run_ids:
        return []
    runs = session.exec(
        select(FoodRun).where(
            FoodRun.id.in_(run_ids), active_status_expr() != ACTIVE_STATUS
        ).order_by(FoodRun.created_at.desc(), FoodRun.id.desc())
    ).all()
    responses = []
    for r in runs:
        runner = session.get(User, r.runner_id)
        # include my_order for historical reference
        mine = session.exec(
            select(Order).where(
                Order.run_id == r.id,
                Order.user_id == user_id,
            )
        ).first()
        base = r.model_dump(
            include={
                "id",
                "runner_id",
                "restaurant",
                "drop_point",
                "eta",
                "capacity",
                "status",
                "description",
            }
        )
        base["status"] = normalize_status(base.get("status"))
        base["description"] = resolve_run_description(
            base.get("restaurant"), base.get("drop_point"), base.get("eta"), base.get("description")
        )
        payload = {
            **base,
            "runner_username": runner.email if runner else str(r.runner_id),
            "seats_remaining": 0,
            "orders": [],
        }
        if mine:
            payload["my_order"] = {
                "id": mine.id,
                "run_id": mine.run_id,
                "items": mine.items,
                "amount": mine.amount,
                "tip": mine.tip,
                "status": mine.status,
                "pin": (mine.pin or ""),
            }
        responses.append(payload)
    return responses


@app.delete("/runs/{run_id}/orders/{order_id}")
def runner_remove_order(
    run_id: int,
    order_id: int,
    claims=Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    user_id = int(claims["sub"])
    run = session.get(FoodRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.runner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not is_active_status(run.status):
        raise HTTPException(status_code=400, detail="Run is not active")
    ord = session.get(Order, order_id)
    if not ord or ord.run_id != run_id or ord.status == "cancelled":
        raise HTTPException(status_code=404, detail="Order not found")
    ord.status = "cancelled"
    session.commit()
    return {"message": "Order removed"}


@app.put("/runs/{run_id}/complete")
def complete_run(
    run_id: int,
    claims=Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    user_id = int(claims["sub"])
    food_run = session.get(FoodRun, run_id)
    if not food_run:
        raise HTTPException(status_code=404, detail="Run not found")
    if food_run.runner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not is_active_status(food_run.status):
        raise HTTPException(status_code=400, detail="Run is not active")

    # Calculate total bill and points
    orders = session.exec(select(Order).where(Order.run_id == run_id)).all()
    total_amount = sum(order.amount for order in orders)
    earned_points = round(
        total_amount / 10
    )  # 1 point per $10, rounded to nearest integer

    # Update run status
    food_run.status = normalize_status("completed")

    # Update runner's points
    runner = session.get(User, user_id)
    runner.points += earned_points

    session.commit()
    return {"message": "Run completed", "points_earned": earned_points}


@app.put("/runs/{run_id}/cancel")
def cancel_run(
    run_id: int,
    claims=Depends(get_current_user_claims),
    session: Session = Depends(get_session),
):
    user_id = int(claims["sub"])
    food_run = session.get(FoodRun, run_id)
    if not food_run:
        raise HTTPException(status_code=404, detail="Run not found")
    if food_run.runner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not is_active_status(food_run.status):
        raise HTTPException(status_code=400, detail="Run is not active")
    food_run.status = normalize_status("cancelled")
    session.commit()
    return {"message": "Run cancelled"}


@app.get("/points", response_model=PointsResponse)
def get_points(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    user_id = int(claims["sub"])
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    points_value = int((user.points // 10) * 5)  # $5 per 10 points, ensuring integer
    return {"points": int(user.points), "points_value": points_value}


@app.post("/points/redeem")
def redeem_points(
    claims=Depends(get_current_user_claims), session: Session = Depends(get_session)
):
    user_id = int(claims["sub"])
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    redeemable_points = (user.points // 10) * 10  # Round down to nearest 10
    if redeemable_points < 10:
        raise HTTPException(status_code=400, detail="Not enough points to redeem")

    redemption_value = (redeemable_points // 10) * 5  # $5 per 10 points
    user.points -= redeemable_points
    session.commit()

    return {
        "points_redeemed": redeemable_points,
        "value_redeemed": redemption_value,
        "remaining_points": user.points,
    }
