from pathlib import Path
import json
import pandas as pd
import pytest
from calendar_studio import (
    CalendarStudio,
    CalendarSpec,
    CalendarArtifact,
    load_holidays,
    CalendarRule,
    CalendarContext,
)


def test_missing_holidays_is_error_and_empty_is_explicit():
    with pytest.raises(ValueError):
        CalendarStudio().generate(start="2026-01-01", end="2026-01-03", holidays=None)
    assert CalendarStudio().generate(start="2026-01-01", end="2026-01-03", holidays=[]).validate().ok
    with pytest.raises(FileNotFoundError):
        load_holidays("nonexistent-holidays.csv")


@pytest.mark.parametrize(
    "holidays", [[None], ["2026-01-01"] * 2, ["bad"], ["2026-01-01T12:00:00"], ["2026-01-01T00:00:00Z"]]
)
def test_invalid_holidays_rejected(holidays):
    with pytest.raises((ValueError, TypeError)):
        CalendarStudio().generate(start="2026-01-01", end="2026-01-03", holidays=holidays)


def configured():
    return CalendarStudio(
        CalendarSpec(
            rules=[
                dict(type="monthly_event", name="payroll", days=[15, 30], adjustment="preceding"),
                dict(type="monthly_event", name="payment", days=[17], adjustment="following"),
                dict(type="business_offsets", events=["payroll"], before=10, after=10),
                dict(type="month_boundary", name="first_business", edge="first"),
            ]
        )
    )


def test_generic_shift_leap_and_offsets():
    frame = (
        configured()
        .generate(start="2024-01-01", end="2024-03-31", holidays=["2024-02-29"])
        .to_pandas()
        .set_index("date")
    )
    assert frame.loc["2024-02-28", "payroll"] == 1
    assert frame.loc["2024-02-29", "is_business_day"] == 0
    assert frame.loc["2024-02-19", "payment"] == 1
    assert frame.loc["2024-02-01", "first_business"] == 1
    assert frame.loc["2024-02-15", "payroll"] == 1
    assert frame.loc["2024-02-14", "payroll__before_10"] == 1


def test_generic_context_is_invariant_to_requested_slice():
    full = configured().generate(start="2021-01-01", end="2022-12-31", holidays=[]).to_pandas()
    cropped = configured().generate(start="2022-12-15", end="2022-12-31", holidays=[]).to_pandas()
    pd.testing.assert_frame_equal(
        full.loc[full.date.between("2022-12-15", "2022-12-31")].reset_index(drop=True), cropped
    )
    assert (
        cropped.loc[cropped.date == "2022-12-30", "payroll__before_10"].item() == 1
    )  # Jan 15 2023 is Sunday: preceding Jan 13, ten business days before is Dec 30.


def test_corrected_november_holiday_and_legacy_projection():
    holidays = load_holidays(Path(__file__).parents[1] / "festivos.csv", date_col="fecha")
    assert "2026-11-02" in holidays
    artifact = CalendarStudio.from_profile("mac_legacy_v1").generate(
        start="2022-01-01", end="2027-12-31", holidays=holidays
    )
    f = artifact.to_pandas().set_index("fecha")
    assert f.loc["2026-11-02", "día festivo"] == 1
    view = artifact.view("mac_legacy_v1").to_pandas()
    assert view.shape == (1517, 244)
    assert "2026-11-02" not in set(view.fecha)
    assert not {"fin de semana", "día festivo"} & set(view.columns)
    before = (
        CalendarStudio.from_profile("mac_legacy_v1")
        .generate(start="2022-01-01", end="2027-12-31", holidays=[h for h in holidays if h != "2026-11-02"])
        .view("mac_legacy_v1")
        .to_pandas()
    )
    assert len(before) == 1518
    shared = view.set_index("fecha").ne(before.set_index("fecha").loc[view.fecha])
    assert shared.any().any()  # Offsets change too, not only the holiday row.


def test_artifact_roundtrip_and_tamper(tmp_path):
    original = configured().generate(start="2026-01-01", end="2026-02-28", holidays=[])
    path = original.save(tmp_path / "calendar")
    pd.testing.assert_frame_equal(original.to_pandas(), CalendarArtifact.load(path).to_pandas())
    assert original.view("business").validate().ok
    with pytest.raises(FileExistsError):
        original.save(path)
    (path / "calendar.parquet").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        CalendarArtifact.load(path)


