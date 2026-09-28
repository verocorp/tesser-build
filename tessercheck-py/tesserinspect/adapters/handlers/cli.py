import json
import subprocess
import typing

import tesser.adapters as ts

import protocol
import tesserinspect.client as client

LIMITATIONS: typing.Final[tuple[str, ...]] = (
    "Candidates are inspection hints, not test selections or a complete dependency graph; an empty list does not prove safety.",
    "Dynamic imports, indirect source reads, external plugins, non-Python consumers and custom collection require manual review.",
    "Readers and fixture definitions are conservative repository-wide candidates; ordinary data readers may be irrelevant.",
    "Only tracked and non-ignored current Python sources and ancestor configuration are inspected; deleted source has no current definitions.",
    "The checkout is not an atomic snapshot; do not modify it during inspection. Git rename detection is heuristic.",
)
USAGE: typing.Final[str] = "usage: tesser-inspect-tests --repo PATH --base REF [--json]"


class InspectionHandler(ts.Handler):
    def __init__(self, inspection_client: client.InspectionClient) -> None:
        self._inspection_client = inspection_client

    def inspect(self, cli_request: protocol.CliRequest) -> protocol.CliResponse:
        args = cli_request.args
        if args == ("--help",):
            return protocol.CliResponse(0, stdout=USAGE, stderr="")
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
                if (
                    option not in {"--repo", "--base"}
                    or option in options
                    or index + 1 >= len(args)
                ):
                    raise ValueError(USAGE)
                options[option] = args[index + 1]
                index += 2
            if "--repo" not in options or "--base" not in options:
                raise ValueError(USAGE)
        except ValueError as error:
            return protocol.CliResponse(
                2,
                stdout=json.dumps(
                    {
                        "schema_version": 1,
                        "status": "error",
                        "error": {"code": "usage_error", "message": str(error)},
                    },
                    sort_keys=True,
                ),
                stderr="",
            )
        try:
            inspect_tests_response = self._inspection_client.inspect_tests(
                client.InspectTestsRequest(
                    repo=options["--repo"], base=options["--base"]
                )
            )
        except client.ERRORS as inspection_failed:
            return protocol.CliResponse(
                2,
                stdout=json.dumps(
                    {
                        "schema_version": 1,
                        "status": "error",
                        "error": {
                            "code": inspection_failed.code,
                            "message": inspection_failed.message,
                        },
                    },
                    sort_keys=True,
                ),
                stderr="",
            )
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            return protocol.CliResponse(
                2,
                stdout=json.dumps(
                    {
                        "schema_version": 1,
                        "status": "error",
                        "error": {"code": "input_error", "message": str(error)},
                    },
                    sort_keys=True,
                ),
                stderr="",
            )
        report = {
            "schema_version": 1,
            "status": "ok",
            "baseline": inspect_tests_response.baseline,
            "changes": [
                {"path": path, "previous_path": previous or None, "status": status}
                for path, previous, status in inspect_tests_response.changes
            ],
            "working_tree_changes": [
                {
                    "path": path,
                    "previous_path": previous or None,
                    "index_status": staged,
                    "worktree_status": unstaged,
                }
                for path, previous, staged, unstaged in inspect_tests_response.working_tree_changes
            ],
            "changed_test_files": list(inspect_tests_response.changed_tests),
            "candidates": [
                {
                    "kind": kind,
                    "path": path,
                    "line": line,
                    "symbol": symbol,
                    "reason": reason,
                }
                for kind, path, line, symbol, reason in inspect_tests_response.candidates
            ],
            "limitations": list(LIMITATIONS),
        }
        return protocol.CliResponse(
            0, stdout=json.dumps(report, sort_keys=True, indent=2), stderr=""
        )
