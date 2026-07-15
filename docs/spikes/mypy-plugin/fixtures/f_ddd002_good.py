from dataclasses import dataclass


@dataclass(frozen=True)
class Labels:
    values: tuple[tuple[str, str], ...] = ()  # hashable storage


l = Labels(values=(("a", "b"),))  # valid construction call, PASSING case
