from http.server import ThreadingHTTPServer

from campaignapp import CampaignService
from linkcampaignimpl import InMemoryCampaignRepository, new_client
from transport import make_handler


def wire(addr: tuple[str, int]) -> ThreadingHTTPServer:
    repo = InMemoryCampaignRepository()
    svc = CampaignService(repo)
    client = new_client(svc)
    handler = make_handler(client)
    return ThreadingHTTPServer(addr, handler)


def main() -> None:
    server = wire(("", 8080))
    print("link-campaign service listening on :8080")  # noqa: T201
    server.serve_forever()


if __name__ == "__main__":
    main()
