from __future__ import annotations

from pathlib import Path
from typing import Optional

import tessercheck.client.client as client
import tessercheck.wiring.wire as wire
from bootstrap.config import Config, from_env


def test_reading_the_environment_asks_it_for_nothing_yet() -> None:
    asked: list[str] = []

    def getenv(name: str) -> Optional[str]:
        asked.append(name)
        return None

    from_env(getenv)
    assert asked == []


def test_a_hostile_environment_cannot_break_the_read() -> None:
    def getenv(name: str) -> Optional[str]:
        raise AssertionError(name)

    assert from_env(getenv).tessercheck is not None


def test_the_config_from_the_environment_wires_a_working_client(tmp_path: Path) -> None:
    def getenv(name: str) -> Optional[str]:
        return None

    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    checker, closeable = wire.build(from_env(getenv).tessercheck)
    try:
        assert checker.check(client.CheckRequest(root=str(tmp_path))).findings == ()
    finally:
        closeable.close()


def test_a_default_config_carries_a_context_config_of_its_own() -> None:
    assert Config().tessercheck is not Config().tessercheck
