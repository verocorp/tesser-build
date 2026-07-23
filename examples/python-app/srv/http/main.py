from __future__ import annotations

import os

from bootstrap.bootstrap import new
from bootstrap.config import from_env
from srv.http.host import HttpHost
from srv.run import run_until_signal


def main() -> None:
    cfg = from_env(os.getenv)
    app = new(cfg)
    host = HttpHost((cfg.http.host, cfg.http.port), app)
    print(f"campaign+linkpolicy app listening on {cfg.http.host or '0.0.0.0'}:{cfg.http.port}")  # noqa: T201
    run_until_signal(host, app)


if __name__ == "__main__":
    main()
