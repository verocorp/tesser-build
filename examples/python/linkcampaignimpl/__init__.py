"""The concrete link-campaign implementation: an in-memory
``campaignapp.CampaignRepository``, and the ``new_client`` seam that composes
the application service behind the public ``linkcampaign.Client``. This
package is imported from exactly one place in the example — the composition
root (``main.py``) — the only site that chooses it over some other
implementation.
"""

from linkcampaignimpl.client import new_client
from linkcampaignimpl.memory_repo import InMemoryCampaignRepository

__all__ = ["InMemoryCampaignRepository", "new_client"]
