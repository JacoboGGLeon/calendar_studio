"""Polymorphic rules producing aligned binary feature columns."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import calendar as standard_calendar
import numpy as np
import pandas as pd
from .specs import MonthlyEventSpec, MonthBoundarySpec


@dataclass
class CalendarContext:
    dates: pd.DatetimeIndex
    business: np.ndarray
    features: pd.DataFrame


class CalendarRule(ABC):
    requires: tuple[str, ...] = ()

    @property
    @abstractmethod
    def outputs(self) -> tuple[str, ...]: ...
    @abstractmethod
    def apply(self, context: CalendarContext) -> pd.DataFrame: ...
    @abstractmethod
    def describe(self) -> dict: ...


class MonthlyEventRule(CalendarRule):
    def __init__(self, spec: MonthlyEventSpec):
        self.spec = spec

    @property
    def outputs(self):
        return (self.spec.name,)

    def describe(self):
        return self.spec.model_dump(mode="json")

    def apply(self, context):
        values = np.zeros(len(context.dates), dtype=np.uint8)
        business = context.dates[context.business]
        for month in context.dates.to_period("M").unique():
            year, m = month.year, month.month
            last = standard_calendar.monthrange(year, m)[1]
            for day in self.spec.days:
                if day > last:
                    if self.spec.missing_day == "skip":
                        continue
                    if self.spec.missing_day == "raise":
                        raise ValueError(f"Day {day} absent in {month}")
                    day = last
                target = pd.Timestamp(year=year, month=m, day=day)
                if self.spec.adjustment == "preceding":
                    i = business.searchsorted(target, side="right") - 1
                    if i < 0:
                        continue  # Outside the padded context, never the requested range.
                    target = business[i]
                elif self.spec.adjustment == "following":
                    i = business.searchsorted(target, side="left")
                    if i >= len(business):
                        continue
                    target = business[i]
                pos = context.dates.get_indexer([target])[0]
                if pos >= 0:
                    values[pos] = 1
        return pd.DataFrame({self.spec.name: values}, index=context.features.index)


class MonthBoundaryRule(CalendarRule):
    def __init__(self, spec: MonthBoundarySpec):
        self.spec = spec

    @property
    def outputs(self):
        return (self.spec.name,)

    def describe(self):
        return self.spec.model_dump(mode="json")

    def apply(self, context):
        values = np.zeros(len(context.dates), dtype=np.uint8)
        positions = np.flatnonzero(context.business)
        groups = pd.Series(positions, index=context.dates[positions].to_period("M"))
        chosen = (
            groups.groupby(level=0).first() if self.spec.edge == "first" else groups.groupby(level=0).last()
        )
        values[chosen.to_numpy()] = 1
        return pd.DataFrame({self.spec.name: values}, index=context.features.index)


class BusinessOffsetsRule(CalendarRule):
    def __init__(self, spec):
        self.spec = spec
        self.requires = tuple(spec.events)

    @property
    def outputs(self):
        return tuple(
            f"{event}__{direction}_{k}"
            for event in self.spec.events
            for direction, count in [("before", self.spec.before), ("after", self.spec.after)]
            for k in range(1, count + 1)
        )

    def describe(self):
        return self.spec.model_dump(mode="json")

    def apply(self, context):
        positions = np.flatnonzero(context.business)
        result = {}
        for event in self.spec.events:
            event_positions = np.flatnonzero(context.features[event].to_numpy())
            for direction, count in [("before", self.spec.before), ("after", self.spec.after)]:
                for k in range(1, count + 1):
                    values = np.zeros(len(context.dates), dtype=np.uint8)
                    indices = (
                        np.searchsorted(positions, event_positions, side="left") - k
                        if direction == "before"
                        else np.searchsorted(positions, event_positions, side="right") + k - 1
                    )
                    valid = indices[(indices >= 0) & (indices < len(positions))]
                    values[positions[valid]] = 1
                    result[f"{event}__{direction}_{k}"] = values
        return pd.DataFrame(result, index=context.features.index)
