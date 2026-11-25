"""Business-calendar generation, independent of UI, filesystem and forecasting."""

from datetime import date
import hashlib
import json
import numpy as np
import pandas as pd
from .specs import CalendarSpec, MonthlyEventSpec, MonthBoundarySpec
from .rules import CalendarContext, MonthlyEventRule, MonthBoundaryRule, BusinessOffsetsRule
from .artifact import CalendarArtifact

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def holiday_dates(values, date_col="date"):
    if values is None:
        raise ValueError("Pass holidays explicitly; [] means deliberately no holidays")
    if isinstance(values, pd.DataFrame):
        if date_col not in values:
            raise ValueError("Holiday date column missing: " + date_col)
        values = values[date_col]
    parsed = []
    for value in values:
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp) or timestamp.tzinfo is not None or timestamp != timestamp.normalize():
            raise ValueError("Holidays must be non-null local dates without time or timezone")
        parsed.append(timestamp.date().isoformat())
    if len(set(parsed)) != len(parsed):
        raise ValueError("Duplicate holidays")
    return sorted(parsed)


class CalendarStudio:
    def __init__(self, spec=None, *, rules=()):
        self.spec = CalendarSpec.model_validate(spec or {})
        self.custom_rules = tuple(rules)
        if self.spec.profile != "generic" and self.custom_rules:
            raise ValueError("Custom rules require generic profile")

    @classmethod
    def from_profile(cls, profile, **kwargs):
        if profile != "mac_legacy_v1":
            raise ValueError("Unknown profile: " + profile)
        return cls(CalendarSpec(profile=profile, date_col="fecha", **kwargs))

    def generate(self, *, start, end, holidays, holiday_date_col="date"):
        start = date.fromisoformat(str(start))
        end = date.fromisoformat(str(end))
        if start > end:
            raise ValueError("start must not exceed end")
        if start.year < 2 or end.year > 9997:
            raise ValueError("Supported calendar years: 2 through 9997")
        holidays = holiday_dates(holidays, holiday_date_col)
        spec = self.spec
        custom = [r.describe() for r in self.custom_rules]
        # Descriptions must be reproducible JSON, not executable import paths.
        json.dumps(custom, sort_keys=True, allow_nan=False)
        if spec.profile == "mac_legacy_v1":
            from . import _legacy

            work = _legacy.run_recalculation_pipeline(
                _legacy.build_base_calendar(start.year, end.year), holidays_path=tuple(holidays)
            )
            output = _legacy.to_required_output_layout(work)
            selected = output.fecha.between(start.isoformat(), end.isoformat())
            output = output.loc[selected].reset_index(drop=True)
            business = output.loc[
                (output["fin de semana"] == 0) & (output["día festivo"] == 0), "fecha"
            ].tolist()
            output = output.rename(columns={"fecha": spec.date_col})
        else:
            lo = max(2, start.year - spec.context_years)
            hi = min(9997, end.year + spec.context_years)
            dates = pd.date_range(f"{lo}-01-01", f"{hi}-12-31", freq="D")
            business_mask = np.isin(dates.weekday, [DAYS.index(x) for x in spec.weekmask]) & ~np.isin(
                dates.strftime("%Y-%m-%d"), holidays
            )
            selected = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
            rules = [
                MonthlyEventRule(r)
                if isinstance(r, MonthlyEventSpec)
                else MonthBoundaryRule(r)
                if isinstance(r, MonthBoundarySpec)
                else BusinessOffsetsRule(r)
                for r in spec.rules
            ] + list(self.custom_rules)
            margin = max([31, *[max(getattr(r, "before", 0), getattr(r, "after", 0)) for r in spec.rules]])
            if rules and (
                sum(business_mask & (dates < pd.Timestamp(start))) < margin
                or sum(business_mask & (dates > pd.Timestamp(end))) < margin
            ):
                raise ValueError(
                    "Insufficient business-day context: extend context_years or review holiday closure"
                )
            frame = pd.DataFrame(
                {
                    "is_weekend": (dates.weekday >= 5).astype("uint8"),
                    "is_holiday": np.isin(dates.strftime("%Y-%m-%d"), holidays).astype("uint8"),
                    "is_business_day": business_mask.astype("uint8"),
                }
            )
            for day in range(1, 32):
                frame[f"day_{day:02d}"] = (dates.day == day).astype("uint8")
            for day in range(7):
                frame[f"weekday_{day}"] = (dates.weekday == day).astype("uint8")
            for month in range(1, 13):
                frame[f"month_{month:02d}"] = (dates.month == month).astype("uint8")
            pending = list(rules)
            while pending:
                ready = next((r for r in pending if set(r.requires) <= set(frame.columns)), None)
                if ready is None:
                    raise ValueError("Missing or cyclic rule dependencies")
                names = list(ready.outputs)
                if len(set(names)) != len(names) or set(names) & set(frame.columns) | set(names) & {
                    spec.date_col
                }:
                    raise ValueError("Rule output names collide")
                block = ready.apply(CalendarContext(dates, business_mask, frame))
                if list(block.columns) != names or not block.index.equals(frame.index):
                    raise ValueError("Rule output alignment/schema mismatch")
                if block.isna().any().any() or not block.isin([0, 1]).all().all():
                    raise ValueError("Rule outputs must be binary and non-null")
                frame = pd.concat([frame, block], axis=1)
                pending.remove(ready)
            if spec.date_col in frame.columns:
                raise ValueError("date_col collides with a feature")
            output = frame.loc[selected].reset_index(drop=True)
            output.insert(0, spec.date_col, dates[selected].strftime("%Y-%m-%d"))
            business = dates[selected & business_mask].strftime("%Y-%m-%d").tolist()
        metadata = dict(
            spec=spec.model_dump(mode="json"),
            holidays=holidays,
            custom_rules=custom,
            start=start.isoformat(),
            end=end.isoformat(),
            axis="daily",
            business_dates=business,
            holidays_sha256=hashlib.sha256(json.dumps(holidays).encode()).hexdigest(),
        )
        artifact = CalendarArtifact(output, metadata)
        artifact.validate().raise_for_errors()
        return artifact
