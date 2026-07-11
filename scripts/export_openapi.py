#!/usr/bin/env python3
"""
Export the current FastAPI OpenAPI document to docs/openapi/.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.server import create_app


def main() -> None:
    app = create_app()
    spec = app.openapi()

    out_dir = Path("docs") / "openapi"
    out_dir.mkdir(parents=True, exist_ok=True)

    versioned = out_dir / f"full-spectrum-engine-openapi-{app.version}.json"
    latest = out_dir / "latest.json"

    payload = json.dumps(spec, ensure_ascii=False, indent=2) + "\n"
    versioned.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")

    print(f"Exported {versioned}")
    print(f"Updated {latest}")


if __name__ == "__main__":
    main()
