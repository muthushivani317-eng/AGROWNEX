#!/usr/bin/env python3
"""Compute and write the content_hash for a disease-risk RulePack file.

Usage (from the backend/ directory):

    python scripts/compute_rule_pack_hash.py \
        app/modules/disease_risk/data/rule_packs/paddy_blast.json

Loads the JSON file, computes its content_hash the same way the registry
does at import time (RulePack.expected_hash() in
app/modules/disease_risk/schemas.py -- a SHA-256 of the pydantic-normalized
dump, everything except content_hash itself), writes the correct hash back
into the file, then reports any schema problems in plain language instead of
a raw pydantic traceback. Exits non-zero if the file doesn't parse or
doesn't validate, so it's safe to wire into a pre-deploy check.

This script does NOT judge whether the epidemiological thresholds are
actually correct, reviewed, or safe to ship -- only that the file is
well-formed. That judgment is the reviewer's, not this script's or Claude's.
See the README in the same directory as the rule pack files before adding
one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.disease_risk.schemas import RulePack  # noqa: E402
from pydantic import ValidationError  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-rule-pack.json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"No such file: {path}", file=sys.stderr)
        return 2

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{path}: not valid JSON -- {exc}", file=sys.stderr)
        return 1

    if not isinstance(raw, dict):
        print(f"{path}: expected a single JSON object, got {type(raw).__name__}", file=sys.stderr)
        return 1

    # A placeholder is required for the file to validate at all (content_hash
    # has a fixed-length pattern) -- overwritten below with the real value.
    raw.setdefault("content_hash", "0" * 64)

    try:
        pack = RulePack.model_validate(raw)
    except ValidationError as exc:
        print(f"{path}: does not pass schema validation:", file=sys.stderr)
        for error in exc.errors():
            loc = ".".join(str(part) for part in error["loc"])
            print(f"  - {loc}: {error['msg']}", file=sys.stderr)
        return 1

    computed = pack.expected_hash()
    raw["content_hash"] = computed
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{path}: wrote content_hash = {computed}")

    live_statuses = {"VERIFIED", "SOURCED_PUBLIC_REFERENCE"}
    if pack.approval_status not in live_statuses:
        print(
            f"\nNote: approval_status is \"{pack.approval_status}\", not a live "
            f"status ({', '.join(sorted(live_statuses))}) -- this pack is "
            "tracked but will NOT be resolved for any farmer until "
            "approval_status is set to one of those by whoever actually "
            "reviewed/sourced it. Re-run this script after changing status "
            "(the hash does not depend on status, but re-running keeps this "
            "check honest).",
        )
    elif pack.approval_status == "SOURCED_PUBLIC_REFERENCE":
        print(
            f"\n{path}: valid SOURCED_PUBLIC_REFERENCE rule pack for "
            f"\"{pack.crop_id}\" / \"{pack.disease_id}\". This will be live "
            "for every matching farmer on next deploy, honestly labeled as "
            "compiled from a public source rather than personally reviewed "
            "by an agronomist -- make sure source_references are the "
            "genuine, real, checkable publication(s).",
        )
    else:
        print(
            f"\n{path}: valid VERIFIED rule pack for \"{pack.crop_id}\" / "
            f"\"{pack.disease_id}\". This will be live for every matching "
            "farmer on next deploy.",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
