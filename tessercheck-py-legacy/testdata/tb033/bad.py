from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignSpec:
    id: str
    name: str


def fingerprint(spec: CampaignSpec, id: str) -> str:
    return f"{id}-{id(spec)}"


def label(spec: CampaignSpec) -> str:
    format = "{0}"
    return format(spec.name)


def widest(names: list[str]) -> int:
    len = 0
    for name in names:
        len = max(len, len(name))
    return len


async def digest(spec: CampaignSpec, hash: str) -> str:
    return f"{hash}-{hash(spec.id)}"
