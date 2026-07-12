#!/usr/bin/env python3
"""
Generic object registry with schema validation and deterministic content digest.

Shared by :class:`ProfileRegistry` and :class:`ScenarioRegistry` (FR-01 / FR-02 /
FR-03). The registry is the single source of truth for loading, validating and
recomputing the ``content_digest`` of every governed object (Profile / Scenario).

Design constraints (v1.3 共享知识):
  * Every object is keyed by ``(id, version)``. Multiple versions of the same
    id may coexist; the default resolution picks the latest *approved* version.
  * ``content_digest`` is ``SHA-256(canonical_json(obj without its own digest
    field))`` — deterministic and reproducible (FR-05 / AC-05).
  * On load / ingest the declared digest is *recomputed* and compared; a mismatch
    raises :class:`ProfileIntegrityError` — never silently accepted (NFR-05).
  * Only the standard library + the existing ``validator`` are used; no new deps.

Zero intrusion: this module is brand-new and additive; it does not touch any
v1.2 core module.
"""
import hashlib
import json
import os

from . import validator
from .envelope import canonical_json  # canonical_json is a pure helper, no cycle


def _digest_without(obj, drop_key="digest"):
    """SHA-256 over canonical_json of ``obj`` with ``drop_key`` removed.

    Mirrors the v1.3 contract: the digest is computed over the object *minus*
    its own digest field, so the digest is stable regardless of where it sits.
    """
    clean = {k: v for k, v in obj.items() if k != drop_key}
    return hashlib.sha256(canonical_json(clean).encode("utf-8")).hexdigest()


class ProfileIntegrityError(Exception):
    """Raised when a declared content_digest does not match the recomputed one."""

    code = "PROFILE_INTEGRITY"

    def __init__(self, message):
        super().__init__(message)


class ObjectRegistry:
    """Load / validate / digest governed objects by ``(id, version)``.

    Concrete registries (``ProfileRegistry``, ``ScenarioRegistry``) pass their
    schema file and fixtures directory.
    """

    def __init__(self, schema_file, fixtures_dir=None):
        self.schema_file = schema_file
        self.fixtures_dir = fixtures_dir
        self._schema = None
        self._cache = {}  # (id, version) -> object dict

    # --------------------------------------------------------------
    # Schema
    # --------------------------------------------------------------
    def _load_schema(self):
        if self._schema is None:
            if os.path.isabs(self.schema_file) and os.path.exists(self.schema_file):
                with open(self.schema_file, encoding="utf-8-sig") as handle:
                    self._schema = json.load(handle)
            else:
                self._schema = validator.load_schema(self.schema_file)
        return self._schema

    # --------------------------------------------------------------
    # Digest
    # --------------------------------------------------------------
    def compute_digest(self, obj):
        """Recompute the canonical content_digest for ``obj`` (digest field excluded)."""
        return _digest_without(obj)

    # --------------------------------------------------------------
    # Validation
    # --------------------------------------------------------------
    def validate(self, obj):
        """Validate ``obj`` against the registry schema. Returns ``(ok, errors)``."""
        return validator.validate_instance(obj, self._load_schema())

    # --------------------------------------------------------------
    # Load fixtures from disk
    # --------------------------------------------------------------
    def load(self):
        """Scan ``fixtures_dir``; validate + integrity-check every JSON object."""
        self._cache = {}
        if not self.fixtures_dir or not os.path.isdir(self.fixtures_dir):
            return
        for fn in sorted(os.listdir(self.fixtures_dir)):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(self.fixtures_dir, fn)
            with open(path, encoding="utf-8-sig") as handle:
                obj = json.load(handle)
            ok, errors = self.validate(obj)
            if not ok:
                raise ValueError(f"fixture {fn} failed schema validation: {errors}")
            declared = obj.get("digest")
            actual = self.compute_digest(obj)
            if declared and declared != actual:
                raise ProfileIntegrityError(
                    f"fixture {fn} digest mismatch: declared={declared} actual={actual}"
                )
            key = (obj["id"], obj.get("version"))
            self._cache[key] = obj

    # --------------------------------------------------------------
    # Resolution
    # --------------------------------------------------------------
    @staticmethod
    def _version_key(version):
        parts = []
        for piece in str(version).split("."):
            parts.append(int(piece) if piece.isdigit() else piece)
        return parts

    def get(self, object_id, version=None):
        """Return the object for ``(object_id, version)``.

        When ``version`` is ``None`` the latest *approved* version is returned
        (effective window first, then highest semantic version).
        """
        if version is not None:
            key = (object_id, version)
            if key not in self._cache:
                raise KeyError(f"no object {object_id}@{version} in registry")
            return self._cache[key]

        candidates = [(oid, ver) for (oid, ver) in self._cache if oid == object_id]
        if not candidates:
            raise KeyError(f"no object {object_id} in registry")

        approved = [
            k for k in candidates
            if self._cache[k].get("approval_status") == "approved"
        ]
        pool = approved if approved else candidates
        pool.sort(key=lambda k: self._version_key(k[1]))
        return self._cache[pool[-1]]

    def all_versions(self, object_id):
        """Return every version string known for ``object_id`` (sorted)."""
        vers = [ver for (oid, ver) in self._cache if oid == object_id]
        return sorted(vers, key=self._version_key)

    # --------------------------------------------------------------
    # Ingest (used by REST load endpoints)
    # --------------------------------------------------------------
    def ingest(self, obj):
        """Validate + integrity-check ``obj`` and add it to the cache.

        Returns the ``id@version`` key string. If the object carries no digest,
        one is computed and attached. A digest mismatch raises
        :class:`ProfileIntegrityError`.
        """
        ok, errors = self.validate(obj)
        if not ok:
            raise ValueError(f"object failed schema validation: {errors}")
        declared = obj.get("digest")
        actual = self.compute_digest(obj)
        if declared and declared != actual:
            raise ProfileIntegrityError(
                f"digest mismatch: declared={declared} actual={actual}"
            )
        if not declared:
            obj = dict(obj)
            obj["digest"] = actual
        key = (obj["id"], obj.get("version"))
        self._cache[key] = obj
        return f"{obj['id']}@{obj.get('version')}"

    def list_ids(self):
        """Return the sorted list of distinct object ids in the cache."""
        return sorted({oid for (oid, _) in self._cache})
