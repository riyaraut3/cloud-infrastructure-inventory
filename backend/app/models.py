from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Part(Base):
    __tablename__ = "parts"
    __table_args__ = (UniqueConstraint("sku", "site", name="uq_part_sku_site"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    site: Mapped[str] = mapped_column(String(100), index=True)
    supplier: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[int] = mapped_column(Integer)
    reorder_level: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ImportRecord(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    object_key: Mapped[str] = mapped_column(String(300))
    filename: Mapped[str] = mapped_column(String(200))
    row_count: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
