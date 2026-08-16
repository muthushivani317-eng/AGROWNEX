# Chilli review workflow

Status: `READY_FOR_INTERNAL_NON_EXPERT_REVIEW`

The validated source manifest contains 4,032 Chilli candidates and zero human
approvals. Run:

```powershell
python scripts/crop_id_human_review.py --crop chilli --port 8765
```

The browser interface provides lazy thumbnail grids, full-size SHA-verified
previews, source/proposed label/path/SHA-256/perceptual hash/duplicate family/
resolution/quality/licence/quarantine metadata, filters, keyboard navigation,
notes, separate crop and disease decisions, resume state, and CSV/JSON exports.
Decisions are atomically stored separately from the source manifest.

No source label is promoted by the tool. `APPROVE` is an explicit human action.
