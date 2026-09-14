from __future__ import annotations

import sys
from typing import Final

import tessercheck.client as client
import tessercheck.component as component

_USAGE: Final[str] = "usage: tessercheck-rename [tree]"

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
        apply_renames_response = tessercheck.client.apply_renames(client.ApplyRenamesRequest(tree=tree))
    finally:
        tessercheck.close()
    print(f"renamed {apply_renames_response.files} file(s)")
    if apply_renames_response.remaining:
        print(f"{len(apply_renames_response.remaining)} finding(s) this cannot repair:")
        for finding in apply_renames_response.remaining:
            print(finding)
    return 1 if apply_renames_response.remaining else 0
