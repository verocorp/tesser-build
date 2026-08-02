from pathlib import Path

import tesser.adapters as ts

from sigcheck.domain import Module


class FilesystemSourceReader(ts.Repository):

    def modules(self, root: str) -> tuple[Module, ...]:
        found: list[Module] = []
        for path in sorted(Path(root).rglob("*.py")):
            parts = list(path.relative_to(root).with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            if not parts:
                continue
            found.append(Module(".".join(parts), path.read_text()))
        return tuple(found)
