from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import tesser.context as ts

import tessercheck.wiring.config as config


@dataclass(frozen=True)
class Config:  # tessercheck:ignore TB051
    tessercheck: config.Config = field(default_factory=config.Config)


@ts.function
def from_env(getenv: Callable[[str], Optional[str]]) -> Config:
    return Config(tessercheck=config.Config())
