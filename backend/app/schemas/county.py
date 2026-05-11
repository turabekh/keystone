from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CountyYearSettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tax_year: int
    clr_factor: float | None
    par: float | None
    appeal_deadline: str | None
    last_reassessment_year: int | None
    notes: str | None


class CountyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    state: str
    slug: str
    fips_code: str | None
    filing_office_name: str | None
    filing_office_address: str | None
    filing_office_phone: str | None


class CountyWithSettings(CountyRead):
    year_settings: list[CountyYearSettingRead]