# Crop Identification Input Audit

## Decision

`CROP_IDENTIFICATION_DATA_INCOMPLETE`

The audit found 11,606 locally resolvable, licensed, original-image candidates for six crops. They are not yet authorized for crop-identification training. Coconut has no verified local labeled archive; `unknown_unsupported_plant` and `invalid_non_plant` have no verified datasets; and every represented crop is effectively tied to one source dataset, creating a material dataset-source shortcut risk.

The generated split manifest preserves the existing disease-model group-aware assignments. Its 873 `provisional_test` rows were copied as metadata only and remain sealed. No provisional-test image was opened.

## Crop inventory

| Crop | Status | Candidate rows | Training-eligible rows | Existing split counts (train/dev/cal/test) |
|---|---|---:|---:|---|
| Banana | PARTIAL_REQUIRES_REVIEW | 897 | 0 | 628 / 134 / 68 / 67 |
| Paddy | PARTIAL_REQUIRES_REVIEW | 7,310 | 0 | 5,116 / 1,096 / 548 / 550 |
| Cotton | PARTIAL_REQUIRES_REVIEW | 779 | 0 | 544 / 116 / 59 / 60 |
| Groundnut | PARTIAL_REQUIRES_REVIEW | 720 | 0 | 504 / 108 / 53 / 55 |
| Coconut | MISSING | 0 | 0 | 0 / 0 / 0 / 0 |
| Chilli | PARTIAL_REQUIRES_REVIEW | 1,203 | 0 | 843 / 180 / 91 / 89 |
| Redgram | PARTIAL_REQUIRES_REVIEW | 697 | 0 | 487 / 105 / 53 / 52 |

## Source evidence

- Paddy: RiceLeafDiseaseBD v2, Mendeley Data, DOI `10.17632/86s4jzj2m4.2`, CC BY 4.0, archive SHA-256 `f3d47107212db817b3941232258630b46b472134742b26f505eb03727bde8164`.
- Cotton: Cotton Leaf Image Dataset for Disease Classification, Mendeley Data, DOI `10.17632/t9hgvk2h9p.1`, CC BY 4.0, archive SHA-256 `a75beeb9d505d6450dadb5acd9531d26a554350e4bc0a9f69e73775a851cd6a7`.
- Groundnut: Sasmal groundnut dataset, Mendeley Data, DOI `10.17632/x6x5jkk873.2`, CC BY 4.0, archive SHA-256 `a4cb2db982d2733100efa444f8eb46a4b547489faeb569042e9007a5ad93df05`.
- Banana: BananaLSD, Mendeley Data, DOI `10.17632/9tb7k297ff.1`, CC BY 4.0, archive SHA-256 `420523152c2b65c3f116c072cf95017733e9b8cd0cd01b7f667c588ca81dc85d`.
- Chilli: Krishna River Basin chilli dataset, Mendeley Data, DOI `10.17632/ymt8k9bjkn.3`, CC BY 4.0, archive SHA-256 `a771b59ee77a245061d797a800f24ef04ce9d5c4ea876508e8811117599881e4`.
- Redgram: Rajput pigeonpea dataset, Mendeley Data, DOI `10.17632/bd553pdtny.1`, CC BY 4.0, archive SHA-256 `c9f24738913e81d6e90d147fcaabab369198af4df30ac317933894cd4e407994`.
- Coconut: a documented Mendeley candidate exists, but there is no verified local archive, checksum, extraction audit, or eligible manifest.

Full archive paths, extracted roots, counts, source classes, and licence evidence are recorded in `dataset_registry.json`.

## Disease-image suitability

Only original or previously cleaned original images are represented. Annotated derivatives and the separately packaged chilli augmentation are excluded. Disease images were not silently promoted as training-ready crop-identification data: all rows carry `verification_status=PARTIAL_REQUIRES_REVIEW`, `training_eligible=FALSE`, and a review reason.

Material risks:

- Paddy contributes 63% of candidate rows (7,310 of 11,606), creating severe crop imbalance.
- Each represented crop comes from one dataset, so crop identity is confounded with camera, background, geography, compression, and collection protocol.
- Disease-class distributions differ by crop, so a model may learn lesions or healthy/disease prevalence rather than crop morphology.
- Existing group-aware split integrity prevents known exact/perceptual-family leakage, but cannot eliminate source-level shortcut learning when an entire crop has one source.
- Reusing the same images and assignments as disease-model evaluation creates cross-task governance risk. A separate crop-ID sealed test set from independent sources is still required.

## Duplicate and leakage checks

- Manifest rows: 11,606.
- Local paths resolved: 11,606 of 11,606.
- Duplicate SHA-256 rows: 0.
- SHA-256 families crossing splits: 0.
- Duplicate families crossing splits: 0.
- Existing split names preserved: `training`, `development_validation`, `calibration`, `provisional_test`.
- Provisional-test images inspected: no.

## Exclusions

- PlantDoc object-detection archive: excluded because licence is unresolved and its mixed labels are not verified for the required crop/open-set classes.
- Chilli augmented material: excluded; only cleaned original images are included as review candidates.
- Coconut documented candidate: excluded because it was not downloaded and has no locally verified hash or image audit.
- Any unresolved, unlicensed, augmented-only, synthetic, social-media, or image-search material: excluded.

## Required next gate

Before changing any row to `training_eligible=TRUE`, obtain at least one independently sourced, licensed, original-image collection per represented crop where practical; add verified Coconut data; add governed open-set plant and non-plant negatives; rerun duplicate-family grouping across all sources; then construct a new crop-ID-specific split with source groups held out so development/calibration/provisional-test data measure generalization rather than source recognition.

