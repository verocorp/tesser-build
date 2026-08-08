from pathlib import Path

import tesser.adapters as ts


class FilesystemSourceReader(ts.Repository):

    def sources(self, root: str) -> tuple[tuple[str, str, bool], ...]:
        found: list[tuple[str, str, bool]] = []
        for path in sorted(Path(root).rglob("*.py")):
            parts = list(path.relative_to(root).with_suffix("").parts)
            is_package = bool(parts) and parts[-1] == "__init__"
            if is_package:
                parts = parts[:-1]
            if not parts:
                continue
            found.append((".".join(parts), path.read_text(), is_package))
        return tuple(found)
