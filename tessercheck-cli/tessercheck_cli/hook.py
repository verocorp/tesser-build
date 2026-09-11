from __future__ import annotations

import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
import typing

import tessercheck.client as client
import tessercheck.component as component

_USAGE: typing.Final[str] = "usage: tessercheck-hook  (reads a Claude Code PostToolUse event on stdin)"

_WORKER: typing.Final[str] = "--worker"

_SKILL_DIR: typing.Final[str] = ".claude/skills/tesser-build"

_SKILL_NAME: typing.Final[str] = "tesser-build"

_STATE_DIR: typing.Final[str] = ".tesser"

_CONF_FILE: typing.Final[str] = "hook.conf"

_LOG_FILE: typing.Final[str] = "changes.jsonl"

_SESSIONS_DIR: typing.Final[str] = "sessions"

_DECLARATION: typing.Final[str] = ".tesser-root"

_BUDGET_ENV: typing.Final[str] = "TESSERCHECK_HOOK_BUDGET"

_DEFAULT_BUDGET_SECONDS: typing.Final[float] = 15.0

_PRUNE_AFTER_SECONDS: typing.Final[float] = 7 * 24 * 3600

_WRITE_TOOLS: typing.Final[frozenset[str]] = frozenset({"Edit", "Write", "MultiEdit"})

_SKILL_KEYS: typing.Final[tuple[str, ...]] = ("skill", "name", "skill_name", "command")

_PREAMBLE: typing.Final[str] = (
    "tessercheck: findings on the file just written. A sibling file you have not "
    "written yet (a test, a fake, a package __init__) is a finding until it exists; "
    "finish the change, then fix what remains."
)


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    if args[:1] == [_WORKER]:
        return _worker(args[1:])
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except ValueError:
        return 0
    if not isinstance(event, dict):
        return 0
    tool = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    cwd = pathlib.Path(str(event.get("cwd") or os.getcwd()))
    session = str(event.get("session_id") or "unknown")
    if tool == "Skill":
        return _note_skill(cwd, session, tool_input)
    if tool == "Read":
        return _note_read(cwd, session, str(tool_input.get("file_path") or ""))
    if tool in _WRITE_TOOLS:
        return _post_write(cwd, session, str(tool_input.get("file_path") or ""))
    return 0


def _worker(args: list[str]) -> int:
    if len(args) != 2:
        print(_USAGE, file=sys.stderr)
        return 2
    tree, path = args
    conf = sys.stdin.read()
    tessercheck = component.Tessercheck(component.Config(component.Spec()))
    try:
        hook_response = tessercheck.client.hook(client.HookRequest(tree=tree, path=path, conf=conf))
    finally:
        tessercheck.close()
    print(json.dumps({
        "governance": hook_response.governance,
        "mode": hook_response.mode,
        "action": hook_response.action,
        "findings": list(hook_response.findings),
        "codes": list(hook_response.codes),
    }))
    return 0


def _note_skill(cwd: pathlib.Path, session: str, tool_input: dict[str, object]) -> int:
    named = " ".join(str(tool_input.get(key) or "") for key in _SKILL_KEYS)
    if _SKILL_NAME in named:
        _append_session(cwd, session, "skill", _SKILL_NAME)
    return 0


def _note_read(cwd: pathlib.Path, session: str, file_path: str) -> int:
    if not file_path:
        return 0
    read = pathlib.Path(file_path)
    if not read.is_absolute():
        read = cwd / read
    skill_dir = cwd / _SKILL_DIR
    try:
        relative = read.resolve().relative_to(skill_dir.resolve())
    except ValueError:
        return 0
    _append_session(cwd, session, "read", relative.as_posix())
    return 0


