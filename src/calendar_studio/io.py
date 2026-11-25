from pathlib import Path
import pandas as pd
from .core import holiday_dates


def load_holidays(path, *, date_col="date"):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError("Holiday inputs must be CSV or Parquet")
    return holiday_dates(frame, date_col)


def example_holidays(profile="mac_legacy_v1"):
    """Versioned project fixture, not a complete or official holiday service."""
    from importlib.resources import files

    if profile != "mac_legacy_v1":
        raise ValueError("Unknown holiday example: " + profile)
    return holiday_dates(pd.read_csv(files("calendar_studio") / "data/mac_legacy_v1_holidays.csv"), "fecha")
