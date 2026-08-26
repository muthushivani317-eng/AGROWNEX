#!/usr/bin/env python3
"""Compute and write the content_hash for a verified crop-stage schedule file.

Usage (from the backend/ directory):

    python scripts/compute_schedule_hash.py \
        app/modules/calendar/data/verified_schedules/paddy.json

Loads the JSON file, computes its content_hash the same way the registry
does at import time (schedule_hash() in app/modules/calendar/registry.py --
a SHA-256 of everything except content_hash itself), writes the correct hash
back into the file, then validates the whole thing against the
CropStageSchedule schema and reports any problems in plain language instead
of a raw pydantic traceback. Exits non-zero if the file doesn't parse or
doesn't validate, so it's safe to wire into a pre-deploy check.

This script does NOT judge whether the content is actually correct,
reviewed, or safe to ship -- only that it's well-formed. That judgment is
the reviewer's, not this script's or Claude's. See the README in the same
directory as the schedule files before adding one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.calendar.registry import CropStageSchedule, schedule_hash  # noqa: E402
from pydantic import ValidationError  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-schedule.json>", file=sys.stderr)
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

    computed = schedule_hash(raw)
    raw["content_hash"] = computed
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{path}: wrote content_hash = {computed}")

    try:
        schedule = CropStageSchedule.model_validate(raw)
    except ValidationError as exc:
        print(
            f"\n{path}: hash written, but the file does not pass schema validation:",
            file=sys.stderr,
        )
        for error in exc.errors():
            loc = ".".join(str(part) for part in error["loc"])
            print(f"  - {loc}: {error['msg']}", file=sys.stderr)
        print(
            "\nFix the issues above and re-run this script (it's safe to run "
            "again -- content_hash will be recomputed).",
            file=sys.stderr,
        )
        return 1

    live_statuses = {"VERIFIED", "SOURCED_PUBLIC_REFERENCE"}
    if schedule.status.value not in live_statuses:
        print(
            f"\nNote: status is \"{schedule.status.value}\", not a live status "
            f"({', '.join(sorted(live_statuses))}) -- this entry is tracked "
            "but will NOT be resolved for any farmer until status is set to "
            "one of those by whoever actually reviewed/sourced it. Re-run "
            "this script after changing status (the hash does not depend on "
            "status, but re-running keeps this check honest).",
        )
    elif schedule.status.value == "SOURCED_PUBLIC_REFERENCE":
        print(
            f"\n{path}: valid SOURCED_PUBLIC_REFERENCE schedule for "
            f"\"{schedule.canonical_crop_id}\" (aliases: {', '.join(schedule.aliases) or 'none'}). "
            "This will be live for every farmer with that crop on next deploy, "
            "honestly labeled as compiled from a public source rather than "
            "personally reviewed by an agronomist -- make sure "
            "source_organization/document_reference are the genuine, real "
            "publication.",
        )
    else:
        print(
            f"\n{path}: valid VERIFIED schedule for \"{schedule.canonical_crop_id}\" "
            f"(aliases: {', '.join(schedule.aliases) or 'none'}). "
            "This will be live for every farmer with that crop on next deploy.",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
