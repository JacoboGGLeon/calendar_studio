"""CLI for generation and the optional Studio frontend."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from .core import CalendarStudio
from .specs import CalendarSpec
from .io import load_holidays


def main(argv=None):
    parser = argparse.ArgumentParser(prog="calendar-studio")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate")
    for flag in ["start", "end", "holidays", "output"]:
        generate.add_argument("--" + flag, required=True)
    generate.add_argument("--holiday-date-col", default="date")
    generate.add_argument("--spec")
    generate.add_argument("--profile", choices=["generic", "mac_legacy_v1"], default="generic")
    commands.add_parser("studio")
    args = parser.parse_args(argv)
    if args.command == "studio":
        try:
            import streamlit  # noqa: F401
        except ImportError:
            parser.error("Install calendar-studio[studio]")
        return subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(Path(__file__).with_name("app.py"))]
        )
    studio = (
        CalendarStudio(CalendarSpec.model_validate(json.loads(Path(args.spec).read_text())))
        if args.spec
        else CalendarStudio.from_profile(args.profile)
        if args.profile != "generic"
        else CalendarStudio()
    )
    calendar = studio.generate(
        start=args.start, end=args.end, holidays=load_holidays(args.holidays, date_col=args.holiday_date_col)
    )
    print(calendar.save(args.output))
    return 0
