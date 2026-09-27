"""Run from the repository after pip install -e .; outputs stay local."""

from pathlib import Path
import argparse

import sci_fakedata as sfd
from sci_fakedata.cli import demo_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", type=Path, help="optional CSV/Excel/NPY instead of bundled public data")
    parser.add_argument("--sheet", default="0")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()
    if args.input:
        sheet = int(args.sheet) if args.sheet.isdecimal() else args.sheet
        report = sfd.analyze.scan(args.input, sheet=sheet)
    else:
        report = demo_report()
    print(report.summary())
    report.write(args.output_dir / "demo_report.txt")
    report.write(args.output_dir / "demo_report.json")


if __name__ == "__main__":
    main()
