"""Vercel ASGI entrypoint for the prediction API and web UI.

Vercel discovers a top-level FastAPI instance named ``app`` in this file and
runs it as a single Python serverless function. Application logic stays in
``used_car_price_intelligence.api.app``; this module only exposes that ASGI app.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from used_car_price_intelligence.api.app import app as app

__all__ = ["app"]
