"""Generate openapi.json from FastAPI app for @hey-api/openapi-ts client generation.

Run from konkurs/ root:
    python backend/scripts/gen_openapi.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # konkurs/
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app  # noqa: E402

if __name__ == "__main__":
    schema = app.openapi()
    out = ROOT / "openapi.json"
    out.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: openapi.json -> {out}")
