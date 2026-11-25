"""Validated, serializable calendar configuration; no implicit file discovery."""

from typing import Annotated, Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Weekday = Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class StrictSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MonthlyEventSpec(StrictSpec):
    type: Literal["monthly_event"] = "monthly_event"
    name: str = Field(min_length=1)
    days: list[int] = Field(min_length=1)
    missing_day: Literal["month_end", "skip", "raise"] = "month_end"
    adjustment: Literal["preceding", "following", "none"] = "none"

    @field_validator("days")
    @classmethod
    def valid_days(cls, value):
        if len(set(value)) != len(value) or any(not 1 <= d <= 31 for d in value):
            raise ValueError("days must be unique integers between 1 and 31")
        return value


class MonthBoundarySpec(StrictSpec):
    type: Literal["month_boundary"] = "month_boundary"
    name: str = Field(min_length=1)
    edge: Literal["first", "last"]


class BusinessOffsetsSpec(StrictSpec):
    type: Literal["business_offsets"] = "business_offsets"
    events: list[str] = Field(min_length=1)
    before: int = Field(default=10, ge=0, le=366)
    after: int = Field(default=10, ge=0, le=366)

    @field_validator("events")
    @classmethod
    def unique_events(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("events must be unique")
        return values


RuleSpec = Annotated[MonthlyEventSpec | MonthBoundarySpec | BusinessOffsetsSpec, Field(discriminator="type")]


class CalendarSpec(StrictSpec):
    name: str = Field(default="calendar", min_length=1)
    profile: Literal["generic", "mac_legacy_v1"] = "generic"
    timezone: str = "UTC"
    date_col: str = Field(default="date", min_length=1)
    weekmask: list[Weekday] = Field(default_factory=lambda: ["Mon", "Tue", "Wed", "Thu", "Fri"])
    rules: list[RuleSpec] = Field(default_factory=list)
    context_years: int = Field(default=2, ge=1, le=10)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (KeyError, ValueError) as exc:
            raise ValueError("Unknown timezone: " + value) from exc
        return value

    @field_validator("weekmask")
    @classmethod
    def valid_weekmask(cls, value):
        if not value or len(set(value)) != len(value):
            raise ValueError("weekmask must be nonempty and unique")
        return value

    @model_validator(mode="after")
    def profile_contract(self):
        if self.profile == "mac_legacy_v1" and (
            self.rules or self.weekmask != ["Mon", "Tue", "Wed", "Thu", "Fri"]
        ):
            raise ValueError("mac_legacy_v1 has fixed rules and weekmask; use generic for custom rules")
        return self
