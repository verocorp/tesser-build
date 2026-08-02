from pathlib import Path

import tesser.adapters as ts


class FilesystemSourceReader(ts.Repository):

    def sources(self, root: str) -> tuple[tuple[str, str], ...]:
        found: list[tuple[str, str]] = []
        for path in sorted(Path(root).rglob("*.py")):
            parts = list(path.relative_to(root).with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            if not parts:
                continue
            found.append((".".join(parts), path.read_text()))
        return tuple(found)
