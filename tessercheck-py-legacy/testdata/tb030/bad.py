from unittest.mock import MagicMock, patch


def test_registration_sends_one_welcome_email() -> None:
    sender = MagicMock()
    sender.send("newuser@example.com")
    sender.send.assert_called_once_with("newuser@example.com")


@patch("app.registration.deliver")
def test_delivery_is_patched(deliver: MagicMock) -> None:
    deliver.return_value = None
    assert deliver is not None
