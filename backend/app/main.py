import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import DateTime, Float, ForeignKey, String, create_engine, func, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bea.db")
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-me")
ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30), default="admin")
    password_hash: Mapped[str] = mapped_column(String(255))


class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    origin: Mapped[str] = mapped_column(String(160))
    destination: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(250), default="")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    trips: Mapped[list["Trip"]] = relationship(back_populates="shipment")


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    model: Mapped[str] = mapped_column(String(100))
    capacity_kg: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="available")


class Driver(Base):
    __tablename__ = "drivers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    license_number: Mapped[str] = mapped_column(String(60), unique=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    status: Mapped[str] = mapped_column(String(30), default="available")


class Trip(Base):
    __tablename__ = "trips"
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"))
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    shipment: Mapped[Shipment] = relationship(back_populates="trips")
    vehicle: Mapped[Vehicle | None] = relationship()
    driver: Mapped[Driver | None] = relationship()


class Maintenance(Base):
    __tablename__ = "maintenance"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    description: Mapped[str] = mapped_column(String(250))
    cost: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    service_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    vehicle: Mapped[Vehicle] = relationship()


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(60))
    amount: Mapped[float] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(String(250), default="")
    incurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ShipmentIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120)
    origin: str = Field(min_length=2, max_length=160)
    destination: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=250)


class ShipmentOut(ORMModel):
    id: int
    tracking_number: str
    customer_name: str
    origin: str
    destination: str
    description: str
    status: str
    created_at: datetime


class VehicleIn(BaseModel):
    plate_number: str = Field(min_length=2, max_length=30)
    model: str = Field(min_length=2, max_length=100)
    capacity_kg: float = Field(gt=0)


class VehicleOut(ORMModel):
    id: int
    plate_number: str
    model: str
    capacity_kg: float
    status: str


class DriverIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    license_number: str = Field(min_length=3, max_length=60)
    phone: str = Field(default="", max_length=30)


class DriverOut(ORMModel):
    id: int
    name: str
    license_number: str
    phone: str
    status: str


class TripIn(BaseModel):
    shipment_id: int


class AssignIn(BaseModel):
    vehicle_id: int
    driver_id: int


class TripOut(ORMModel):
    id: int
    shipment_id: int
    vehicle_id: int | None
    driver_id: int | None
    status: str
    scheduled_at: datetime


class TripStatusIn(BaseModel):
    status: str


class MaintenanceIn(BaseModel):
    vehicle_id: int
    description: str = Field(min_length=3, max_length=250)
    cost: float = Field(ge=0)
    status: Literal["scheduled", "in_progress", "completed"] = "scheduled"


class MaintenanceOut(ORMModel):
    id: int
    vehicle_id: int
    description: str
    cost: float
    status: str
    service_date: datetime


class ExpenseIn(BaseModel):
    category: str = Field(min_length=2, max_length=60)
    amount: float = Field(gt=0)
    notes: str = Field(default="", max_length=250)


class ExpenseOut(ORMModel):
    id: int
    category: str
    amount: float
    notes: str
    incurred_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    role: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    role: str = Field(pattern="^(admin|logistics_manager|fleet_manager)$")
    password: str = Field(min_length=10, max_length=100)


def require_roles(*roles: str):
    def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Your role cannot perform this operation")
        return user
    return check


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]) -> User:
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token",
                          headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError, TypeError):
        raise error
    user = db.get(User, user_id)
    if user is None:
        raise error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
