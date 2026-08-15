from __future__ import annotations

import tesser.context as ts

import repo.client.client as repo_client
import repo.wiring.wire as repo_wire


class App:  # tessercheck:ignore TB051

    def __init__(self, repo: repo_client.Client) -> None:
        self.repo = repo


@ts.function
def new() -> App:
    return App(repo=repo_wire.build())
