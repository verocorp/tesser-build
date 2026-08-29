from __future__ import annotations

import tesser.app as ts

import ordering.component.component as ordering_component

import app.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        self.ordering = ordering_component.Ordering(cfg.ordering)

    def close(self) -> None:
        self.ordering.close()
