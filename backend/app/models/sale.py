from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Sale(BaseModel):
    __tablename__ = "sales"

    property_id: Mapped[UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    sale_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deed_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grantor: Mapped[str | None] = mapped_column(String(500), nullable=True)
    grantee: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_arms_length: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    property: Mapped["Property"] = relationship(back_populates="sales")

    __table_args__ = (
        CheckConstraint("sale_price >= 0", name="ck_sales_price_nonnegative"),
    )