from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUFF_CONFIG = ROOT / "ruff.toml"
IMPORTLINTER_CONFIG = ROOT / ".importlinter"

_HANDLER_IMPORTS = (
    "from campaign.adapters.handlers.http import Handler as CampaignHandler\n"
    "from reports.adapters.handlers.http import Handler as ReportsHandler\n"
)

_PACKAGE_SKELETON = (
    "campaign/__init__.py",
    "campaign/adapters/__init__.py",
    "campaign/adapters/handlers/__init__.py",
    "campaign/adapters/handlers/http.py",
    "campaign/application/__init__.py",
    "campaign/application/service.py",
    "campaign/client.py",
    "reports/__init__.py",
    "reports/adapters/__init__.py",
    "reports/adapters/handlers/__init__.py",
    "reports/adapters/handlers/http.py",
    "reports/client.py",
    "linkpolicy/__init__.py",
    "linkpolicy/application/__init__.py",
    "linkpolicy/application/service.py",
    "bootstrap/__init__.py",
    "srv/__init__.py",
    "srv/http/__init__.py",
    "srv/http/host.py",
    "srv/http/main.py",
)


def _write(root: pathlib.Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _import_graph(root: pathlib.Path, *, violating: bool) -> None:
    for rel in _PACKAGE_SKELETON:
        _write(root, rel, "")
    _write(root, "bootstrap/__init__.py", "from linkpolicy.application import service\n")
    _write(root, "srv/http/main.py", "import bootstrap\n")
    host = _HANDLER_IMPORTS
    if violating:
        host += "from campaign.application.service import CampaignService\n"
        _write(root, "linkpolicy/application/service.py", "from campaign.client import Client\n")
        _write(root, "campaign/client.py", "from reports.client import Client\n")
    _write(root, "srv/http/host.py", host)
    shutil.copy(IMPORTLINTER_CONFIG, root / ".importlinter")


def _ruff(target: pathlib.Path) -> subprocess.CompletedProcess[str]:
    shutil.copy(RUFF_CONFIG, target / "ruff.toml")
    return subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format", "concise", "."],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )


def _lint_imports(target: pathlib.Path) -> subprocess.CompletedProcess[str]:
    executable = pathlib.Path(sys.executable).parent / "lint-imports"
    resolved = str(executable) if executable.is_file() else shutil.which("lint-imports")
    assert resolved, "lint-imports is not installed — the import contracts are not being enforced"
    return subprocess.run(
        [resolved],
        cwd=target,
        env={"PYTHONPATH": str(target)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_ruff_config_flags_env_reads_and_exits_below_the_edge(tmp_path: pathlib.Path) -> None:
    _write(
        tmp_path,
        "campaign/wiring/wire.py",
        "import os\nimport sys\n\n\ndef wire() -> None:\n"
        "    os.getenv('CAMPAIGN_STORAGE')\n"
        "    os.environ['CAMPAIGN_STORAGE']\n"
        "    sys.exit(1)\n"
        "    os._exit(1)\n"
        "    exit(1)\n",
    )
    result = _ruff(tmp_path)
    assert result.returncode == 1, result.stdout
    flagged = [line for line in result.stdout.splitlines() if line.startswith("campaign/")]
    assert [line.split(" ")[1] for line in flagged] == [
        "TID251",
        "TID251",
        "TID251",
        "TID251",
        "PLR1722",
    ], result.stdout


def test_ruff_config_lifts_the_bans_only_at_the_host_edge(tmp_path: pathlib.Path) -> None:
    edge = "import os\nimport sys\n\n\ndef main() -> None:\n    os.getenv('X')\n    sys.exit(0)\n"
    _write(tmp_path, "srv/http/main.py", edge)
    _write(tmp_path, "srv/http/host.py", edge)
    result = _ruff(tmp_path)
    assert result.returncode == 1, result.stdout
    assert "srv/http/main.py" not in result.stdout
    assert result.stdout.count("srv/http/host.py") == 2, result.stdout


def test_ruff_config_never_lifts_the_bare_exit_ban(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "srv/http/main.py", "def main() -> None:\n    exit(1)\n    quit(1)\n")
    result = _ruff(tmp_path)
    assert result.returncode == 1, result.stdout
    assert result.stdout.count("PLR1722") == 2, result.stdout


def test_import_contracts_break_on_a_host_reaching_past_handlers(tmp_path: pathlib.Path) -> None:
    _import_graph(tmp_path, violating=True)
    result = _lint_imports(tmp_path)
    assert result.returncode == 1, result.stdout
    assert "Contracts: 0 kept, 3 broken." in result.stdout, result.stdout
    assert "srv.http.host -> campaign.application.service" in result.stdout
    assert "linkpolicy.application.service -> campaign.client" in result.stdout
    assert "campaign.client -> reports.client" in result.stdout


def test_import_contracts_allow_a_host_reaching_a_context_through_bootstrap(
    tmp_path: pathlib.Path,
) -> None:
    _import_graph(tmp_path, violating=False)
    result = _lint_imports(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "Contracts: 3 kept, 0 broken." in result.stdout, result.stdout
