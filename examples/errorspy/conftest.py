"""Put examples/errorspy on sys.path so the example's top-level modules import
cleanly under pytest without any install step — plain venv, no packaging.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
