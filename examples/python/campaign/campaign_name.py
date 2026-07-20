from dataclasses import dataclass

from serialization import canonical_str


@dataclass(frozen=True)
class CampaignName:

    _value: str

    def __post_init__(self) -> None:
        if not self._value.strip():
            raise ValueError("campaign name must not be empty")

    def __str__(self) -> str:
        return canonical_str(self._value)
