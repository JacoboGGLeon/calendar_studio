import os
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import calendar_engine as engine  # noqa: E402


def test_export_layout_matches_required_contract():
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        df = engine.build_base_calendar(2022, 2027)
        df = engine.run_recalculation_pipeline(df)
        out = engine.to_required_output_layout(df)
    finally:
        os.chdir(cwd)

    assert out.shape == (2191, 246)
    assert list(out.columns) == engine.required_output_columns()
    assert {"año", "mes", "dia", "weekday", "es_habil"}.isdisjoint(out.columns)


def test_quincenas_backward_and_impuestos_forward_from_business_days():
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        df = engine.build_base_calendar(2022, 2027)
        df = engine.run_recalculation_pipeline(df)
        out = engine.to_required_output_layout(df)
    finally:
        os.chdir(cwd)

    checks = out.set_index("fecha")

    # Jan 2022: theoretical 30th was Sunday, so payroll moves backward.
    assert checks.loc["2022-01-28", "día de cobro de quincena"] == 1
    assert checks.loc["2022-01-31", "día de cobro de quincena"] == 0

    # Holy week holidays in festivos.csv: payroll cannot fall on a holiday.
    assert checks.loc["2022-04-13", "día de cobro de quincena"] == 1
    assert checks.loc["2022-04-15", "día de cobro de quincena"] == 0

    # Taxes move forward from the 17th when the 17th is not a business day.
    assert checks.loc["2025-04-17", "día de pago de impuestos"] == 0
    assert checks.loc["2025-04-21", "día de pago de impuestos"] == 1


def test_events_never_land_on_non_business_days():
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        df = engine.build_base_calendar(2022, 2027)
        df = engine.run_recalculation_pipeline(df)
    finally:
        os.chdir(cwd)

    diagnostics = engine.validate_business_rules(df)

    assert diagnostics["quincenas_en_no_habil"] == []
    assert diagnostics["impuestos_en_no_habil"] == []


def test_flags_are_independent_and_offsets_can_overlap_events():
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        df = engine.build_base_calendar(2022, 2027)
        df = engine.run_recalculation_pipeline(df)
        out = engine.to_required_output_layout(df).set_index("fecha")
    finally:
        os.chdir(cwd)

    # 2022-01-15 was Saturday, so the first quincena moves back to 2022-01-14.
    # 2022-01-14 is also exactly 10 business days before the 2022-01-28 quincena.
    # Both flags must coexist; calendar flags are independent, not mutually exclusive.
    assert out.loc["2022-01-14", "día de cobro de quincena"] == 1
    assert out.loc["2022-01-14", "10 días antes de día de cobro de quincena"] == 1


def test_validation_reports_overlaps_as_valid_not_warning():
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        df = engine.build_base_calendar(2022, 2027)
        df = engine.run_recalculation_pipeline(df)
        report = engine.validate_export_calendar(df)
    finally:
        os.chdir(cwd)

    assert report["ok"] is True
    assert report["overlap_count"] > 0
    assert report["max_flags_on_one_date"] > 1
    overlap_check = next(item for item in report["checks"] if item["check"] == "overlapping_flags_allowed")
    assert overlap_check["ok"] is True
