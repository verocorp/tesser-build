"""End-to-end: drives the real wired service (main.wire) over actual HTTP."""

import json
import threading
from collections.abc import Iterator
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

from main import wire


@pytest.fixture
def server() -> Iterator[tuple[str, int]]:
    httpd: ThreadingHTTPServer = wire(("127.0.0.1", 0))
    host = str(httpd.server_address[0])
    port = int(httpd.server_address[1])
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield (host, port)
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _request(
    addr: tuple[str, int], method: str, path: str, body: object | None = None
) -> tuple[int, dict[str, Any]]:
    conn = HTTPConnection(addr[0], addr[1], timeout=5)
    payload = json.dumps(body).encode("utf-8") if body is not None else b""
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn.request(method, path, body=payload, headers=headers)
    resp = conn.getresponse()
    data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    status = resp.status
    conn.close()
    return status, data


def test_full_report_lifecycle_over_http(server: tuple[str, int]) -> None:
    # 1. create a report with an initial expense
    status, created = _request(
        server,
        "POST",
        "/reports",
        {
            "title": "Trip to NYC",
            "labels": {"project": "apollo"},
            "expenses": [
                {
                    "amount": "42.50",
                    "currency": "USD",
                    "category": "travel",
                    "receipt_number": "R-1",
                }
            ],
        },
    )
    assert status == 201
    report_id = created["report_id"]
    assert report_id
    assert created["status"] == "draft"
    assert created["total_amount"] == "42.50"

    # 2. add a second expense to the draft report
    status, after_add = _request(
        server,
        "POST",
        f"/reports/{report_id}/expenses",
        {
            "amount": "7.50",
            "currency": "USD",
            "category": "meals",
            "receipt_number": "R-2",
        },
    )
    assert status == 200
    assert len(after_add["expenses"]) == 2
    assert after_add["total_amount"] == "50.00"

    # 3. fetch the report and see both expenses, the title, and the labels
    status, fetched = _request(server, "GET", f"/reports/{report_id}")
    assert status == 200
    assert fetched["title"] == "Trip to NYC"
    assert fetched["labels"] == {"project": "apollo"}
    assert len(fetched["expenses"]) == 2
    assert fetched["status"] == "draft"

    # 4. submit the report
    status, submitted = _request(server, "POST", f"/reports/{report_id}/submit")
    assert status == 200
    assert submitted["status"] == "submitted"

    # 5. editing a submitted report is rejected
    status, rejected = _request(
        server,
        "POST",
        f"/reports/{report_id}/expenses",
        {
            "amount": "1.00",
            "currency": "USD",
            "category": "meals",
            "receipt_number": "R-3",
        },
    )
    assert status == 400
    assert "error" in rejected

    # 6. submitting again is rejected too
    status, _ = _request(server, "POST", f"/reports/{report_id}/submit")
    assert status == 400

    # 7. fetching an unknown report is a 404
    status, missing = _request(server, "GET", "/reports/does-not-exist")
    assert status == 404
    assert "error" in missing


def test_report_over_the_cap_is_rejected_over_http(server: tuple[str, int]) -> None:
    status, body = _request(
        server,
        "POST",
        "/reports",
        {
            "title": "Too much",
            "expenses": [
                {
                    "amount": "1000.01",
                    "currency": "USD",
                    "category": "travel",
                    "receipt_number": "R-1",
                }
            ],
        },
    )
    assert status == 400
    assert "error" in body
