#!/usr/bin/env python3
"""Enable `python -m src.governance_chain ...`."""
import sys

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
