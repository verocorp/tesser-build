from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:
    value: str

    def __post_init__(self) -> None:
        # canonicalization on the construction path is the sanctioned use
        object.__setattr__(self, "value", self.value.lower())
