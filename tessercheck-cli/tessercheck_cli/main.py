from __future__ import annotations

import sys
from typing import Final

import tessercheck.client as client
import tessercheck.component as component

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
    tessercheck = component.Tessercheck(component.Config(component.Spec()))
    try:
        check_response = tessercheck.client.check(client.CheckRequest(tree=tree))
    finally:
        tessercheck.close()
    for finding in check_response.findings:
        print(finding)
    return 1 if check_response.findings else 0
