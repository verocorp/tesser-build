from dataclasses import dataclass


@dataclass(frozen=True)
class TargetURL:
    """The URL a ShortLink redirects to. Simple, single-value value object:
    one field, native equality (one representation per value).
    """

    value: str

    def __post_init__(self) -> None:
        if not (self.value.startswith("http://") or self.value.startswith("https://")):
            raise ValueError(
                f"invalid target URL {self.value!r}: must start with "
                "http:// or https://"
            )

    def __str__(self) -> str:
        return self.value
