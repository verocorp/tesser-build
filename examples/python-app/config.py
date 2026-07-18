"""The single env edge: the ONE place that knows environment variables exist.

``from_env`` is a shared pure decoder (env-lookup passed in) producing the nested
application ``Config`` every host shares; ``http_addr_from_env`` decodes the
http host's OWN launch config. Host ``main``s CALL these — they never touch the
environment themselves, and ``bootstrap.new`` never reads it. This keeps env access
to one auditable spot (enforced by the self-enforcement test) and closes the
per-host-drift and hidden-env-read holes.

A real service would resolve secret *references* (Vault/AWS/GCP) here too; that
launch-time loader is a legitimate host-side concern, deliberately not built.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from bootstrap.config import Config
from campaign.wiring.config import Config as CampaignConfig
from linkpolicy.wiring.config import Config as LinkPolicyConfig

Getenv = Callable[[str], "str | None"]


def _os_getenv(key: str) -> str | None:
    return os.environ.get(key)


def from_env(getenv: Getenv = _os_getenv) -> Config:
    """Decode the nested application config. A missing coordinate stays empty and
    ``bootstrap`` fails fast on it — it never defaults to volatile storage."""
    return Config(
        campaign=CampaignConfig(storage=getenv("CAMPAIGN_STORAGE") or ""),
        linkpolicy=LinkPolicyConfig(storage=getenv("LINKPOLICY_STORAGE") or ""),
    )


def http_addr_from_env(getenv: Getenv = _os_getenv) -> tuple[str, int]:
    """The http host's own launch config — decoded here, not scattered in main."""
    return (getenv("HTTP_HOST") or "", int(getenv("HTTP_PORT") or "8080"))
