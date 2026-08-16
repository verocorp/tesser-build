from tesser.application.port import Port
from tesser.lifecycle import Closeable


class _Connection:

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_anything_with_close_satisfies_closeable() -> None:
    def shut_down(resource: Closeable) -> None:
        resource.close()

    connection = _Connection()
    shut_down(connection)
    assert connection.closed


def test_closeable_is_not_an_application_port() -> None:
    assert Port not in Closeable.__mro__