Db = Annotated[Session, Depends(get_db)]
app = FastAPI(title="Enterprise Logistics and Fleet Operations API", version="1.0.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        demo_email = "admin@bea.local"
        if db.scalar(select(User).where(User.email == demo_email)) is None:
            db.add(User(email=demo_email, name="Demo Administrator", role="admin",
                        password_hash=password_hash.hash("Admin123!")))
            db.commit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/token", response_model=TokenOut)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Db) -> TokenOut:
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not password_hash.verify(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = jwt.encode({"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(hours=8)},
                       JWT_SECRET, algorithm=ALGORITHM)
    return TokenOut(access_token=token, name=user.name, role=user.role)


@app.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@app.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, user: Annotated[User, Depends(require_roles("admin"))], db: Db) -> User:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    item = User(email=email, name=body.name, role=body.role, password_hash=password_hash.hash(body.password))
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.get("/dashboard")
def dashboard(user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> dict[str, int | float]:
    return {
        "shipments": db.scalar(select(func.count()).select_from(Shipment)) or 0,
        "in_transit": db.scalar(select(func.count()).select_from(Shipment).where(Shipment.status == "in_transit")) or 0,
        "available_vehicles": db.scalar(select(func.count()).select_from(Vehicle).where(Vehicle.status == "available")) or 0,
        "available_drivers": db.scalar(select(func.count()).select_from(Driver).where(Driver.status == "available")) or 0,
        "open_maintenance": db.scalar(select(func.count()).select_from(Maintenance).where(Maintenance.status != "completed")) or 0,
        "expense_total": db.scalar(select(func.coalesce(func.sum(Expense.amount), 0.0))) or 0.0,
    }


@app.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> list[Shipment]:
    return list(db.scalars(select(Shipment).order_by(Shipment.id.desc())).all())


@app.post("/shipments", response_model=ShipmentOut, status_code=201)
def create_shipment(body: ShipmentIn, user: Annotated[User, Depends(require_roles("admin", "logistics_manager"))], db: Db) -> Shipment:
    item = Shipment(tracking_number=f"BEA-{datetime.now(UTC):%y%m%d}-{db.scalar(select(func.count()).select_from(Shipment)) + 1:04d}", **body.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).order_by(Vehicle.id.desc())).all())


@app.post("/vehicles", response_model=VehicleOut, status_code=201)
def create_vehicle(body: VehicleIn, user: Annotated[User, Depends(require_roles("admin", "fleet_manager"))], db: Db) -> Vehicle:
    item = Vehicle(**body.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.get("/drivers", response_model=list[DriverOut])
def list_drivers(user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> list[Driver]:
    return list(db.scalars(select(Driver).order_by(Driver.id.desc())).all())


@app.post("/drivers", response_model=DriverOut, status_code=201)
def create_driver(body: DriverIn, user: Annotated[User, Depends(require_roles("admin", "fleet_manager"))], db: Db) -> Driver:
    item = Driver(**body.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.get("/trips", response_model=list[TripOut])
def list_trips(user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> list[Trip]:
    return list(db.scalars(select(Trip).order_by(Trip.id.desc())).all())


@app.post("/trips", response_model=TripOut, status_code=201)
def create_trip(body: TripIn, user: Annotated[User, Depends(require_roles("admin", "logistics_manager"))], db: Db) -> Trip:
    shipment = db.get(Shipment, body.shipment_id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if shipment.status == "delivered":
        raise HTTPException(status_code=409, detail="A delivered shipment cannot be scheduled again")
    active_trip = db.scalar(select(Trip).where(Trip.shipment_id == body.shipment_id, Trip.status.not_in(["delivered", "cancelled"])))
    if active_trip:
        raise HTTPException(status_code=409, detail="This shipment already has an active trip")
    item = Trip(shipment_id=body.shipment_id)
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.post("/trips/{trip_id}/assign", response_model=TripOut)
def assign_trip(trip_id: int, body: AssignIn, user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> Trip:
    trip, vehicle, driver = db.get(Trip, trip_id), db.get(Vehicle, body.vehicle_id), db.get(Driver, body.driver_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    if vehicle is None or driver is None:
        raise HTTPException(status_code=404, detail="Vehicle or driver not found")
    if vehicle.status != "available" or driver.status != "available":
        raise HTTPException(status_code=409, detail="Vehicle and driver must both be available")
    vehicle.status, driver.status = "assigned", "assigned"
    trip.vehicle_id, trip.driver_id, trip.status = vehicle.id, driver.id, "assigned"
    db.get(Shipment, trip.shipment_id).status = "assigned"
    db.commit(); db.refresh(trip)
    return trip


@app.patch("/trips/{trip_id}/status", response_model=TripOut)
def update_trip_status(trip_id: int, body: TripStatusIn, user: CurrentUser, db: Db) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    if user.role not in {"admin", "logistics_manager", "fleet_manager"}:
        raise HTTPException(status_code=403, detail="Your role cannot update this trip")
    allowed_transitions = {
        "scheduled": {"cancelled"},
        "assigned": {"in_transit", "cancelled"},
        "in_transit": {"delivered", "cancelled"},
        "delivered": set(),
        "cancelled": set(),
    }
    if body.status not in allowed_transitions[trip.status]:
        raise HTTPException(status_code=409, detail=f"Cannot move a {trip.status} trip to {body.status}")
    if body.status in {"in_transit", "delivered"} and not trip.vehicle_id:
        raise HTTPException(status_code=409, detail="Assign a vehicle and driver before starting this trip")
    trip.status = body.status
    shipment = db.get(Shipment, trip.shipment_id)
    shipment.status = "delivered" if body.status == "delivered" else body.status
    if body.status in {"delivered", "cancelled"}:
        if trip.vehicle_id and (vehicle := db.get(Vehicle, trip.vehicle_id)):
            vehicle.status = "available"
        if trip.driver_id and (driver := db.get(Driver, trip.driver_id)):
            driver.status = "available"
    db.commit(); db.refresh(trip)
    return trip


@app.get("/maintenance", response_model=list[MaintenanceOut])
def list_maintenance(user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> list[Maintenance]:
    return list(db.scalars(select(Maintenance).order_by(Maintenance.id.desc())).all())


@app.post("/maintenance", response_model=MaintenanceOut, status_code=201)
def create_maintenance(body: MaintenanceIn, user: Annotated[User, Depends(require_roles("admin", "fleet_manager"))], db: Db) -> Maintenance:
    vehicle = db.get(Vehicle, body.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle.status != "available":
        raise HTTPException(status_code=409, detail="Vehicle must be available before recording maintenance")
    item = Maintenance(**body.model_dump())
    if item.status != "completed":
        vehicle.status = "maintenance"
    db.add(item); db.commit(); db.refresh(item)
    return item


@app.patch("/maintenance/{maintenance_id}/complete", response_model=MaintenanceOut)
def complete_maintenance(maintenance_id: int, user: Annotated[User, Depends(require_roles("admin", "fleet_manager"))], db: Db) -> Maintenance:
    item = db.get(Maintenance, maintenance_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    item.status = "completed"
    vehicle = db.get(Vehicle, item.vehicle_id)
    if vehicle and vehicle.status == "maintenance":
        vehicle.status = "available"
    db.commit(); db.refresh(item)
    return item


@app.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> list[Expense]:
    return list(db.scalars(select(Expense).order_by(Expense.id.desc())).all())


@app.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(body: ExpenseIn, user: Annotated[User, Depends(require_roles("admin", "logistics_manager", "fleet_manager"))], db: Db) -> Expense:
    item = Expense(**body.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item
