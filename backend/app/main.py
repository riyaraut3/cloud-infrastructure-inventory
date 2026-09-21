"""Inventory API with strict imports, paged queries, and site-level reporting."""
from contextlib import asynccontextmanager
from decimal import Decimal
import csv
import hashlib
from io import StringIO
import os
import secrets

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
try:
    from mangum import Mangum
except ImportError:  # Optional only for standalone local test environments.
    Mangum = None
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import create_schema, session_dependency
from .models import ImportRecord, Part
from .service import ImportValidationError, MAX_BYTES, parse_inventory
from .storage import save_source


def authenticate(x_api_key: str | None = Header(default=None)):
    # For AWS deployment, API Gateway's JWT authorizer rejects unauthenticated
    # requests before invoking Lambda; Lambda is not exposed via a function URL.
    if os.getenv("AUTH_MODE") == "apigw_jwt":
        if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            raise HTTPException(500, "apigw_jwt requires an AWS Lambda/API Gateway deployment")
        return
    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(500, "API_KEY is not configured")
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(401, "Invalid API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lightweight demo bootstrap. Production applications should run migrations
    # out-of-band; see docs/operations.md.
    create_schema()
    yield


app = FastAPI(title="Infrastructure Inventory API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Authorization", "Content-Type"],
)
api = Depends(authenticate)


@app.get("/api/health")
def health():
    return {"status": "ok"}


def as_part(item: Part):
    return {
        "id": item.id,
        "sku": item.sku,
        "name": item.name,
        "site": item.site,
        "supplier": item.supplier,
        "quantity": item.quantity,
        "reorder_level": item.reorder_level,
        "unit_cost": str(item.unit_cost),
        "inventory_value": str(item.unit_cost * item.quantity),
        "low_stock": item.quantity <= item.reorder_level,
        "updated_at": item.updated_at.isoformat(),
    }


@app.post("/api/inventory/imports", dependencies=[api], status_code=201)
async def upload_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(session_dependency),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(415, "Upload a .csv inventory file")
    data = await file.read(MAX_BYTES + 1)
    try:
        rows = parse_inventory(data)
    except ImportValidationError as exc:
        raise HTTPException(422, str(exc)) from exc

    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(ImportRecord).where(ImportRecord.sha256 == digest))
    if existing:
        return {"id": existing.id, "rows": existing.row_count, "created": 0, "updated": 0, "duplicate": True}

    # Validate entire CSV before persisting any row or original file.
    key = f"imports/{digest}.csv"
    try:
        save_source(data, key)
    except Exception as exc:
        raise HTTPException(503, "Could not store original upload") from exc
    created, updated = 0, 0
    try:
        for row in rows:
            part = db.scalar(select(Part).where(Part.sku == row["sku"], Part.site == row["site"]))
            if part is None:
                db.add(Part(**row))
                created += 1
            else:
                for key_name, value in row.items():
                    setattr(part, key_name, value)
                updated += 1
        record = ImportRecord(
            sha256=digest,
            object_key=key,
            filename=file.filename[:200],
            row_count=len(rows),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Concurrent import conflict; retry request") from exc
    except Exception:
        db.rollback()
        raise
    return {"id": record.id, "rows": len(rows), "created": created, "updated": updated, "duplicate": False}


@app.get("/api/parts", dependencies=[api])
def list_parts(
    q: str | None = Query(default=None, max_length=100),
    site: str | None = Query(default=None, max_length=100),
    low_stock: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(session_dependency),
):
    filters = []
    if q:
        # SQLAlchemy parameterizes the value; escaping treats % and _ as literal user input.
        safe = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(Part.sku.ilike(f"%{safe}%", escape="\\"))
    if site:
        filters.append(Part.site == site)
    if low_stock:
        filters.append(Part.quantity <= Part.reorder_level)
    total = db.scalar(select(func.count(Part.id)).where(*filters)) or 0
    parts = db.scalars(select(Part).where(*filters).order_by(Part.site, Part.sku).offset(offset).limit(limit)).all()
    return {"total": total, "limit": limit, "offset": offset, "items": [as_part(p) for p in parts]}


@app.get("/api/reports/summary", dependencies=[api])
def summary(db: Session = Depends(session_dependency)):
    parts = db.scalars(select(Part)).all()
    sites: dict[str, dict] = {}
    for part in parts:
        site = sites.setdefault(part.site, {"site": part.site, "sku_count": 0, "units": 0, "low_stock_count": 0, "value": Decimal("0")})
        site["sku_count"] += 1
        site["units"] += part.quantity
        site["low_stock_count"] += int(part.quantity <= part.reorder_level)
        site["value"] += part.quantity * part.unit_cost
    grouped = [{**s, "value": str(s["value"].quantize(Decimal("0.01")))} for s in sorted(sites.values(), key=lambda x: x["site"])]
    return {
        "total_skus": sum(s["sku_count"] for s in grouped),
        "total_units": sum(s["units"] for s in grouped),
        "low_stock_count": sum(s["low_stock_count"] for s in grouped),
        "total_value": str(sum((Decimal(s["value"]) for s in grouped), Decimal("0")).quantize(Decimal("0.01"))),
        "by_site": grouped,
    }


@app.get("/api/reports/low-stock.csv", dependencies=[api])
def low_stock_csv(db: Session = Depends(session_dependency)):
    rows = db.scalars(select(Part).where(Part.quantity <= Part.reorder_level).order_by(Part.site, Part.sku)).all()
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(["sku", "name", "site", "supplier", "quantity", "reorder_level", "unit_cost"])
    for part in rows:
        # Spreadsheet formula injection protection for user-controlled text fields.
        def safe(value):
            s = str(value)
            return "'" + s if s.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else s
        writer.writerow([safe(part.sku), safe(part.name), safe(part.site), safe(part.supplier), part.quantity, part.reorder_level, str(part.unit_cost)])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="low-stock.csv"'})


# Lambda handler. Adapter is imported only, not executed, during local uvicorn use.
handler = Mangum(app, lifespan="auto") if Mangum else None
