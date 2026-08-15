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
