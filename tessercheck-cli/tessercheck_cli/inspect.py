import json
import subprocess
import sys
from typing import Final

import tesserinspect.client as client
import tesserinspect.component as component

_USAGE: Final[str] = "usage: tesser-inspect-tests --repo PATH --base REF [--json]"
_LIMITATIONS: Final[tuple[str, ...]] = (
    "Candidates are inspection hints, not test selections or a complete dependency graph; an empty list does not prove safety.",
    "Dynamic imports, indirect source reads, external plugins, non-Python consumers and custom collection require manual review.",
    "Readers and fixture definitions are conservative repository-wide candidates; ordinary data readers may be irrelevant.",
    "Only tracked and non-ignored current Python sources and ancestor configuration are inspected; deleted source has no current definitions.",
    "The checkout is not an atomic snapshot; do not modify it during inspection. Git rename detection is heuristic.",
)


def _error(code: str, message: str) -> int:
    print(json.dumps({"schema_version": 1, "status": "error", "error": {"code": code, "message": message}}, sort_keys=True))
    return 2


def main() -> int:
    args = sys.argv[1:]
    if args == ["--help"]:
        print(_USAGE)
        return 0
    options = {}
    index = 0
    try:
        while index < len(args):
            option = args[index]
            if option == "--json":
                if option in options:
                    raise ValueError("duplicate --json")
                options[option] = "true"
                index += 1
                continue
            if option not in {"--repo", "--base"} or option in options or index + 1 >= len(args):
                raise ValueError(_USAGE)
            options[option] = args[index + 1]
            index += 2
        if "--repo" not in options or "--base" not in options:
            raise ValueError(_USAGE)
    except ValueError as error:
        return _error("usage_error", str(error))
    try:
        inspection = component.Inspection(component.Config(component.Spec()))
        try:
            response = inspection.client.inspect_tests(
                client.InspectTestsRequest(repo=options["--repo"], base=options["--base"])
            )
        finally:
            inspection.close()
    except client.ERRORS as error:
        return _error(error.code, error.message)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return _error("input_error", str(error))
    print(json.dumps({
        "schema_version": 1,
        "status": "ok",
        "baseline": response.baseline,
        "changes": [
            {"path": path, "previous_path": previous or None, "status": status}
            for path, previous, status in response.changes
        ],
        "working_tree_changes": [
            {"path": path, "previous_path": previous or None, "index_status": staged, "worktree_status": unstaged}
            for path, previous, staged, unstaged in response.working_tree_changes
        ],
        "changed_test_files": list(response.changed_tests),
        "candidates": [
            {"kind": kind, "path": path, "line": line, "symbol": symbol, "reason": reason}
            for kind, path, line, symbol, reason in response.candidates
        ],
        "limitations": list(_LIMITATIONS),
    }, sort_keys=True, indent=2))
    return 0
