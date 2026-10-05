from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'fulfillment.db'}")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(String, nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    courier: Mapped[str] = mapped_column(String, nullable=False)
    tracking: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")
    events: Mapped[list[Event]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    variant: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    picked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    order: Mapped[Order] = relationship(back_populates="items")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("sku", "warehouse"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    variant: Mapped[str] = mapped_column(String, nullable=False)
    warehouse: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String, default="—", nullable=False)


class Transfer(Base):
    __tablename__ = "transfers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, default="Secondary", nullable=False)
    destination: Mapped[str] = mapped_column(String, default="Main", nullable=False)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="REQUESTED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    received_at: Mapped[datetime | None] = mapped_column(DateTime)


class Issue(Base):
    __tablename__ = "exceptions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    order: Mapped[Order] = relationship(back_populates="events")


class ItemIn(BaseModel):
    sku: str
    quantity: int = Field(gt=0, le=1000)


class OrderIn(BaseModel):
    customer: str = Field(min_length=1, max_length=120)
    channel: Literal["Amazon", "Flipkart", "Website"]
    priority: Literal["NORMAL", "HIGH", "URGENT"] = "NORMAL"
    deadline: datetime
    courier: Literal["BlueDart", "Delhivery", "DTDC"]
    items: list[ItemIn] = Field(min_length=1)


class TransferIn(BaseModel):
    sku: str
    quantity: int = Field(gt=0, le=1000)
    order_id: str | None = None


class PickIn(BaseModel):
    sku: str
    variant: str
    quantity: int = Field(gt=0)


class StageIn(BaseModel):
    location: str = Field(min_length=1, max_length=30)


class IssueIn(BaseModel):
    order_id: str | None = None
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    owner: str = Field(min_length=1, max_length=100)


app = FastAPI(title="Fulfillment Hub API", version="1.0.0", description="Order fulfillment workflow API for the XYZ demo.")
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
allowed_origins.extend(origin.strip().rstrip("/") for origin in os.getenv("FRONTEND_ORIGINS", "").split(",") if origin.strip())
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_methods=["*"], allow_headers=["*"])


def session_dep():
    with SessionLocal() as session:
        yield session


def now():
    return datetime.now()


def event(db: Session, order: Order, action: str, detail: str):
    db.add(Event(order_id=order.id, action=action, detail=detail))


def inventory_row(db: Session, sku: str, warehouse: str = "Main") -> Inventory | None:
    return db.scalar(select(Inventory).where(Inventory.sku == sku, Inventory.warehouse == warehouse))


def order_dict(o: Order, include_events=False):
    stage_location = next((e.detail.split(" at ", 1)[1] for e in reversed(o.events) if e.action == "STAGED" and " at " in e.detail), None)
    data = {"id": o.id, "customer": o.customer, "channel": o.channel, "priority": o.priority,
            "deadline": o.deadline.isoformat(), "status": o.status, "courier": o.courier,
            "tracking": o.tracking, "created_at": o.created_at.isoformat(),
            "items": [{"sku": i.sku, "name": i.name, "variant": i.variant, "quantity": i.quantity, "picked": i.picked} for i in o.items],
            "exception": None, "stage": stage_location,
            "package": f"PKG-{o.id[-4:]}" if o.status in {"PACKED", "STAGED", "SHIPPED"} else None}
    if include_events:
        data["events"] = [{"action": e.action, "detail": e.detail, "created_at": e.created_at.isoformat()} for e in sorted(o.events, key=lambda e: e.created_at)]
    return data


def issue_dict(x: Issue):
    return {"id": x.id, "order_id": x.order_id, "title": x.title, "description": x.description,
            "owner": x.owner, "status": x.status, "created_at": x.created_at.isoformat(),
            "resolved_at": x.resolved_at.isoformat() if x.resolved_at else None}


def transfer_dict(t: Transfer):
    return {"id": t.id, "sku": t.sku, "product": inventory_row_name(t.sku), "quantity": t.quantity,
            "source": t.source, "destination": t.destination, "order_id": t.order_id,
            "status": t.status, "created_at": t.created_at.isoformat(),
            "received_at": t.received_at.isoformat() if t.received_at else None}


