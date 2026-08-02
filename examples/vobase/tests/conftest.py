import os
import sys

_start = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _start)
_dir = _start
while True:
    _candidate = os.path.join(_dir, "tesser-py")
    if os.path.isdir(_candidate):
        sys.path.insert(0, _candidate)
        break
    _parent = os.path.dirname(_dir)
    if _parent == _dir:
        raise RuntimeError(f"no tesser-py directory found above {_start}")
    _dir = _parent
