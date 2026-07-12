from campaignapp import CampaignService
from linkcampaign import Client


def new_client(svc: CampaignService) -> Client:
    """Compose ``svc`` behind the public ``linkcampaign.Client``.

    In Go the concrete client *embeds* the application service so its methods
    are promoted and the contract is satisfied with zero forwarding code. In
    Python the equivalent is *structural typing*: ``CampaignService`` already
    has exactly the four methods ``Client`` declares, taking and returning the
    public package's DTOs, so it satisfies the Protocol directly — no wrapper
    is needed in this single-service, 1:1 case, and simply returning it is
    enough.

    The ``-> Client`` return annotation is the compile-time proof (mypy's
    analog of Go's ``var _ linkcampaign.Client = (*client)(nil)``): if a
    service method's signature drifts from the Protocol, this stops type
    checking.

    When you need to *reshape* the public surface — rename methods, expose a
    subset, or compose several internal services/processes into one contract
    (the decoupling boundary's real purpose) — write an explicit class here
    that holds those components and delegates. This example stays 1:1, so it
    doesn't need one.
    """
    return svc
