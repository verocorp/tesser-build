from __future__ import annotations

import beta.client as client


class TestKeyRejected:

    def test_a_rejected_key_carries_its_code_and_message(self) -> None:
        key_rejected = client.KeyRejected("empty_key", "a key is never empty")
        assert key_rejected.code == "empty_key"
        assert key_rejected.message == "a key is never empty"
        assert str(key_rejected) == "a key is never empty"
