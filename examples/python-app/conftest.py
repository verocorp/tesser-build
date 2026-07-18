"""Put examples/python-app on sys.path so the app's top-level packages
(campaign, linkpolicy, reports, bootstrap, srv, errors) import cleanly
under pytest without any install step — plain venv, no packaging.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
