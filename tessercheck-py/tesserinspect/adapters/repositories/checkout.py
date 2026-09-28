import os
import pathlib
import stat
import subprocess

import tesser.adapters as ts

import tesserinspect.application.ports as ports


class GitCheckoutReader(ts.Repository):
    def read_checkout(
        self, read_checkout_request: ports.ReadCheckoutRequest
    ) -> ports.ReadCheckoutResponse:
        root = pathlib.Path(read_checkout_request.repo).resolve(strict=True)
        command = [
            "git",
            "--no-pager",
            "--no-optional-locks",
            "-c",
            f"core.hooksPath={os.devnull}",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-C",
            str(root),
        ]
        result = subprocess.run(
            command + ["rev-parse", "--show-toplevel"],
            capture_output=True,
            check=True,
            timeout=30,
        )
        if pathlib.Path(result.stdout.decode("utf-8").strip()).resolve() != root:
            raise ValueError("repo must name the Git checkout root")
        result = subprocess.run(
            command
            + [
                "config",
                "--name-only",
                "--get-regexp",
                r"^filter\..*\.(clean|smudge|process|required)$",
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode not in {0, 1}:
            raise ValueError("cannot inspect Git filter configuration")
        overrides = []
        for name in result.stdout.decode("utf-8").splitlines():
            overrides.extend(
                ["-c", name + ("=false" if name.endswith(".required") else "=")]
            )
        command[2:2] = overrides
        result = subprocess.run(
            command + ["ls-files", "--stage", "-z"],
            capture_output=True,
            check=True,
            timeout=30,
        )
        if any(entry.startswith(b"160000 ") for entry in result.stdout.split(b"\x00")):
            raise ValueError(
                "submodules are unsupported; inspect each checkout independently"
            )
        if (
            not read_checkout_request.base
            or read_checkout_request.base.startswith("-")
            or "\x00" in read_checkout_request.base
        ):
            raise ValueError("base must be a nonempty commit/ref, not an option")
        result = subprocess.run(
            command
            + [
                "rev-parse",
                "--verify",
                "--end-of-options",
                read_checkout_request.base + "^{commit}",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        baseline = result.stdout.decode("ascii").strip()
        result = subprocess.run(
            command
            + [
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--ignore-submodules=all",
                "--name-status",
                "-z",
                "--find-renames",
                baseline,
                "--",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        fields = result.stdout.decode("utf-8").split("\x00")
        changes = []
        index = 0
        while index < len(fields) - 1:
            status = fields[index]
            path = fields[index + 1]
            previous = ""
            index += 2
            if status.startswith(("R", "C")):
                previous = path
                path = fields[index]
                index += 1
            if status[:1] not in {"A", "M", "D", "R", "T"}:
                raise ValueError(f"unsupported Git change status: {status}")
            changes.append((path, previous, status))
        result = subprocess.run(
            command + ["ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            check=True,
            timeout=30,
        )
        paths = sorted(set(result.stdout.decode("utf-8").split("\x00")) - {""})
        result = subprocess.run(
            command + ["ls-files", "-z", "--others", "--exclude-standard"],
            capture_output=True,
            check=True,
            timeout=30,
        )
        untracked = set(result.stdout.decode("utf-8").split("\x00")) - {""}
        result = subprocess.run(
            command
            + [
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignore-submodules=all",
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        fields = result.stdout.decode("utf-8").split("\x00")
        working_tree_changes = []
        index = 0
        while index < len(fields) - 1:
            staged = fields[index][0]
            unstaged = fields[index][1]
            path = fields[index][3:]
            previous = ""
            index += 1
            if staged in {"R", "C"} or unstaged in {"R", "C"}:
                previous = fields[index]
                index += 1
            if staged == "U" or unstaged == "U" or staged + unstaged in {"AA", "DD"}:
                raise ValueError("unmerged checkout is unsupported")
            working_tree_changes.append((path, previous, staged, unstaged))
        changed_paths = {row[0] for row in changes}
        changes.extend((path, "", "?") for path in sorted(untracked - changed_paths))
        deleted = {path for path, previous, status in changes if status == "D"}
        deleted.update(
            path
            for path, previous, staged, unstaged in working_tree_changes
            if unstaged == "D"
        )
        sources = []
        existing = []
        for path in paths:
            if path in deleted and path not in untracked:
                continue
            parts = pathlib.PurePosixPath(path).parts
            if not parts or ".." in parts or pathlib.PurePosixPath(path).is_absolute():
                raise ValueError("unsupported repository path")
            if not path.endswith(".py") and parts[-1] not in {
                "pytest.ini",
                ".pytest.ini",
                "pyproject.toml",
                "setup.cfg",
                "tox.ini",
            }:
                continue
            descriptors = [os.open(root, os.O_RDONLY | os.O_DIRECTORY)]
            try:
                for part in parts[:-1]:
                    descriptors.append(
                        os.open(
                            part,
                            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptors[-1],
                        )
                    )
                descriptor = os.open(
                    parts[-1],
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=descriptors[-1],
                )
                with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise ValueError(f"unsupported non-regular source: {path}")
                    text = stream.read()
                existing.append(path)
                if path.endswith(".py"):
                    sources.append((path, text))
            finally:
                for descriptor in reversed(descriptors):
                    os.close(descriptor)
        return ports.ReadCheckoutResponse(
            baseline=baseline,
            sources=tuple(sources),
            changes=tuple(sorted(changes)),
            paths=tuple(existing),
            working_tree_changes=tuple(sorted(working_tree_changes)),
        )
