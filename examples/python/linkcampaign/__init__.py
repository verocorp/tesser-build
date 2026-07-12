"""Public contract for the link-campaign component. Re-exports the ``Client``
Protocol and its DTOs so callers import them from ``linkcampaign`` directly.
"""

from linkcampaign.client import (
    AddShortLinkRequest,
    AddShortLinkResponse,
    Client,
    CreateCampaignRequest,
    CreateCampaignResponse,
    DeactivateShortLinkRequest,
    DeactivateShortLinkResponse,
    GetCampaignRequest,
    GetCampaignResponse,
    ShortLinkInput,
    ShortLinkView,
)

__all__ = [
    "AddShortLinkRequest",
    "AddShortLinkResponse",
    "Client",
    "CreateCampaignRequest",
    "CreateCampaignResponse",
    "DeactivateShortLinkRequest",
    "DeactivateShortLinkResponse",
    "GetCampaignRequest",
    "GetCampaignResponse",
    "ShortLinkInput",
    "ShortLinkView",
]
