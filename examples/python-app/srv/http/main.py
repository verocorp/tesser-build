from __future__ import annotations

import tesser.srv as ts

from app.loader import load
from srv.http.host import HttpHost
from srv.run import run_until_signal


@ts.do_not_use_function
def main() -> None:  # tesser:debt TB051
    app = load()
    host = HttpHost((app.http.host, app.http.port), app)
    print(f"campaign+linkpolicy app listening on {app.http.host or '0.0.0.0'}:{app.http.port}")  # noqa: T201
    run_until_signal(host, app.close)


if __name__ == "__main__":  # tesser:debt TB051
    main()
