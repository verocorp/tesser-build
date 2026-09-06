import pathlib

import tesser.adapters as ts

import tessercheck.application.ports as ports


class FilesystemRulebookSources(ts.Repository):

    def read(
        self, read_rulebook_request: ports.ReadRulebookRequest
    ) -> ports.ReadRulebookResponse:
        base = pathlib.Path(read_rulebook_request.tree)
        modules = [
            base / "tessercheck" / "tests" / "test_checks.py",
            *sorted((base / "tessercheck" / "domain").glob("test_*.py")),
        ]
        return ports.ReadRulebookResponse(
            checks_text=(base / "tessercheck" / "domain" / "checks.py").read_text(
                encoding="utf-8"
            ),
            test_modules=tuple(
                ports.TestModuleText(
                    name=str(path.relative_to(base)),
                    text=path.read_text(encoding="utf-8"),
                )
                for path in modules
            ),
            contracts_text=(base / ".importlinter").read_text(encoding="utf-8"),
        )
