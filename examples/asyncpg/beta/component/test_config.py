from __future__ import annotations

import pytest

import beta.component.config as config
import pgdatabase.database as pgdatabase


class TestConfig:

    def test_a_postgres_coordinate_requests_that_database(self) -> None:
        cfg = config.Config(config.Spec(storage="postgres://a@b/c"))
        assert cfg.storage == "postgres://a@b/c"
        assert cfg.database == pgdatabase.DatabaseRequest("postgres://a@b/c")

    def test_an_unknown_coordinate_is_refused(self) -> None:
        with pytest.raises(ValueError):
            config.Config(config.Spec(storage="sqlite"))
