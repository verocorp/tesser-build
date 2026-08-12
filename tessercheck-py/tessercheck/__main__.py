import sys

from tessercheck.adapters.repositories import FilesystemSourceReader
from tessercheck.application.service import TessercheckService
from tessercheck.client.client import CheckRequest


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    response = TessercheckService(FilesystemSourceReader()).check(CheckRequest(root=root))
    for finding in response.findings:
        print(finding)
    return 1 if response.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
