from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignID:

    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("campaign id must not be empty")

    def __str__(self) -> str:
        return self._value
