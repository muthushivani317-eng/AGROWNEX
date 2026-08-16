# Coconut Crop-Identification Subset Audit

## Decision

`COCONUT_CROP_ID_SUBSET_REQUIRES_REVIEW`

The conservative subset contains 5,735 readable Coconut images. None is yet marked training-eligible because viewpoint labels are class-level audit proxies rather than independently reviewed per-image annotations, and the dataset remains a single disease-focused source. The main crop-identification split manifest was therefore not modified.

## Source

- Dataset: Coconut Tree Disease Dataset
- DOI: `10.17632/gh56wbsnj5.1`
- Licence recorded by the source: CC BY 4.0
- Archive SHA-256: `0a755b7c57c9255204d67e65207db14d310a7ed8bf83906a335e4807cd5ef487`
- Readable images audited: 5,798
- Corrupt images: 0

## Conservative Filtering

- Excluded all 58 images belonging to the 29 exact cross-class conflict families.
- For five non-conflicting same-class exact duplicate pairs, retained one deterministic canonical image and excluded the redundant copy.
- Did not delete perceptual-near-duplicate candidates automatically.
- Assigned stable perceptual-family identifiers so every retained family can be grouped into one future split.
- Preserved the original disease-folder label only as audit provenance; every crop-identification target is `coconut`.
- Did not claim that disease-focused images provide healthy or general Coconut coverage.

## Counts

| Measure | Count |
|---|---:|
| Input readable images | 5,798 |
| Retained conservative candidates | 5,735 |
| Excluded exact cross-class images | 58 |
| Excluded redundant same-class exact copies | 5 |
| Training-eligible images | 0 |

## Viewpoint Audit

The current viewpoint assignment is a conservative class-level proxy derived from the visible subject type associated with each audited folder. It is not a completed per-image expert review.

| Viewpoint | Candidate images |
|---|---:|
| leaf | 2,103 |
| crown/bud | 470 |
| trunk/stem | 1,006 |
| partial_tree | 0 |
| whole_tree | 514 |
| unknown_view | 1,642 |

The absence of `partial_tree` observations and the 1,642 `unknown_view` records are material coverage gaps. Group-aware sampling must use `perceptual_family`, and future split construction must keep each such family wholly inside one split.

## Readiness Blockers

1. Complete per-image or statistically justified human viewpoint verification.
2. Resolve the large `unknown_view` group and document whether the retained imagery genuinely depicts Coconut rather than only lesions or cropped tissue.
3. Add independent, licence-verified Coconut sources with healthy and general-view coverage to reduce source and disease-label shortcuts.
4. Add verified `unknown_unsupported_plant` and `invalid_non_plant` data.
5. Re-run duplicate-family grouping before creating any four-way crop-identification split.

No disease label was promoted as a crop-identification target, no training was performed, and no main split was changed.
