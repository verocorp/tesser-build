from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest


def test_the_edge_announces_its_address_and_exits_zero_when_signalled() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {
        "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry),
        "PYTHONUNBUFFERED": "1",
        "CAMPAIGN_STORAGE": "memory",
        "LINKPOLICY_STORAGE": "memory",
        "HTTP_HOST": "127.0.0.1",
        "HTTP_PORT": "0",
    }
    with subprocess.Popen(
        [sys.executable, "-m", "srv.http.main"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        assert proc.stdout is not None
        banner = proc.stdout.readline()
        assert banner.strip() == "campaign+linkpolicy app listening on 127.0.0.1:0"
        with pytest.raises(subprocess.TimeoutExpired):
            proc.wait(timeout=1)
        proc.terminate()
        stderr = proc.communicate(timeout=30)[1]
    assert proc.returncode == 0
    assert stderr == ""


def test_the_edge_refuses_to_start_without_its_storage_coordinate() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {
        "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry),
        "PYTHONUNBUFFERED": "1",
        "HTTP_HOST": "127.0.0.1",
        "HTTP_PORT": "0",
    }
    with subprocess.Popen(
        [sys.executable, "-m", "srv.http.main"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        stdout, stderr = proc.communicate(timeout=30)
    assert proc.returncode != 0
    assert stdout == ""
    assert "missing_coordinate" in stderr


def test_the_edge_refuses_to_start_on_an_unreadable_port() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {
        "PYTHONPATH": os.pathsep.join(entry for entry in sys.path if entry),
        "PYTHONUNBUFFERED": "1",
        "CAMPAIGN_STORAGE": "memory",
        "LINKPOLICY_STORAGE": "memory",
        "HTTP_PORT": "eighty",
    }
    with subprocess.Popen(
        [sys.executable, "-m", "srv.http.main"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        stdout, stderr = proc.communicate(timeout=30)
    assert proc.returncode != 0
    assert stdout == ""
    assert "bad_http_port" in stderr
