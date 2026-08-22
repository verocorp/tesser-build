from __future__ import annotations

import protocol.http as http


def test_a_response_carries_the_status_and_body_it_was_built_with() -> None:
    resp = http.Response(201, {"id": "c1"})
    assert resp.status == 201
    assert resp.body == {"id": "c1"}


def test_two_responses_with_the_same_status_and_body_are_equal() -> None:
    assert http.Response(200, {"status": "added"}) == http.Response(200, {"status": "added"})


def test_responses_differing_in_status_are_not_equal() -> None:
    assert http.Response(200, {"id": "c1"}) != http.Response(201, {"id": "c1"})


def test_responses_differing_in_body_are_not_equal() -> None:
    assert http.Response(200, {"id": "c1"}) != http.Response(200, {"id": "c2"})
