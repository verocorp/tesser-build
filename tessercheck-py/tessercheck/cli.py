"""``python -m tessercheck`` — run the checks over paths, print flake8-style."""

import argparse
import sys
from collections.abc import Sequence

from tessercheck import __version__
from tessercheck.finding import CHECKS, codes
from tessercheck.run import run_paths


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tessercheck",
        description="DDD conformance analyzer for Python domain code "
        "(see skills/tesser-build/python.md).",
    )
    p.add_argument("paths", nargs="*", default=["."], help="files or directories (default: .)")
    p.add_argument("--version", action="version", version=f"tessercheck-py {__version__}")
    p.add_argument(
        "--list-checks",
        action="store_true",
        help="print the check registry and exit",
    )
    p.add_argument(
        "--select",
        metavar="CODES",
        help="comma-separated check codes to run exclusively (e.g. TB001,TB010); "
        "the ratchet's blocking/advisory tiers are two CI jobs with different "
        "code lists — never inline suppressions",
    )
    p.add_argument(
        "--ignore",
        metavar="CODES",
        help="comma-separated check codes to skip (applied after --select)",
    )
    return p


def _parse_codes(raw: str, parser: argparse.ArgumentParser, flag: str) -> frozenset[str]:
    """Split a comma-separated code list, upper-cased; an unknown code is a
    loud usage error, never a silently-empty filter."""
    wanted = frozenset(c.strip().upper() for c in raw.split(",") if c.strip())
    if not wanted:
        parser.error(f"{flag}: no check codes given")
    unknown = sorted(wanted - codes())
    if unknown:
        registered = ", ".join(sorted(codes()))
        parser.error(f"{flag}: unknown check code(s) {', '.join(unknown)} (registered: {registered})")
    return wanted


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_checks:
        for c in CHECKS:
            print(f"{c.code}  {c.name}\n    {c.summary}")
        return 0

    selected: frozenset[str] | None = None
    if args.select is not None:
        selected = _parse_codes(args.select, parser, "--select")
    ignored: frozenset[str] = frozenset()
    if args.ignore is not None:
        ignored = _parse_codes(args.ignore, parser, "--ignore")

    paths: list[str] = args.paths or ["."]
    findings, errors = run_paths(paths)
    if selected is not None:
        findings = [f for f in findings if f.code in selected]
    if ignored:
        findings = [f for f in findings if f.code not in ignored]

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
