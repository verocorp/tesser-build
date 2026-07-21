class FakeEmailSender:
    def __init__(self) -> None:
        self._sent: list[str] = []

    def send(self, address: str) -> None:
        self._sent.append(address)

    def sent(self) -> list[str]:
        return list(self._sent)


def test_registration_sends_one_welcome_email() -> None:
    sender = FakeEmailSender()
    sender.send("newuser@example.com")
    assert sender.sent() == ["newuser@example.com"]
