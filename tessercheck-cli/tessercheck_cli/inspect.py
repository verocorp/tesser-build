import sys

import srv.cli as cli


def main() -> int:
    return cli.InspectHost().run(sys.argv[1:])
