"""``python -m tessercheck`` — run the checks over paths, print flake8-style."""

import argparse
import pathlib
import sys
from collections.abc import Sequence

from tessercheck import __version__
from tessercheck.discovery import APP_LEVEL_PACKAGES, classify_root, totality_errors
from tessercheck.finding import CHECKS, codes
from tessercheck.run import run_paths


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tessercheck",
        description="DDD conformance analyzer for Python domain code "
        "(see skills/tesser-build/python.md).",
    )
    p.add_argument(
        "paths",
        nargs="*",
        default=[],
        help="files or directories (default: --app-root if given, else .)",
    )
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
    p.add_argument(
        "--app-root",
        metavar="DIR",
        help="treat DIR as an app root: discover its bounded contexts by their "
        "Client seam and fail on any root-level package that classifies as "
        "neither app-level nor context (the totality guard); when no paths "
        "are given, DIR is also what gets checked. Discovery failures are "
        "structural errors (exit 2), not findings — --select/--ignore never "
        "scope them away",
    )
    p.add_argument(
        "--app-level",
        metavar="NAMES",
        help="comma-separated package names to treat as app-level plumbing in "
        f"addition to the template's ({', '.join(sorted(APP_LEVEL_PACKAGES))}); "
        "requires --app-root — an extension is declared, never inferred",
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

    if args.app_level is not None and args.app_root is None:
        parser.error("--app-level requires --app-root")
    app_root: pathlib.Path | None = None
    app_level = APP_LEVEL_PACKAGES
    if args.app_root is not None:
        app_root = pathlib.Path(args.app_root)
        if not app_root.is_dir():
            parser.error(f"--app-root: not a directory: {args.app_root}")
        if args.app_level is not None:
            extra = frozenset(n.strip() for n in args.app_level.split(",") if n.strip())
            if not extra:
                parser.error("--app-level: no package names given")
            app_level = APP_LEVEL_PACKAGES | extra

    paths: list[str] = args.paths or ([str(app_root)] if app_root is not None else ["."])
    findings, errors = run_paths(paths)
    if app_root is not None:
        errors.extend(totality_errors(app_root, classify_root(app_root, app_level), app_level))
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
