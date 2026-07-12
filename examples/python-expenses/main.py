"""main — the composition root.

Constructs the concrete repository and service, composes them behind the
public `Client`, constructs the handler, and injects the `Client` into it.
This is the only module that imports the concrete impl package
(`expensewellimpl`); everything else depends on the public `expensewell`
package or a Protocol.
"""

from http.server import ThreadingHTTPServer

from expensewellapp.service import ExpenseReportService
from expensewellimpl import InMemoryExpenseReportRepository, new_client
from transport import make_handler


def wire(addr: tuple[str, int]) -> ThreadingHTTPServer:
    repo = InMemoryExpenseReportRepository()  # the impl choice lives here … and ONLY here
    svc = ExpenseReportService(repo)
    client = new_client(svc)  # compose behind the public Client
    handler = make_handler(client)  # construct the handler, INJECT the Client
    return ThreadingHTTPServer(addr, handler)


def main() -> None:
    server = wire(("0.0.0.0", 8080))
    print("expensewell listening on :8080")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
