import json

import tesser.testing as ts

import protocol
import tesserinspect.adapters.handlers as handlers
import tesserinspect.client as client


@ts.fake
class InspectionClient(client.InspectionClient):
    def inspect_tests(
        self, inspect_tests_request: client.InspectTestsRequest
    ) -> client.InspectTestsResponse:
        if inspect_tests_request.base == "broken":
            raise ValueError("invalid source")
        return client.InspectTestsResponse(
            baseline="abc",
            changes=(("test_new.py", "", "?"),),
            changed_tests=("test_new.py",),
            candidates=(),
            working_tree_changes=(),
        )


def test_handler_returns_versioned_json_not_a_test_pass() -> None:
    inspection_handler = handlers.InspectionHandler(InspectionClient())

    cli_response = inspection_handler.inspect(
        protocol.CliRequest(args=("--repo", "/repo", "--base", "HEAD", "--json"))
    )
    report = json.loads(cli_response.stdout)

    assert cli_response.exit_code == 0
    assert report["schema_version"] == 1
    assert report["status"] == "ok"
    assert report["baseline"] == "abc"
    assert report["changed_test_files"] == ["test_new.py"]
    assert report["limitations"]


def test_handler_errors_are_nonzero_machine_readable_and_not_clean_reports() -> None:
    inspection_handler = handlers.InspectionHandler(InspectionClient())

    for args in (
        ("--json",),
        ("--repo", "/repo", "--base", "broken", "--json"),
        ("--repo", "/repo", "--base", "HEAD", "--unknown"),
    ):
        cli_response = inspection_handler.inspect(protocol.CliRequest(args=args))
        report = json.loads(cli_response.stdout)
        assert cli_response.exit_code == 2
        assert report["status"] == "error"
        assert "candidates" not in report
