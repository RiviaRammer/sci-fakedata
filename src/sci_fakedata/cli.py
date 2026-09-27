"""Local CLI: sfd analyze FILE, or sfd demo with a documented public-data excerpt."""

from __future__ import annotations

import argparse
import codecs
from contextlib import ExitStack
from importlib.resources import as_file, files
import json
from pathlib import Path
import sys

from . import analyze
from .io import load_all


def demo_report():
    """Compare Fig. 2b and Extended Data Fig. 3 using unmodified public numeric blocks."""
    resource = files("sci_fakedata").joinpath("datasets")
    provenance = json.loads(resource.joinpath("provenance.json").read_text(encoding="utf-8"))
    with ExitStack() as stack:
        inputs = {record["dataset_name"]: stack.enter_context(as_file(resource.joinpath(record["file"])))
                  for record in provenance["datasets"]}
        report = analyze.scan(inputs, expected_sum={"Fig.2b-1": 100.0, "Extended Data Fig.3f-1": 100.0}, sum_axis=1)
    report.dataset_info = {record["dataset_name"]: record for record in provenance["datasets"]}
    report.notes.append("Public source: " + provenance["article_url"])
    report.notes.append("Publisher Source Data snapshot date: " + provenance["downloaded_at"])
    report.notes.append("The paper has an author correction; see provenance. These results do not establish misconduct.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sfd", description="Local NumPy numerical-pattern analysis")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze_parser = commands.add_parser("analyze", help="analyze a CSV/Excel/NumPy file")
    analyze_parser.add_argument("input", type=Path)
    analyze_parser.add_argument("--sheet", default="0", help="Excel sheet name or zero-based index")
    analyze_parser.add_argument("--all-sheets", action="store_true")
    analyze_parser.add_argument("--header", choices=("auto", "yes", "no"), default="auto")
    analyze_parser.add_argument("--skiprows", type=int, default=0)
    analyze_parser.add_argument("--min-samples", type=int, default=6)
    analyze_parser.add_argument("--max-pairs", type=int, default=50000)
    analyze_parser.add_argument("--expected-sum", type=float, default=None)
    analyze_parser.add_argument("--sum-axis", type=int, default=-1)
    demo_parser = commands.add_parser("demo", help="analyze documented public Nature source data")
    for command in (analyze_parser, demo_parser):
        command.add_argument("--output", "-o", type=Path, help="write full text report")
        command.add_argument("--json", dest="json_path", type=Path, help="write structured JSON report")
        command.add_argument("--show", type=int, default=30, help="maximum findings shown in terminal")
        command.add_argument("--encoding", help="terminal output encoding (default: preserve Python/terminal setting)")
    args = parser.parse_args(argv)
    if args.encoding:
        try:
            codecs.lookup(args.encoding)
        except LookupError:
            parser.error("unknown output encoding: " + args.encoding)
        if not hasattr(sys.stdout, "reconfigure"):
            parser.error("this output stream cannot change encoding; use PYTHONIOENCODING")
        sys.stdout.reconfigure(encoding=args.encoding)
    try:
        if args.command == "demo":
            report = demo_report()
        else:
            header = {"auto": "auto", "yes": True, "no": False}[args.header]
            options = {"header": header, "skiprows": args.skiprows}
            data = args.input
            if args.all_sheets:
                data = load_all(args.input, **options)
                options = {}
            else:
                options["sheet"] = int(args.sheet) if args.sheet.isdecimal() else args.sheet
            report = analyze.scan(data, min_samples=args.min_samples, max_pairs=args.max_pairs,
                                  expected_sum=args.expected_sum, sum_axis=args.sum_axis, **options)
        print(report.summary(max_findings=max(0, args.show)))
        if args.output:
            report.write(args.output)
        if args.json_path:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(report.to_json() + "\n", encoding="utf-8")
    except (OSError, ValueError, ImportError, KeyError, IndexError) as exc:
        parser.exit(2, f"sfd: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
