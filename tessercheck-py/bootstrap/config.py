from __future__ import annotations

import tesser.app as ts

import tessercheck.wiring.config as config


class Spec(ts.Spec):

    def __init__(self, tessercheck: config.Config) -> None:
        self.tessercheck = tessercheck


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.tessercheck = spec.tessercheck