def inventory_row_name(sku: str):
    with SessionLocal() as db:
        row = db.scalar(select(Inventory).where(Inventory.sku == sku))
        return row.name if row else sku


def next_id(db: Session, model, prefix: str, start: int):
    existing = db.scalars(select(model.id)).all()
    numbers = [int(v.split("-")[-1]) for v in existing if v.startswith(prefix + "-") and v.split("-")[-1].isdigit()]
    return f"{prefix}-{max(numbers, default=start - 1) + 1}"


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(Order.id).limit(1)):
            return
        today = now().replace(hour=0, minute=0, second=0, microsecond=0)
        products = [
            ("WM-101", "Wireless Mouse", "Graphite", 14, 8, "A-03-B-02"),
            ("KB-205", "Mechanical Keyboard", "Brown switch", 1, 12, "B-01-A-03"),
            ("HP-301", "Studio Headphones", "Midnight", 5, 4, "A-02-C-01"),
            ("BT-440", "Bluetooth Speaker", "Stone", 9, 6, "C-04-A-02"),
            ("CB-115", "USB-C Hub", "7-in-1", 21, 10, "A-01-B-04"),
        ]
        product_map = {}
        for sku, name, variant, main, secondary, location in products:
            product_map[sku] = (name, variant)
            db.add_all([Inventory(sku=sku, name=name, variant=variant, warehouse="Main", quantity=main, location=location),
                        Inventory(sku=sku, name=name, variant=variant, warehouse="Secondary", quantity=secondary, location="Overflow")])
        records = [
            ("ORD-2084", "Ananya Mehta", "Amazon", "URGENT", 13, 30, "READY_TO_PICK", "BlueDart", [("WM-101", 2), ("KB-205", 1)]),
            ("ORD-2083", "Rohan Iyer", "Website", "HIGH", 15, 0, "PICKING", "Delhivery", [("HP-301", 1)]),
            ("ORD-2082", "Priya Nair", "Flipkart", "URGENT", 14, 0, "AWAITING_STOCK", "BlueDart", [("KB-205", 3)]),
            ("ORD-2081", "Kabir Shah", "Amazon", "NORMAL", 17, 0, "PACKED", "DTDC", [("BT-440", 1)]),
            ("ORD-2080", "Meera Joshi", "Website", "HIGH", 16, 0, "STAGED", "Delhivery", [("WM-101", 1)]),
            ("ORD-2079", "Arjun Rao", "Amazon", "NORMAL", 18, 0, "SHIPPED", "DTDC", [("CB-115", 1)]),
            ("ORD-2078", "Sara Thomas", "Flipkart", "NORMAL", 18, 0, "READY_TO_PICK", "DTDC", [("BT-440", 2)]),
            ("ORD-2077", "Dev Malhotra", "Website", "HIGH", 15, 30, "EXCEPTION", "BlueDart", [("HP-301", 2)]),
        ]
        for idx, (oid, customer, channel, priority, hour, minute, status, courier, lines) in enumerate(records):
            o = Order(id=oid, customer=customer, channel=channel, priority=priority,
                      deadline=today.replace(hour=hour, minute=minute), status=status, courier=courier,
                      tracking=f"{courier[:2].upper()}{702184900+idx}", created_at=now()-timedelta(minutes=idx*9))
            for sku, qty in lines:
                name, variant = product_map[sku]
                o.items.append(OrderItem(sku=sku, name=name, variant=variant, quantity=qty,
                                         picked=qty if status in {"PACKED", "STAGED", "SHIPPED"} else 0))
            db.add(o)
        db.flush()
        db.add_all([
            Issue(id="EX-042", order_id="ORD-2082", title="Stock shortage", description="Keyboard short by 2 units in Main. Secondary has stock available.", owner="Warehouse · Neel", status="OPEN"),
            Issue(id="EX-041", order_id="ORD-2077", title="Shelf count mismatch", description="Headphones not found at A-02-C-01. Order is blocked pending recount.", owner="Warehouse · Neel", status="OPEN"),
            Issue(id="EX-040", order_id=None, title="Courier missed pickup", description="Package remained in staging after the 08:30 pickup.", owner="Office · Kavya", status="RESOLVED", resolved_at=now()),
        ])
        for o in db.scalars(select(Order)).all():
            event(db, o, "ORDER_RECEIVED", f"Order received from {o.channel}")
            if o.status not in {"RECEIVED", "EXCEPTION", "AWAITING_STOCK"}:
                event(db, o, o.status, f"Sample order currently {o.status.lower().replace('_', ' ')}")
        db.commit()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fulfillment-hub"}


