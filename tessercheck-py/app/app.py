from __future__ import annotations

import tesser.app as ts

import tessercheck.component.component as tessercheck_component

import app.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        self.tessercheck = tessercheck_component.Tessercheck(cfg.tessercheck)

    def close(self) -> None:
        self.tessercheck.close()
