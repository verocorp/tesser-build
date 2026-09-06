from __future__ import annotations

import tesser.app as ts

import tessercheck.component as component


class Spec(ts.Spec):

    def __init__(self, tessercheck: component.Config) -> None:
        self.tessercheck = tessercheck


class AppConfig(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.tessercheck = spec.tessercheck
