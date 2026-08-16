from __future__ import annotations

import tesser.srv as ts

from bootstrap.loader import load_app
from srv.http.host import HttpHost
from srv.run import run_until_signal


@ts.function
def main() -> None:
    app = load_app()
    host = HttpHost((app.http.host, app.http.port), app)
    print(f"campaign+linkpolicy app listening on {app.http.host or '0.0.0.0'}:{app.http.port}")  # noqa: T201
    run_until_signal(host, app)


if __name__ == "__main__":  # tessercheck:ignore TB051
    main()
