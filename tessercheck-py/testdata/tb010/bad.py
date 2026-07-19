from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    _amount: str
    currency: str

    def __str__(self) -> str:
        return f"{self._amount} {self.currency}"