@app.get("/api/overview")
def overview(db: Session = Depends(session_dep)):
    orders = db.scalars(select(Order)).all()
    exceptions = db.scalars(select(Issue).where(Issue.status == "OPEN")).all()
    states = ["READY_TO_PICK", "PICKING", "AWAITING_STOCK", "PACKED", "STAGED"]
    queue = sorted([o for o in orders if o.status not in {"SHIPPED", "DELIVERED", "CANCELLED"}], key=lambda o: (o.deadline, 0 if o.priority == "URGENT" else 1))[:6]
    return {"open_orders": sum(o.status not in {"SHIPPED", "DELIVERED", "CANCELLED"} for o in orders),
            "orders_today": len(orders), "urgent": sum(o.priority == "URGENT" and o.status not in {"SHIPPED", "DELIVERED"} for o in orders),
            "packed_staged": sum(o.status in {"PACKED", "STAGED"} for o in orders), "open_exceptions": len(exceptions),
            "stages": {s: sum(o.status == s for o in orders) for s in states},
            "queue": [order_dict(o) for o in queue], "exceptions": [issue_dict(x) for x in exceptions]}


@app.get("/api/orders")
def list_orders(status: str | None = None, priority: str | None = None, q: str | None = None, db: Session = Depends(session_dep)):
    rows = db.scalars(select(Order).order_by(Order.deadline)).all()
    if status:
        rows = [o for o in rows if o.status == status]
    if priority:
        rows = [o for o in rows if o.priority == priority]
    if q:
        term = q.lower()
        rows = [o for o in rows if term in f"{o.id} {o.customer} {o.channel} {o.courier}".lower()]
    return [order_dict(o) for o in rows]


