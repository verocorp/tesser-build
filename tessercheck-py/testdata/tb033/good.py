from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignSpec:
    id: str
    name: str


class Repository:

    def __init__(self) -> None:
        self._store: dict[str, CampaignSpec] = {}

    def save(self, spec: CampaignSpec) -> None:
        self._store[spec.id] = spec

    def load(self, id: str) -> CampaignSpec:
        return self._store[id]


def describe(spec: CampaignSpec) -> str:
    return f"{spec.name} ({spec.id})"


def identity_of(spec: CampaignSpec) -> int:
    return id(spec)


def summarize(items: list[str], format: str = "csv") -> str:
    joined = ", " if format == "csv" else " "
    return joined.join(items)


def count_links(links: list[str]) -> int:
    return len(links)
