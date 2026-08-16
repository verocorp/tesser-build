from __future__ import annotations

import tesser.app as ts

import tessercheck.wiring.wire as tessercheck_wire

import bootstrap.config as config


class App(ts.App):

    def __init__(self, cfg: config.Config) -> None:
        self.tessercheck = tessercheck_wire.Tessercheck(cfg.tessercheck)

    def close(self) -> None:
        self.tessercheck.close()
