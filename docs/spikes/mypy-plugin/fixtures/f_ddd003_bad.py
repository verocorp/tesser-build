from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:
    value: str

    def normalize(self) -> None:
        # mutating a frozen instance after construction -- DDD003
        object.__setattr__(self, "value", self.value.lower())


s = Slug(value="X")  # valid construction call -- must still typecheck
