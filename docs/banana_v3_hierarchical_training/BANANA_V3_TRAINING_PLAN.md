# Banana V3 Training Plan

## 1. Objective

Train two separate baselines:

- **A.** a healthy-versus-diseased binary gate;
- **B.** a Cordana-versus-Pestalotiopsis-versus-Sigatoka classifier.

Do not train a crop classifier or learned quality model in the first baseline.

## 2. Source data policy

The only allowed initial source is the approved Banana V2 internal dataset. Do not add:

- the opened 424-image external benchmark;
- expert-review external images;
- scraped social-media or unverified internet images;
- augmented copies as independent originals;
- data without established licence and provenance.

**Verify dataset licence and provenance against official source.**

The external benchmark is blocked from training, model selection, calibration, threshold selection, preprocessing tuning, architecture selection, and debugging.

## 3. Label transformation

Binary gate:

- `banana__healthy` → `banana__healthy`
- `banana__cordana_leaf_spot` → `banana__diseased`
- `banana__pestalotiopsis_leaf_spot` → `banana__diseased`
- `banana__sigatoka_leaf_spot` → `banana__diseased`

Disease classifier:

- `banana__cordana_leaf_spot`
- `banana__pestalotiopsis_leaf_spot`
- `banana__sigatoka_leaf_spot`

Exclude healthy images from the disease classifier.

## 4. Split preservation

Use the existing final grouped Banana V2 split as the source of truth. Preserve `training`, `development_validation`, and `calibration`; do not randomly resplit images.

Preserve capture groups, exact duplicate groups, perceptual duplicate groups, and source-family grouping. Do not use the opened external benchmark.

## 5. Expected derived split counts

Do not hardcode derived counts. Colab must calculate and print:

- binary-gate training, development, and calibration counts by class;
- disease-classifier training, development, and calibration counts by class.

It must reconcile every derived total to the approved source manifest and split manifest.

## 6. Baseline model

For both models use:

- torchvision MobileNetV3 Small with pretrained ImageNet weights;
- input size 224;
- weighted cross entropy;
- AdamW;
- ReduceLROnPlateau;
- automatic mixed precision;
- checkpoint selection by development macro F1;
- early stopping;
- recorded deterministic seed.

Configurable starting values, not proven optima:

- batch size `32`;
- learning rate `3e-4`;
- weight decay `1e-4`;
- maximum epochs `30`;
- early-stopping patience `6`.

## 7. Data augmentation baseline

Allow conservative training-only augmentation:

- random resized crop;
- horizontal flip only when biologically acceptable;
- mild rotation;
- mild brightness and contrast changes;
- mild colour jitter.

Do not use aggressive geometric distortion, synthetic lesions, copied disease symptoms, MixUp, or CutMix in the first baseline. **Verify whether each augmentation preserves biologically valid symptoms.**

## 8. Class imbalance

For each model:

- calculate weights from the training split only;
- print training class distribution;
- never use development or calibration labels to derive training weights;
- do not oversample before confirming group-leakage safety.

## 9. Training outputs

Save separately for each model:

- `best.pt`;
- `last.pt`;
- `training_history.csv`;
- `training_config.json`;
- `class_to_index.json`;
- `index_to_class.json`;
- checkpoint SHA-256;
- split-manifest SHA-256;
- environment receipt;
- reproducibility receipt.

## 10. Development evaluation

For each model calculate:

- Top-1;
- Top-2 or Top-3 as appropriate;
- macro precision, recall, and F1;
- weighted F1;
- per-class precision, recall, F1, and support;
- raw and normalized confusion matrices;
- NLL, ECE, and multiclass Brier score;
- false-confident errors;
- highest-confidence wrong predictions.

Binary gate additionally reports healthy recall, diseased recall, false healthy rate, and false diseased rate.

Disease classifier additionally reports Cordana, Pestalotiopsis, and Sigatoka recall and pairwise confusion counts.

## 11. Calibration

Fit separate scalar temperatures for the healthy gate and disease classifier, using only the calibration split. Confirm that argmax does not change and report NLL, ECE, and Brier score before and after scaling.

## 12. Threshold selection

Select:

- healthy and diseased confidence and margin thresholds for the healthy gate;
- class-specific confidence and margin thresholds for each disease.

Evaluate coverage, accepted accuracy, accepted macro F1, per-class coverage, per-class accepted accuracy, false-confident errors, and the zero-accepted-class constraint. Do not select thresholds from the opened external benchmark.

## 13. Hierarchical simulation

Before freezing, simulate the full hierarchy on `development_validation` and `calibration`. Report:

- final exact-disease and healthy coverage;
- abstention rate;
- final accepted accuracy and macro F1;
- per-class final recall;
- reason-code and gate-failure distributions;
- model-symptom conflict placeholder count when symptoms are unavailable.

## 14. Freeze procedure

Freeze both checkpoints, both temperatures, all thresholds, class mappings, preprocessing, stage configuration, decision policy, split manifest, and SHA-256 checksums. After freezing, no tuning against external results is permitted.

## 15. Evaluation policy

The already-opened 424-image benchmark may be used only once as a diagnostic comparison after freezing. It cannot be used for training, model selection, calibration, threshold selection, preprocessing selection or tuning, architecture selection, or debugging.

A future official field-performance claim requires a new sealed, expert-reviewed field test. Public-dataset performance is not Tamil Nadu field accuracy.

## 16. Stop conditions

Stop and do not deploy when:

- external transfer remains poor;
- one disease class collapses;
- accepted accuracy is unsafe;
- false-confident errors remain high;
- class coverage is near zero;
- calibration fails under domain shift;
- label definitions remain unresolved.

Label definitions and symptom interpretations: **Verify against official source or qualified plant-pathology expert.**

## 17. Ablation order after baseline

Only after the baseline:

1. label-noise review;
2. class-specific thresholds;
3. symptom-question decision layer;
4. realistic farmer-photo augmentation;
5. TTA;
6. larger backbone;
7. localization.

No ablation is assumed to improve performance. Banana V2 and its frozen artifacts must not be modified. Farmer never pays, and no pesticide brand may be promoted.
