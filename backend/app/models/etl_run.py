from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class EtlRunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class EtlRun(BaseModel):
    __tablename__ = "etl_runs"

    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[EtlRunStatus] = mapped_column(
        ENUM(
            EtlRunStatus,
            name="etl_run_status",
            schema="keystone",
            create_type=False,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )
    rows_seen: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows_inserted: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows_updated: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rows_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)