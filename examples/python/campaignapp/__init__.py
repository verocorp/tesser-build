"""The application-service and repository seam for the link-campaign domain.

``CampaignService`` coordinates each use case (convert -> delegate -> persist
-> respond) and holds no business logic of its own — every rule is enforced by
the ``campaign`` package's ``Campaign`` aggregate and its owned ``ShortLink``
entities. ``CampaignRepository`` is the persistence boundary the domain
depends on to load and save a ``Campaign``.

The service's methods speak the public ``linkcampaign`` package's DTOs
directly (rather than a second, service-local set) — so the service
*structurally satisfies* the ``linkcampaign.Client`` Protocol with no adapter
code: every use case here maps 1:1 onto a ``Client`` operation of the same
name (see ``linkcampaignimpl``).
"""

from campaignapp.service import CampaignRepository, CampaignService

__all__ = ["CampaignRepository", "CampaignService"]