def _post_write(cwd: pathlib.Path, session: str, file_path: str) -> int:
    started = time.monotonic()
    if not file_path.endswith(".py"):
        return 0
    written = pathlib.Path(file_path)
    if not written.is_absolute():
        written = cwd / written
    tree = _tree_of(written, cwd)
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    line: dict[str, object] = {
        "actor": _actor(cwd),
        "session_id": session,
        "ts": stamp,
        "relpath": _relative(written, tree if tree is not None else cwd),
        "source": "write",
        "placement": "outside",
        "findings": [],
        "findings_count": 0,
        "mode": "advisory",
        "guidance": _guidance(cwd, session),
        "status": "ok",
        "exit_code": 0,
        "duration_ms": 0,
    }
    exit_code = 0
    stdout = ""
    stderr = ""
    if tree is not None:
        relpath = _relative(written, tree)
        conf = _conf(cwd)
        line["mode"] = _mode_of(conf)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "tessercheck_cli.hook", _WORKER, str(tree), relpath],
                input=conf,
                capture_output=True,
                text=True,
                timeout=_budget(),
                check=False,
            )
            if result.returncode != 0:
                line["status"] = "error"
            else:
                answer = json.loads(result.stdout)
                findings = [str(item) for item in answer["findings"]]
                codes = [str(item) for item in answer["codes"]]
                line["placement"] = str(answer["governance"])
                line["mode"] = str(answer["mode"])
                line["findings"] = [f"{code}:{relpath}" for code in codes]
                line["findings_count"] = len(findings)
                action = str(answer["action"])
                if action == "advise":
                    stdout = json.dumps({
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "additionalContext": _advisory(relpath, findings),
                        }
                    })
                elif action == "feedback":
                    stderr = _PREAMBLE + "\n" + "\n".join(findings)
                    exit_code = 2
                elif action == "disabled":
                    line["status"] = "disabled"
        except subprocess.TimeoutExpired:
            line["status"] = "timeout"
        except (ValueError, KeyError, TypeError, OSError):
            line["status"] = "error"
    line["exit_code"] = exit_code
    line["duration_ms"] = int((time.monotonic() - started) * 1000)
    _append_log(cwd, line)
    _prune_sessions(cwd)
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    return exit_code


def _tree_of(written: pathlib.Path, cwd: pathlib.Path) -> pathlib.Path | None:
    here = written.parent
    root = cwd.resolve()
    while True:
        if (here / _DECLARATION).exists():
            return here
        if here.resolve() == root or here.parent == here:
            return None
        here = here.parent


def _relative(written: pathlib.Path, base: pathlib.Path) -> str:
    try:
        return written.relative_to(base).as_posix()
    except ValueError:
        return written.as_posix()


def _conf(cwd: pathlib.Path) -> str:
    try:
        return (cwd / _STATE_DIR / _CONF_FILE).read_text(encoding="utf-8")
    except OSError:
        return ""


def _mode_of(conf: str) -> str:
    mode = "advisory"
    enabled = True
    for raw in conf.splitlines():
        key, _, value = raw.strip().partition("=")
        key = key.strip()
        value = value.strip()
        if key == "mode" and value in ("advisory", "feedback"):
            mode = value
        elif key == "enabled" and value in ("true", "false"):
            enabled = value == "true"
    return mode if enabled else "disabled"


def _budget() -> float:
    try:
        return float(os.environ.get(_BUDGET_ENV, _DEFAULT_BUDGET_SECONDS))
    except ValueError:
        return _DEFAULT_BUDGET_SECONDS


def _actor(cwd: pathlib.Path) -> str:
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    email = result.stdout.strip()
    return email if result.returncode == 0 and email else "unknown"


def _advisory(relpath: str, findings: list[str]) -> str:
    count = len(findings)
    noun = "finding" if count == 1 else "findings"
    return f"tessercheck: {count} {noun} on {relpath}\n" + "\n".join(findings)


def _sessions(cwd: pathlib.Path) -> pathlib.Path:
    return cwd / _STATE_DIR / _SESSIONS_DIR


def _append_session(cwd: pathlib.Path, session: str, via: str, path: str) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    _append(_sessions(cwd) / f"{session}.jsonl", {"ts": stamp, "via": via, "path": path})


def _guidance(cwd: pathlib.Path, session: str) -> list[str]:
    seen: dict[str, None] = {}
    try:
        text = (_sessions(cwd) / f"{session}.jsonl").read_text(encoding="utf-8")
    except OSError:
        return []
    for raw in text.splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if isinstance(event, dict):
            seen[f"{event.get('via', '?')}:{event.get('path', '?')}"] = None
    return list(seen)


def _prune_sessions(cwd: pathlib.Path) -> None:
    sessions = _sessions(cwd)
    try:
        entries = list(sessions.iterdir())
    except OSError:
        return
    cutoff = time.time() - _PRUNE_AFTER_SECONDS
    for entry in entries:
        try:
            if entry.suffix == ".jsonl" and entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:
            continue


def _append_log(cwd: pathlib.Path, line: dict[str, object]) -> None:
    _append(cwd / _STATE_DIR / _LOG_FILE, line)


def _append(target: pathlib.Path, record: dict[str, object]) -> None:
    payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    except OSError:
        return
    try:
        os.write(handle, payload)
    except OSError:
        return
    finally:
        os.close(handle)


if __name__ == "__main__":
    raise SystemExit(main())
