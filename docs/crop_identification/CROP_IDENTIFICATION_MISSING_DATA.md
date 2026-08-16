# Crop Identification Missing Data

## Blocking classes

| Class | Status | Missing evidence |
|---|---|---|
| coconut | MISSING | Verified local archive, licence linkage, SHA-256, extraction audit, crop labels, duplicate audit, and fixed split |
| unknown_unsupported_plant | MISSING | Authoritatively licensed plant images outside the seven supported crops, governed taxonomy/sampling plan, and fixed split |
| invalid_non_plant | MISSING | Licensed non-plant/invalid-input images with a documented safety-label policy and fixed split |

## Review still required for six represented crops

Banana, Paddy, Cotton, Groundnut, Chilli, and Redgram have source-backed candidate rows, but each crop is represented by one source dataset. Independent-source crop images are required to measure and reduce source/background shortcut learning. Crop-balanced sampling must be fixed before training. Disease and healthy subclasses must be reviewed so lesion prevalence cannot act as a surrogate crop label.

No candidate row is marked training-eligible in the delivered manifest.

## Upload requirement

The two completed local files must be manually uploaded to:

- `/content/drive/MyDrive/AgrowAI_V1/crop_identification/dataset_registry.json`
- `/content/drive/MyDrive/AgrowAI_V1/crop_identification/split_manifest.csv`

Uploading them does not change the preflight decision or authorize training. The notebook should continue to fail closed while `training_authorized` is `false`.

