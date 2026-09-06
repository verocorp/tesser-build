from __future__ import annotations

import tesser.app as ts

import tessercheck.component as component

import app.config as config


class TessercheckApp(ts.App):

    def __init__(self, app_config: config.AppConfig) -> None:
        self.tessercheck = component.Tessercheck(app_config.tessercheck)

    def close(self) -> None:
        self.tessercheck.close()
