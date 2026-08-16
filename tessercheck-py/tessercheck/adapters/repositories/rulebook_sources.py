from pathlib import Path

import tesser.adapters as ts

import tessercheck.application.ports.rulebook_sources as rulebook_sources


class FilesystemRulebookSources(ts.Repository):

    def read(
        self, request: rulebook_sources.ReadRulebookRequest
    ) -> rulebook_sources.ReadRulebookResponse:
        base = Path(request.root)
        modules = [
            base / "tessercheck" / "tests" / "test_checks.py",
            *sorted((base / "tessercheck" / "domain").glob("test_*.py")),
        ]
        return rulebook_sources.ReadRulebookResponse(
            checks_text=(base / "tessercheck" / "domain" / "checks.py").read_text(
                encoding="utf-8"
            ),
            test_modules=tuple(
                rulebook_sources.TestModuleText(
                    name=str(path.relative_to(base)),
                    text=path.read_text(encoding="utf-8"),
                )
                for path in modules
            ),
            contracts_text=(base / ".importlinter").read_text(encoding="utf-8"),
        )
