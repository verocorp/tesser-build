"""A minimal, runnable link-campaign service: the composition root that wires
the in-memory repository, the application service, the public Client, and the
HTTP handler together, then serves requests.

Run it with:  ``python main.py``  (from examples/python/).
"""

from http.server import ThreadingHTTPServer

from campaignapp import CampaignService
from linkcampaignimpl import InMemoryCampaignRepository, new_client
from transport import make_handler


def wire(addr: tuple[str, int]) -> ThreadingHTTPServer:
    """The composition root: the one place that chooses the concrete
    implementations (here, the in-memory repository), composes them behind the
    public ``linkcampaign.Client``, and constructs the handler, injecting the
    Client into it. Swapping the repository for a database-backed one later is
    a one-line change, here only.
    """
    repo = InMemoryCampaignRepository()  # the impl choice lives here ...
    svc = CampaignService(repo)  # ... inject it into the service
    client = new_client(svc)  # compose behind the public Client
    handler = make_handler(client)  # construct handler, INJECT the Client
    return ThreadingHTTPServer(addr, handler)


def main() -> None:
    server = wire(("", 8080))
    print("link-campaign service listening on :8080")  # noqa: T201
    server.serve_forever()  # a minimal runnable main


if __name__ == "__main__":
    main()
