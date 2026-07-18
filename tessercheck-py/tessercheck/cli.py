"""``python -m tessercheck`` — run the checks over paths, print flake8-style."""

import argparse
import sys
from collections.abc import Sequence

from tessercheck import __version__
from tessercheck.finding import CHECKS
from tessercheck.run import run_paths


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tessercheck",
        description="DDD conformance analyzer for Python domain code "
        "(see skills/ddd/python.md).",
    )
    p.add_argument("paths", nargs="*", default=["."], help="files or directories (default: .)")
    p.add_argument("--version", action="version", version=f"tessercheck-py {__version__}")
    p.add_argument(
        "--list-checks",
        action="store_true",
        help="print the check registry and exit",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_checks:
        for c in CHECKS:
            print(f"{c.code}  {c.name}\n    {c.summary}")
        return 0

    paths: list[str] = args.paths or ["."]
    findings, errors = run_paths(paths)

    for finding in findings:
        print(finding.render())
    for err in errors:
        print(err, file=sys.stderr)

    if findings:
        n = len(findings)
        print(
            f"\n{n} finding{'s' if n != 1 else ''} — "
            "fix or annotate with '# tessercheck:ignore'.",
            file=sys.stderr,
        )
    if errors:
        return 2
    return 1 if findings else 0
