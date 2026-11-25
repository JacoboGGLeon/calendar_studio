"""Immutable-by-copy calendar views, validation, atomic artifacts and integrity checks."""

from dataclasses import dataclass
from pathlib import Path
from datetime import date
import copy
import hashlib
import json
import shutil
import tempfile
import pandas as pd
from pandas.api.types import is_integer_dtype
from .specs import CalendarSpec


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@dataclass(frozen=True)
class ValidationReport:
    errors: tuple[str, ...]

    @property
    def ok(self):
        return not self.errors

    def raise_for_errors(self):
        if self.errors:
            raise ValueError("; ".join(self.errors))
        return self


class CalendarArtifact:
    def __init__(self, frame, metadata):
        self._frame = frame.copy(deep=True)
        self._metadata = copy.deepcopy(metadata)

    @property
    def metadata(self):
        return copy.deepcopy(self._metadata)

    def to_pandas(self):
        return self._frame.copy(deep=True)

    def validate(self):
        errors = []
        frame = self._frame
        try:
            spec = CalendarSpec.model_validate(self._metadata["spec"])
        except (ValueError, KeyError) as exc:
            return ValidationReport((str(exc),))
        col = spec.date_col
        if not frame.columns.is_unique:
            errors.append("Duplicate column names")
        if col not in frame:
            return ValidationReport(tuple([*errors, "Missing date column"]))
        dates = frame[col]
        try:
            parsed = [date.fromisoformat(str(d)) for d in dates]
            if parsed != sorted(set(parsed)):
                errors.append("Dates must be ordered and unique")
            expected = (
                pd.date_range(self._metadata["start"], self._metadata["end"]).strftime("%Y-%m-%d").tolist()
                if self._metadata["axis"] == "daily"
                else self._metadata["business_dates"]
            )
            if dates.tolist() != expected:
                errors.append("Date axis does not match declared coverage")
        except (ValueError, TypeError, KeyError):
            errors.append("Invalid date axis")
        for name in frame.columns:
            if name == col:
                continue
            if (
                not is_integer_dtype(frame[name].dtype)
                or frame[name].isna().any()
                or not frame[name].isin([0, 1]).all()
            ):
                errors.append("Nonbinary or nullable integer feature: " + name)
        if len(frame.columns) < 2:
            errors.append("Calendar has no features")
        if spec.profile == "mac_legacy_v1":
            from ._legacy import required_output_columns

            expected = required_output_columns()
            if self._metadata.get("view") == "mac_legacy_v1":
                expected = [c for c in expected if c not in ["día festivo", "fin de semana"]]
            expected = [col if c == "fecha" else c for c in expected]
            if frame.columns.tolist() != expected:
                errors.append("Legacy feature schema/order mismatch")
        return ValidationReport(tuple(errors))

    def view(self, name):
        if name not in ["business", "mac_legacy_v1"]:
            raise ValueError("Unknown calendar view: " + name)
        frame = self._frame
        meta = self.metadata
        col = meta["spec"]["date_col"]
        if name == "mac_legacy_v1" and meta["spec"]["profile"] != "mac_legacy_v1":
            raise ValueError("MAC view requires the explicit legacy profile")
        frame = frame.loc[frame[col].isin(meta["business_dates"])].copy().reset_index(drop=True)
        meta["axis"] = "business"
        meta["view"] = name
        if name == "mac_legacy_v1":
            frame = frame.drop(columns=["fin de semana", "día festivo"])
        result = CalendarArtifact(frame, meta)
        result.validate().raise_for_errors()
        return result

    def export(self, path):
        self.validate().raise_for_errors()
        path = Path(path)
        if path.suffix not in [".parquet", ".csv"]:
            raise ValueError("Choose .parquet or .csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
        try:
            if path.suffix == ".parquet":
                self._frame.to_parquet(temp, index=False, compression="zstd")
            else:
                self._frame.to_csv(temp, index=False)
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
        return path

    def save(self, path):
        self.validate().raise_for_errors()
        path = Path(path).resolve()
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="calendar_", dir=path.parent))
        try:
            data = staging / "calendar.parquet"
            self.export(data)
            manifest = dict(
                format_version=1,
                library_version="0.1.0",
                metadata=self.metadata,
                columns=self._frame.columns.tolist(),
                rows=len(self._frame),
                sha256=file_sha(data),
            )
            (staging / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)
            )
            staging.rename(path)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        return path

    @classmethod
    def load(cls, path):
        path = Path(path)
        manifest = json.loads((path / "manifest.json").read_text())
        if manifest.get("format_version") != 1:
            raise ValueError("Unsupported artifact format")
        if file_sha(path / "calendar.parquet") != manifest["sha256"]:
            raise ValueError("Calendar integrity mismatch")
        frame = pd.read_parquet(path / "calendar.parquet")
        if frame.columns.tolist() != manifest["columns"] or len(frame) != manifest["rows"]:
            raise ValueError("Artifact schema mismatch")
        result = cls(frame, manifest["metadata"])
        result.validate().raise_for_errors()
        return result
