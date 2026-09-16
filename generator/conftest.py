import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _root)
_candidate = os.path.abspath(os.path.join(_root, "..", "tesser-py"))
if not os.path.isdir(_candidate):
    raise RuntimeError(f"no tesser-py at ../ from {_root}")
sys.path.insert(0, _candidate)
