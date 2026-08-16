from __future__ import annotations

from pathlib import Path

import pytest

import tessercheck.client.client as client
import tessercheck.wiring.config as config
import tessercheck.wiring.wire as wire


def test_the_context_takes_no_settings_yet() -> None:
    with pytest.raises(TypeError):
        config.Config("some/tree")  # type: ignore[call-arg]


def test_a_config_wires_a_client_that_checks_a_declared_tree(tmp_path: Path) -> None:
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    checker, closeable = wire.build(config.Config())
    try:
        assert checker.check(client.CheckRequest(root=str(tmp_path))).findings == ()
    finally:
        closeable.close()


def test_two_configs_wire_two_independent_clients(tmp_path: Path) -> None:
    first, first_closeable = wire.build(config.Config())
    second, second_closeable = wire.build(config.Config())
    try:
        assert first is not second
    finally:
        first_closeable.close()
        second_closeable.close()
