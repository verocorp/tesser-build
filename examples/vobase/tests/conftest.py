import os
import sys

_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _dir)
while _dir != os.path.dirname(_dir):
    _candidate = os.path.join(_dir, "tesser-py")
    if os.path.isdir(_candidate):
        sys.path.insert(0, _candidate)
        break
    _dir = os.path.dirname(_dir)
