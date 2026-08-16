from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

from tests.support import ROOT


def test_ruff_config_flags_env_reads_and_exits_below_the_edge(tmp_path: pathlib.Path) -> None:
    shutil.copy(ROOT / "ruff.toml", tmp_path / "ruff.toml")
    offender = tmp_path / "campaign" / "wiring" / "wire.py"
    offender.parent.mkdir(parents=True)
    offender.write_text(
        "import os\nimport sys\n\n\ndef wire() -> None:\n"
        "    os.getenv('CAMPAIGN_STORAGE')\n"
        "    os.environ['CAMPAIGN_STORAGE']\n"
        "    sys.exit(1)\n"
        "    os._exit(1)\n"
        "    exit(1)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format", "concise", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
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
    shutil.copy(ROOT / "ruff.toml", tmp_path / "ruff.toml")
    edge = "import os\nimport sys\n\n\ndef main() -> None:\n    os.getenv('X')\n    sys.exit(0)\n"
    (tmp_path / "srv" / "http").mkdir(parents=True)
    (tmp_path / "srv" / "http" / "main.py").write_text(edge, encoding="utf-8")
    (tmp_path / "srv" / "http" / "host.py").write_text(edge, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format", "concise", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout
    assert "srv/http/main.py" not in result.stdout
    assert result.stdout.count("srv/http/host.py") == 2, result.stdout


def test_ruff_config_lifts_the_env_ban_only_at_the_loader(tmp_path: pathlib.Path) -> None:
    shutil.copy(ROOT / "ruff.toml", tmp_path / "ruff.toml")
    read = "import os\n\n\ndef get() -> None:\n    os.environ['X']\n"
    (tmp_path / "bootstrap").mkdir(parents=True)
    (tmp_path / "bootstrap" / "loader.py").write_text(read, encoding="utf-8")
    (tmp_path / "bootstrap" / "repository.py").write_text(read, encoding="utf-8")
    (tmp_path / "bootstrap" / "app.py").write_text(read, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format", "concise", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout
    assert "bootstrap/loader.py" not in result.stdout
    assert result.stdout.count("bootstrap/repository.py") == 1, result.stdout
    assert result.stdout.count("bootstrap/app.py") == 1, result.stdout


def test_ruff_config_never_lifts_the_bare_exit_ban(tmp_path: pathlib.Path) -> None:
    shutil.copy(ROOT / "ruff.toml", tmp_path / "ruff.toml")
    (tmp_path / "srv" / "http").mkdir(parents=True)
    (tmp_path / "srv" / "http" / "main.py").write_text(
        "def main() -> None:\n    exit(1)\n    quit(1)\n", encoding="utf-8"
    )
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format", "concise", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout
    assert result.stdout.count("PLR1722") == 2, result.stdout


def test_import_contracts_break_on_a_host_reaching_past_handlers(tmp_path: pathlib.Path) -> None:
    shutil.copy(ROOT / ".importlinter", tmp_path / ".importlinter")
    for rel in (
        "campaign/__init__.py",
        "campaign/adapters/__init__.py",
        "campaign/adapters/handlers/__init__.py",
        "campaign/adapters/handlers/http.py",
        "campaign/application/__init__.py",
        "campaign/application/service.py",
        "reports/__init__.py",
        "reports/adapters/__init__.py",
        "reports/adapters/handlers/__init__.py",
        "reports/adapters/handlers/http.py",
        "reports/client.py",
        "linkpolicy/__init__.py",
        "linkpolicy/application/__init__.py",
        "srv/__init__.py",
        "kernel/__init__.py",
        "srv/http/__init__.py",
    ):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("", encoding="utf-8")
    (tmp_path / "bootstrap").mkdir()
    (tmp_path / "bootstrap" / "__init__.py").write_text("import linkpolicy\n", encoding="utf-8")
    (tmp_path / "srv" / "http" / "main.py").write_text("import bootstrap\n", encoding="utf-8")
    (tmp_path / "srv" / "http" / "host.py").write_text(
        "from campaign.adapters.handlers.http import Handler as CampaignHandler\n"
        "from reports.adapters.handlers.http import Handler as ReportsHandler\n"
        "from campaign.application.service import CampaignService\n",
        encoding="utf-8",
    )
    (tmp_path / "linkpolicy" / "application" / "service.py").write_text(
        "from campaign.client import Client\n", encoding="utf-8"
    )
    (tmp_path / "campaign" / "client.py").write_text(
        "from reports.client import Client\n", encoding="utf-8"
    )
    executable = pathlib.Path(sys.executable).parent / "lint-imports"
    resolved = str(executable) if executable.is_file() else shutil.which("lint-imports")
    assert resolved, "lint-imports is not installed — the import contracts are not being enforced"
    result = subprocess.run(
        [resolved],
        cwd=tmp_path,
        env={"PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout
    assert "Contracts: 1 kept, 3 broken." in result.stdout, result.stdout
    assert "srv.http.host -> campaign.application.service" in result.stdout
    assert "linkpolicy.application.service -> campaign.client" in result.stdout
    assert "campaign.client -> reports.client" in result.stdout


def test_import_contracts_allow_a_host_reaching_a_context_through_bootstrap(
    tmp_path: pathlib.Path,
) -> None:
    shutil.copy(ROOT / ".importlinter", tmp_path / ".importlinter")
    for rel in (
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
        "srv/__init__.py",
        "kernel/__init__.py",
        "srv/http/__init__.py",
    ):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("", encoding="utf-8")
    (tmp_path / "bootstrap").mkdir()
    (tmp_path / "bootstrap" / "__init__.py").write_text("import linkpolicy\n", encoding="utf-8")
    (tmp_path / "srv" / "http" / "main.py").write_text("import bootstrap\n", encoding="utf-8")
    (tmp_path / "srv" / "http" / "host.py").write_text(
        "from campaign.adapters.handlers.http import Handler as CampaignHandler\n"
        "from reports.adapters.handlers.http import Handler as ReportsHandler\n",
        encoding="utf-8",
    )
    executable = pathlib.Path(sys.executable).parent / "lint-imports"
    resolved = str(executable) if executable.is_file() else shutil.which("lint-imports")
    assert resolved, "lint-imports is not installed — the import contracts are not being enforced"
    result = subprocess.run(
        [resolved],
        cwd=tmp_path,
        env={"PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert "Contracts: 4 kept, 0 broken." in result.stdout, result.stdout
