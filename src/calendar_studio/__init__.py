"""Calendar Studio: deterministic business calendars with explicit inputs."""

from .specs import CalendarSpec, MonthlyEventSpec, MonthBoundarySpec, BusinessOffsetsSpec
from .rules import CalendarRule, CalendarContext, MonthlyEventRule, MonthBoundaryRule, BusinessOffsetsRule
from .core import CalendarStudio
from .artifact import CalendarArtifact, ValidationReport
from .io import load_holidays, example_holidays

__version__ = "0.1.0"
__all__ = [
    "CalendarStudio",
    "CalendarSpec",
    "CalendarArtifact",
    "CalendarRule",
    "CalendarContext",
    "MonthlyEventSpec",
    "MonthBoundarySpec",
    "BusinessOffsetsSpec",
    "MonthlyEventRule",
    "MonthBoundaryRule",
    "BusinessOffsetsRule",
    "ValidationReport",
    "load_holidays",
    "example_holidays",
]
