from __future__ import annotations

import sys
from typing import Final

import tessercheck.client.client as client
import tessercheck.component.component as component
import tessercheck.component.config as config

_USAGE: Final[str] = "usage: tessercheck-check [tree]"

_HERE: Final[str] = "."

_HELP: Final[frozenset[str]] = frozenset({"-h", "--help"})


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in _HELP:
        print(_USAGE)
        return 0
    if len(args) > 1:
        print(f"unexpected extra arguments\n{_USAGE}", file=sys.stderr)
        return 2
    tree = args[0] if args else _HERE
    checker = component.Tessercheck(config.Config(config.Spec()))
    try:
        view = checker.client.check(client.CheckRequest(tree=tree))
    finally:
        checker.close()
    for finding in view.findings:
        print(finding)
    return 1 if view.findings else 0
