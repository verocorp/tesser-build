from __future__ import annotations

import beta.client as client


class TestRejected:

    def test_a_rejection_carries_its_code_and_message(self) -> None:
        rejected = client.Rejected("empty_key", "a key is never empty")
        assert rejected.code == "empty_key"
        assert rejected.message == "a key is never empty"
        assert str(rejected) == "a key is never empty"
