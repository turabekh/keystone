from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID

from app.models.base import BaseModel


class County(BaseModel):
    __tablename__ = "counties"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    fips_code: Mapped[str | None] = mapped_column(String(5), nullable=True)

    filing_office_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filing_office_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    filing_office_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    year_settings: Mapped[list["CountyYearSetting"]] = relationship(
            back_populates="county",
            cascade="all, delete-orphan",
        )

    properties: Mapped[list["Property"]] = relationship(back_populates="county")

    __table_args__ = (
        UniqueConstraint("state", "slug", name="uq_counties_state_slug"),
        CheckConstraint("state = upper(state)", name="ck_counties_state_uppercase"),
        CheckConstraint("length(state) = 2", name="ck_counties_state_length"),
        Index("ix_counties_state", "state"),
    )


class CountyYearSetting(BaseModel):
    __tablename__ = "county_year_settings"

    county_id: Mapped[UUID] = mapped_column(
        ForeignKey("counties.id", ondelete="CASCADE"),
        nullable=False,
    )
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    clr_factor: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    par: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    appeal_deadline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_reassessment_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    county: Mapped["County"] = relationship(back_populates="year_settings")

    __table_args__ = (
        UniqueConstraint("county_id", "tax_year", name="uq_county_year_settings_county_id_tax_year"),
        CheckConstraint("tax_year >= 2000 AND tax_year <= 2100", name="ck_county_year_settings_tax_year_range"),
        CheckConstraint("clr_factor IS NULL OR clr_factor > 0", name="ck_county_year_settings_clr_positive"),
        Index("ix_county_year_settings_county_id_tax_year", "county_id", "tax_year"),
    )