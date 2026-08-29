from __future__ import annotations

import tesser.app as ts

import ordering.component.config as ordering_config


class Spec(ts.Spec):

    def __init__(self, ordering: ordering_config.Config) -> None:
        self.ordering = ordering


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        self.ordering = spec.ordering
