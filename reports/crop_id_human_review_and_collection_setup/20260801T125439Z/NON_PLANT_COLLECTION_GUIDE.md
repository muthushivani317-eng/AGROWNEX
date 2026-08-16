# Non-plant local collection guide

Status: `PACKAGE_READY_NO_PHOTOGRAPHS_COLLECTED`

Permitted subjects include indoor/outdoor objects, tools, vehicles without
identifiers, buildings, empty backgrounds, soil-only scenes, documents without
personal data, screens without private data, animals without people, blurred
non-plants, and low-light non-plants. Technical quality failures must remain
separate from semantic non-plant examples.

Never capture identifiable faces, personal documents, licence plates, private
screens, or copyrighted posters as the main subject. Remove such files before
ingestion. Aim for at least 1024 pixels on the shorter side where feasible and
vary lighting, background, camera distance, and portrait/landscape orientation.
Include genuine blur and low-quality examples, but do not rely on synthetic noise.
Avoid repeated shots of the same scene.

Use `python scripts/ingest_local_crop_id_collection.py --kind non_plant --input <folder>`.
It retains originals, creates EXIF-stripped processed copies, hashes files,
extracts dimensions, detects exact/perceptual duplicate groups, records
`SELF_CAPTURED`, and creates a pending review packet. Ingestion is not approval.
