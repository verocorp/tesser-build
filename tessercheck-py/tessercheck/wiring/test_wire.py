from __future__ import annotations

from pathlib import Path

import tessercheck.client.client as client
import tessercheck.wiring.config as config
import tessercheck.wiring.wire as wire


def test_build_returns_a_working_client(tmp_path: Path) -> None:
    checker, closeable = wire.build(config.Config())
    (tmp_path / ".tesser-root").write_text("app\n", encoding="utf-8")
    response = checker.check(client.CheckRequest(root=str(tmp_path)))
    assert response.findings == ()
    closeable.close()


def test_build_returns_a_closeable_that_closes_twice(tmp_path: Path) -> None:
    _, closeable = wire.build(config.Config())
    closeable.close()
    closeable.close()


def test_an_undeclared_tree_is_reported_through_the_built_client(tmp_path: Path) -> None:
    checker, closeable = wire.build(config.Config())
    response = checker.check(client.CheckRequest(root=str(tmp_path)))
    assert any("TB044" in finding for finding in response.findings)
    closeable.close()
