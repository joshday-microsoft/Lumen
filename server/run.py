"""Headless launcher for the Lumen daemon (scheduled task / pythonw).

pythonw has no console: sys.stdout/stderr are None and uvicorn's logging
crashes on import. Point them at a file first, then start uvicorn.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
(ROOT / "tmp").mkdir(exist_ok=True)

_out = open(ROOT / "tmp" / "uvicorn.out", "a", buffering=1, encoding="utf-8")
if sys.stdout is None:
    sys.stdout = _out
if sys.stderr is None:
    sys.stderr = _out

sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("server.main:app", host="127.0.0.1", port=7788)