@app.get("/api/orders/{order_id}")
def order_detail(order_id: str, db: Session = Depends(session_dep)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    data = order_dict(o, True)
    data["stage"] = next((e.detail.split(" at ", 1)[1] for e in reversed(o.events) if e.action == "STAGED" and " at " in e.detail), None)
    data["package"] = f"PKG-{o.id[-4:]}" if o.status in {"PACKED", "STAGED", "SHIPPED"} else None
    return data


@app.post("/api/orders", status_code=201)
def create_order(payload: OrderIn, db: Session = Depends(session_dep)):
    lines = []
    for item in payload.items:
        inv = inventory_row(db, item.sku)
        if not inv:
            raise HTTPException(422, f"Unknown SKU {item.sku}")
        lines.append((item, inv))
    shortage = any(inv.quantity < item.quantity for item, inv in lines)
    secondary_sufficient = all((inventory_row(db, item.sku, "Secondary") or Inventory(quantity=0)).quantity + inv.quantity >= item.quantity for item, inv in lines)
    status = "AWAITING_STOCK" if shortage and secondary_sufficient else "EXCEPTION" if shortage else "READY_TO_PICK"
    oid = next_id(db, Order, "ORD", 2085)
    courier_prefix = {"BlueDart": "BD", "Delhivery": "DL", "DTDC": "DT"}[payload.courier]
    o = Order(id=oid, customer=payload.customer, channel=payload.channel, priority=payload.priority,
              deadline=payload.deadline, status=status, courier=payload.courier,
              tracking=f"{courier_prefix}{int(now().timestamp()) % 1000000000:09d}")
    for item, inv in lines:
        o.items.append(OrderItem(sku=item.sku, name=inv.name, variant=inv.variant, quantity=item.quantity))
    db.add(o)
    event(db, o, "ORDER_RECEIVED", f"Order received from {payload.channel}")
    if status in {"AWAITING_STOCK", "EXCEPTION"}:
        for item, inv in lines:
            if inv.quantity < item.quantity:
                secondary = inventory_row(db, item.sku, "Secondary")
                title = "Stock shortage" if secondary and secondary.quantity + inv.quantity >= item.quantity else "Insufficient stock"
                description = f"{item.sku} needs {item.quantity}; Main has {inv.quantity}, Secondary has {secondary.quantity if secondary else 0}."
                exid = next_id(db, Issue, "EX", 43)
                db.add(Issue(id=exid, order_id=oid, title=title, description=description, owner="Office · Kavya"))
                event(db, o, "EXCEPTION_OPENED", description)
    db.commit()
    return order_dict(o)


@app.get("/api/inventory")
def inventory(db: Session = Depends(session_dep)):
    rows = db.scalars(select(Inventory).order_by(Inventory.name, Inventory.warehouse)).all()
    products = {}
    for r in rows:
        p = products.setdefault(r.sku, {"sku": r.sku, "name": r.name, "variant": r.variant, "location": r.location, "main": 0, "secondary": 0})
        p["main" if r.warehouse == "Main" else "secondary"] = r.quantity
    return list(products.values())


@app.get("/api/transfers")
def list_transfers(db: Session = Depends(session_dep)):
    return [transfer_dict(t) for t in db.scalars(select(Transfer).order_by(Transfer.created_at.desc())).all()]


@app.post("/api/transfers", status_code=201)
def create_transfer(payload: TransferIn, db: Session = Depends(session_dep)):
    source = inventory_row(db, payload.sku, "Secondary")
    if not source:
        raise HTTPException(404, "SKU is not stocked in Secondary")
    if source.quantity < payload.quantity:
        raise HTTPException(409, f"Secondary has only {source.quantity} units")
    if payload.order_id and not db.get(Order, payload.order_id):
        raise HTTPException(404, "Order not found")
    tid = next_id(db, Transfer, "TR", 101)
    t = Transfer(id=tid, sku=payload.sku, quantity=payload.quantity, order_id=payload.order_id)
    db.add(t)
    if payload.order_id:
        o = db.get(Order, payload.order_id)
        event(db, o, "TRANSFER_REQUESTED", f"{tid}: {payload.quantity} × {payload.sku} requested from Secondary")
    db.commit()
    return transfer_dict(t)


@app.post("/api/transfers/{transfer_id}/receive")
def receive_transfer(transfer_id: str, db: Session = Depends(session_dep)):
    t = db.get(Transfer, transfer_id)
    if not t:
        raise HTTPException(404, "Transfer not found")
    if t.status != "REQUESTED":
        raise HTTPException(409, "Transfer is no longer awaiting receipt")
    source, dest = inventory_row(db, t.sku, t.source), inventory_row(db, t.sku, t.destination)
    if not source or not dest or source.quantity < t.quantity:
        raise HTTPException(409, "Source balance changed; recount before receiving")
    source.quantity -= t.quantity
    dest.quantity += t.quantity
    t.status, t.received_at = "RECEIVED", now()
    if t.order_id:
        o = db.get(Order, t.order_id)
        event(db, o, "TRANSFER_RECEIVED", f"{t.quantity} × {t.sku} received into Main")
        if o.status == "AWAITING_STOCK" and all((inventory_row(db, i.sku).quantity >= i.quantity for i in o.items)):
            o.status = "READY_TO_PICK"
            event(db, o, "READY_TO_PICK", "Main warehouse now has enough stock")
            for issue in db.scalars(select(Issue).where(Issue.order_id == o.id, Issue.status == "OPEN")):
                issue.status, issue.resolved_at = "RESOLVED", now()
    db.commit()
    return transfer_dict(t)


@app.post("/api/orders/{order_id}/pick")
def pick(order_id: str, payload: PickIn, db: Session = Depends(session_dep)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if o.status not in {"READY_TO_PICK", "PICKING"}:
        raise HTTPException(409, f"Order cannot be picked while {o.status}")
    line = next((i for i in o.items if i.sku == payload.sku), None)
    if not line:
        raise HTTPException(409, "Wrong SKU: this item is not on the order")
    if line.variant != payload.variant:
        raise HTTPException(409, f"Wrong variant: expected {line.variant}")
    if line.picked:
        raise HTTPException(409, "This order line has already been picked")
    if payload.quantity != line.quantity:
        raise HTTPException(409, f"Quantity mismatch: expected {line.quantity}")
    stock = inventory_row(db, line.sku)
    if not stock or stock.quantity < line.quantity:
        raise HTTPException(409, "Main warehouse does not have enough stock")
    stock.quantity -= line.quantity
    line.picked = line.quantity
    o.status = "PICKING"
    event(db, o, "ITEM_PICKED", f"Verified {line.sku} · {line.variant} · quantity {line.quantity}")
    if all(i.picked == i.quantity for i in o.items):
        o.status = "PICKED"
        event(db, o, "PICKED", "All order lines picked and verified")
    db.commit()
    return order_dict(o)


@app.post("/api/orders/{order_id}/pack")
def pack(order_id: str, db: Session = Depends(session_dep)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if o.status != "PICKED":
        raise HTTPException(409, "All order lines must be verified before packing")
    o.status = "PACKED"
    event(db, o, "PACKED", f"PKG-{o.id[-4:]} · label LBL-{o.id[-4:]} attached")
    db.commit()
    return order_dict(o)


@app.post("/api/orders/{order_id}/stage")
def stage(order_id: str, payload: StageIn, db: Session = Depends(session_dep)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if o.status != "PACKED":
        raise HTTPException(409, "Only packed orders can be staged")
    o.status = "STAGED"
    event(db, o, "STAGED", f"{o.id} staged at {payload.location}")
    db.commit()
    return order_detail(order_id, db)


@app.post("/api/orders/{order_id}/pickup")
def pickup(order_id: str, db: Session = Depends(session_dep)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    if o.status != "STAGED":
        raise HTTPException(409, "Order must be staged before pickup")
    o.status = "SHIPPED"
    event(db, o, "SHIPPED", f"Handed to {o.courier}; tracking {o.tracking}")
    db.commit()
    return order_dict(o)


@app.get("/api/exceptions")
def list_exceptions(status: str | None = None, db: Session = Depends(session_dep)):
    rows = db.scalars(select(Issue).order_by(Issue.created_at.desc())).all()
    return [issue_dict(x) for x in rows if not status or x.status == status]


@app.post("/api/exceptions", status_code=201)
def create_exception(payload: IssueIn, db: Session = Depends(session_dep)):
    o = db.get(Order, payload.order_id) if payload.order_id else None
    if payload.order_id and not o:
        raise HTTPException(404, "Order not found")
    xid = next_id(db, Issue, "EX", 43)
    issue = Issue(id=xid, order_id=payload.order_id, title=payload.title, description=payload.description, owner=payload.owner)
    db.add(issue)
    if o and o.status not in {"SHIPPED", "DELIVERED", "CANCELLED"}:
        o.status = "EXCEPTION"
        event(db, o, "EXCEPTION_OPENED", f"{xid}: {payload.title} · {payload.description}")
    db.commit()
    return issue_dict(issue)


@app.post("/api/exceptions/{exception_id}/resolve")
def resolve_exception(exception_id: str, db: Session = Depends(session_dep)):
    issue = db.get(Issue, exception_id)
    if not issue:
        raise HTTPException(404, "Exception not found")
    if issue.status != "OPEN":
        raise HTTPException(409, "Exception is already resolved")
    issue.status, issue.resolved_at = "RESOLVED", now()
    o = db.get(Order, issue.order_id) if issue.order_id else None
    if o and o.status == "EXCEPTION":
        enough = all((inventory_row(db, i.sku) and inventory_row(db, i.sku).quantity >= i.quantity for i in o.items))
        if enough:
            o.status = "READY_TO_PICK"
            event(db, o, "EXCEPTION_RESOLVED", f"{issue.title} resolved; order ready to pick")
        else:
            event(db, o, "EXCEPTION_RESOLVED", f"{issue.title} marked resolved; order remains blocked until stock is available")
    db.commit()
    return issue_dict(issue)
