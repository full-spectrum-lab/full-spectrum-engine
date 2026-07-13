#!/usr/bin/env python3
"""
Full Spectrum Governance Chain generator.

Turns a raw business input (e.g. an ecommerce after-sales dialogue) into the
complete governance object chain and validates it against the vendored
Full Spectrum Protocol schemas. Self-contained: standard library only, no
numpy / network dependency.

Quick start:
    python -m src.governance_chain generate \
        -i examples/governance_chain/raw-input.ecommerce.json -o out
"""
from .generate import build_chain, write_chain
from .adapters import get_adapter, EcommerceAdapter
from . import validator

__all__ = ["build_chain", "write_chain", "get_adapter", "EcommerceAdapter", "validator"]
__version__ = "1.4.0"
