from dataclasses import dataclass


@dataclass(frozen=True)
class Labels:
    values: dict[str, str]  # mutable collection field -- DDD002


l = Labels(values={"a": "b"})  # valid construction call -- must still typecheck
