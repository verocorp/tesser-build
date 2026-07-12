from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignName:
    """The marketing team's name for a Campaign. Simple, single-value value
    object: one field, native equality.

    The rules given for this feature don't say anything about the shape of a
    campaign's name beyond "a name" — the simplest rule that fits the skill's
    primitive-obsession guidance (the value is domain-meaningful and gets a
    validation rule) is "non-empty". Noted here since the skill left this
    specific rule uncovered.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("campaign name must not be empty")

    def __str__(self) -> str:
        return self.value
