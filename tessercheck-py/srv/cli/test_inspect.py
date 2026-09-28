import pytest

import srv.cli as cli


def test_inspect_host_routes_usage_errors_as_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.InspectHost().run(["--json"]) == 2
    assert '"usage_error"' in capsys.readouterr().out
