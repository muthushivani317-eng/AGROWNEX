# Crop Identification Data Acquisition and Approval Plan

## Current decision

`CROP_IDENTIFICATION_DOWNLOADS_REQUIRED`

No crop-identification model is authorized for training. The existing 11,606 rows remain review candidates with `training_eligible=FALSE`.

## Acquisition order

1. Download the documented Coconut archive from its primary Mendeley Data record.
2. Acquire governed open-set plant sources covering plants outside the seven supported crops.
3. Acquire governed semantic non-plant sources and separately create a technical image-quality rejection corpus.
4. Add at least one independent original-image source for every supported crop.
5. Audit licences, hashes, readability, class semantics, exact duplicates and perceptual duplicate families before adding any row.
6. Construct a new crop-identification-specific grouped split. Do not reuse source-dependent random splits as proof of generalization.

## Approval record required for every source

Each source must have:

- primary source URL and DOI where available;
- exact dataset and archive name;
- licence text verified at the primary host;
- archive SHA-256 and byte size;
- extraction root and readable/corrupt image counts;
- original/augmented/derived status;
- class and crop mapping approved by a reviewer;
- source group and duplicate-family identifiers;
- asset-level provenance review where a dataset was assembled from internet images;
- explicit crop-identification suitability decision.

No file may enter `split_manifest.csv` until it exists locally and passes those gates.

## Coconut

Download exactly `Coconut Tree Disease Dataset.zip` from `https://data.mendeley.com/datasets/gh56wbsnj5/1`. The primary record identifies DOI `10.17632/gh56wbsnj5.1`, CC BY 4.0, 5,798 labeled images, and a 967 MB archive. These are publisher-reported values, not local audit results.

After download:

1. Preserve the original archive.
2. Compute SHA-256 and byte size locally.
3. Extract safely to a new audited root.
4. Count readable and corrupt files.
5. Confirm the five documented folders and whether any healthy-control images exist.
6. Determine whether images are original, preprocessed, augmented, or duplicated.
7. Run exact and perceptual duplicate checks.
8. Review the ambiguous `Bud Root Dropping` label without silently correcting it.
9. Decide separately whether the dataset is suitable for crop identification and Coconut disease training.

## Supported-crop source diversity

Banana, Paddy, Cotton, Groundnut, Chilli, and Redgram each have one locally verified source. That is insufficient to demonstrate that a crop classifier learns crop morphology instead of collection-specific signals.

For every crop, acquire at least one independent original-image source where practical. Independence requires different collection provenance—not a mirror, resized export, crop of the same image, or augmented derivative.

Review and neutralize:

- background and field-setting differences;
- fixed resolution or aspect ratio;
- watermarks, borders and text;
- camera/compression signatures;
- augmentation patterns;
- folder/file-name leakage;
- disease prevalence acting as a crop proxy.

## Balancing plan

Do not delete Paddy images. Before training approval:

- use crop-balanced batches or a weighted sampler;
- cap per-epoch contribution rather than deleting source files;
- keep duplicate families within one split;
- treat source dataset as a grouping variable;
- hold out independent source groups for development and sealed evaluation;
- report both macro crop recall and per-source recall;
- prevent one source from appearing in every split when source-held-out evaluation is possible;
- freeze sampling weights before opening the sealed provisional test.

Paddy currently represents 7,310 of 11,606 candidates (63.0%). Uniform image sampling is not approved.

## Drive handoff

The existing registry and split manifest should not be uploaded as training-ready inputs. If uploaded for notebook preflight, the notebook must honor `training_authorized=false`.

After Coconut and negative-source audits are complete, regenerate both files and upload them to:

- `/content/drive/MyDrive/AgrowAI_V1/crop_identification/dataset_registry.json`
- `/content/drive/MyDrive/AgrowAI_V1/crop_identification/split_manifest.csv`

