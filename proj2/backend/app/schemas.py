from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str  # maps to email
    points: int


class AuthResponse(BaseModel):
    user: UserOut
    token: str


class OrderCreate(BaseModel):
    items: str
    # enforce positive amounts for orders
    amount: float = Field(..., gt=0)
    tip: float = Field(default=0, ge=0)
    pin: Optional[str] = (
        None  # optional client-provided PIN; server will generate if missing
    )


class OrderResponse(BaseModel):
    # Public order details shared with runner and other joiners (no PIN)
    id: int
    run_id: int
    user_id: int
    status: str
    items: str
    amount: float
    tip: float
    user_email: str


class OrderJoinResponse(BaseModel):
    # Response for joining a run; includes the generated PIN for the joiner
    id: int
    run_id: int
    user_id: int
    status: str
    items: str
    amount: float
    tip: float
    user_email: str
    pin: str


class MyOrderResponse(BaseModel):
    id: int
    run_id: int
    items: str
    amount: float
    tip: float
    status: str
    pin: str


class FoodRunCreate(BaseModel):
    restaurant: str
    drop_point: str
    eta: str
    capacity: int = 5
    description: Optional[str] = None


class FoodRunResponse(FoodRunCreate):
    id: int
    runner_id: int
    runner_username: str
    status: str
    seats_remaining: int
    orders: List[OrderResponse] = []


class JoinedRunResponse(FoodRunResponse):
    my_order: Optional[MyOrderResponse] = None


class PointsResponse(BaseModel):
    points: int
    # represent redeemable value as integer dollars for clarity in API and tests
    points_value: int  # in dollars


class PinVerifyRequest(BaseModel):
    pin: str


class RunDescriptionRequest(BaseModel):
    restaurant: str
    drop_point: str
    eta: str


class RunDescriptionResponse(BaseModel):
    suggestion: str
