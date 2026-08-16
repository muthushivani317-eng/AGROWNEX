# Crop Identification Negative-Class Policy

## `unknown_unsupported_plant`

Runtime meaning: a plant is visible, but it is outside Banana, Paddy, Cotton, Groundnut, Coconut, Chilli, and Redgram.

This is an open-set safety category, not a botanical species. Source labels may be retained for auditing, but the runtime class must remain `unknown_unsupported_plant`.

Required coverage should include multiple independent, licensed sources across:

- maize and sugarcane;
- tomato and brinjal;
- pulses other than Redgram;
- weeds;
- ornamental plants;
- trees and wild plants;
- flowers.

Selection rules:

- exclude any image containing or ambiguously depicting a supported crop;
- never use social-media scraping or unlicensed image-search downloads;
- preserve source-dataset and original-label metadata;
- balance sources and plant groups so one dataset or species cannot define the class;
- group mirrors, derivatives, crops and augmentations into one duplicate family;
- hold out source groups for evaluation;
- do not infer an exact species when the source does not provide one.

### Existing local candidate

PlantDoc Object Detection is locally present:

- primary source: `https://github.com/pratikkayal/PlantDoc-Object-Detection-Dataset`;
- paper DOI: `10.1145/3371158.3371196`;
- dataset licence: CC BY 4.0;
- archive: `D:\AgrowAI\knowledge_base\vision\datasets\raw\plantdoc_object_detection\plantdoc_object_detection_master.zip`;
- SHA-256: `5a1c4e745967c7cc13b4b38c407e933c5137074932339c00e0d4fc17506c68ac`;
- readable local images: 2,586.

It is not approved for negative-class rows. The authors describe it as internet-scraped; asset-level provenance remains unresolved. It also mixes supported and unsupported plant labels, contains multiple annotations per image, and has known derivative/mirror families. Cropped PlantDoc and the Roboflow export are not independent sources.

## `invalid_non_plant`

This category is semantic rejection: a readable image that does not present a usable plant subject. It may include people, animals, vehicles, buildings, indoor scenes, tools, soil-only images, sky, documents and screenshots.

No verified local semantic non-plant dataset was found.

Required source policy:

- use primary datasets with explicit licences permitting the intended use;
- record the dataset source for every image;
- sample multiple independent sources and scene types;
- remove images containing supported crops;
- perform privacy and sensitive-content review for people;
- do not use only synthetic noise;
- do not generate counts until files are locally audited.

## Technical image-quality failures

Technical failures must be tracked separately from semantic non-plant rejection:

- unreadable or corrupted file;
- decode failure;
- dimensions below the approved minimum;
- completely or extremely blurred image;
- extreme underexposure or overexposure;
- nearly blank image.

These cases should normally be rejected by the pre-inference quality gate, not learned as botanical evidence. If examples are retained for testing, store them in a separate quality-failure manifest with the transformation or corruption provenance. Do not mix them into semantic `invalid_non_plant` performance reporting.

## Approval gate

Neither negative class is ready. Approval requires at least two genuinely independent, verified-licence sources per semantic negative category, source-balanced sampling, duplicate-family checks, reviewer-approved exclusions of supported crops, and a sealed source-held-out test assignment.