def test_strict_validation_before_normalization():
    a = CalendarStudio().generate(start="2026-01-01", end="2026-01-03", holidays=[])
    f = a.to_pandas()
    f.loc[0, "is_holiday"] = 2
    assert not CalendarArtifact(f, a.metadata).validate().ok
    f = a.to_pandas().drop(columns="date")
    assert not CalendarArtifact(f, a.metadata).validate().ok
    f = a.to_pandas().iloc[::-1]
    assert not CalendarArtifact(f, a.metadata).validate().ok
    f = a.to_pandas().astype({"is_holiday": "float64"})
    assert not CalendarArtifact(f, a.metadata).validate().ok


@pytest.mark.parametrize(
    "config",
    [
        {"rules": [dict(type="monthly_event", name="x", days=[32])]},
        {"rules": [dict(type="monthly_event", name="x", days=[15, 15])]},
        {"profile": "mac_legacy_v1", "rules": [dict(type="monthly_event", name="x", days=[15])]},
        {"weekmask": []},
        {"unexpected": True},
    ],
)
def test_invalid_specs(config):
    with pytest.raises(ValueError):
        CalendarSpec.model_validate(config)


def test_dependencies_collisions_and_custom_rules():
    with pytest.raises(ValueError, match="dependencies"):
        CalendarStudio(CalendarSpec(rules=[dict(type="business_offsets", events=["absent"])])).generate(
            start="2026-01-01", end="2026-01-31", holidays=[]
        )
    with pytest.raises(ValueError, match="collide"):
        CalendarStudio(
            CalendarSpec(rules=[dict(type="monthly_event", name="is_holiday", days=[15])])
        ).generate(start="2026-01-01", end="2026-01-31", holidays=[])

    class Always(CalendarRule):
        outputs = ("custom",)

        def describe(self):
            return dict(type="custom", version=1)

        def apply(self, context: CalendarContext):
            return pd.DataFrame({"custom": [1] * len(context.dates)}, index=context.features.index)

    f = (
        CalendarStudio(rules=[Always()])
        .generate(start="2026-01-01", end="2026-01-02", holidays=[])
        .to_pandas()
    )
    assert f.custom.eq(1).all()


def test_cli(tmp_path):
    from calendar_studio.cli import main

    p = tmp_path / "holidays.parquet"
    pd.DataFrame({"date": ["2026-11-02"]}).to_parquet(p, index=False)
    assert (
        main(
            [
                "generate",
                "--start",
                "2026-01-01",
                "--end",
                "2026-12-31",
                "--holidays",
                str(p),
                "--output",
                str(tmp_path / "output"),
            ]
        )
        == 0
    )
    assert CalendarArtifact.load(tmp_path / "output").validate().ok


def test_studio_ui():
    from streamlit.testing.v1 import AppTest
    import calendar_studio

    app = AppTest.from_file(str(Path(calendar_studio.__file__).parent / "app.py")).run()
    assert not app.exception
    app.checkbox[0].set_value(True)
    app.button[0].click().run()
    assert not app.exception
    assert app.success


def test_packaged_holiday_correction():
    from calendar_studio import example_holidays

    assert "2026-11-02" in example_holidays()


def test_weekmask_and_offset_dependency_order():
    spec = CalendarSpec(
        weekmask=["Mon", "Tue", "Wed", "Thu", "Sun"],
        rules=[
            dict(type="business_offsets", events=["x"], before=1, after=0),
            dict(type="monthly_event", name="x", days=[17], adjustment="following"),
        ],
    )
    f = (
        CalendarStudio(spec)
        .generate(start="2026-01-01", end="2026-01-31", holidays=[])
        .to_pandas()
        .set_index("date")
    )
    assert f.loc["2026-01-18", "x"] == 1
    assert f.loc["2026-01-15", "x__before_1"] == 1


def test_installed_package_origin():
    import os, calendar_studio

    prefix = os.environ.get("CALENDAR_STUDIO_EXPECTED_PREFIX")
    if prefix:
        assert Path(calendar_studio.__file__).resolve().is_relative_to(Path(prefix))
