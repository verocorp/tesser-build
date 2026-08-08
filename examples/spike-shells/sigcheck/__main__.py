import sys

from sigcheck.adapters.repositories import FilesystemSourceReader
from sigcheck.application.service import SigcheckService
from sigcheck.client.client import CheckRequest


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    response = SigcheckService(FilesystemSourceReader()).check(CheckRequest(root=root))
    for finding in response.findings:
        print(finding)
    return 1 if response.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
