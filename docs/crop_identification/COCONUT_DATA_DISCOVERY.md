# Coconut Data Discovery

## Final Coconut status

`COCONUT_DATA_FOUND_REQUIRES_DOWNLOAD`

## Candidate audit

| Field | Finding |
|---|---|
| Dataset | Coconut Tree Disease Dataset |
| Primary source | https://data.mendeley.com/datasets/gh56wbsnj5/1 |
| Dataset DOI | 10.17632/gh56wbsnj5.1 |
| Related data article | https://doi.org/10.1016/j.dib.2023.109690 |
| Licence | CC BY 4.0 on the primary Mendeley record |
| Exact archive | `Coconut Tree Disease Dataset.zip` |
| Publisher-reported archive size | 967 MB |
| Archive locally available | No |
| Local SHA-256 | Not available |
| Local extracted image count | 0 |
| Publisher-reported images | 5,798 |
| Documented classes | Bud Root Dropping; Bud Rot; Gray Leaf Spot; Leaf Rot; Stem Bleeding |
| Healthy class | Not documented |
| Original/augmented status | Data article calls repository data original/raw, but also reports preprocessing; archive inspection still required |
| Duplicate risk | Unknown; no local duplicate audit |
| Crop-identification suitability | Requires download and audit; five disease-only classes may create disease/collection shortcuts |
| Coconut disease-training suitability | Requires class review, healthy-control decision, duplicate audit and exact disease mapping |

The dataset is an image dataset, unlike the Coconut textbooks and PDFs elsewhere in the project. Those documents remain knowledge/reference evidence and are not counted as training images.

## Local and Drive audit

- Local Coconut raw folder contains only `.gitkeep`.
- Crop Expansion V2 ingestion status is `BLOCKED_DATASET_NOT_FOUND` with zero eligible images.
- Existing Coconut image, source, exclusion, quality and duplicate registers contain no eligible records.
- No local archive or extracted Coconut image directory was found.
- No project manifest documents a Google Drive copy or Drive checksum.
- Existing notebooks and readiness documents reference the candidate but do not prove download or extraction.

## Required manual action

Download `Coconut Tree Disease Dataset.zip` only from the primary Mendeley record. Place it in the project’s designated Coconut raw-intake directory without renaming its contents. Then rerun checksum, safe extraction, readability, class, licence-linkage, original/processed status and duplicate-family audits.

Do not create Coconut split rows from the publisher’s reported count.

