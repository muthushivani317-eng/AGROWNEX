# Disease Model Final Report

## 1. Decision

- Crop and model version:
- Requested release stage: `OFFLINE_ONLY | INTERNAL | KVK_PILOT | FARMER`
- Decision: `PASS | BLOCKED`
- Promotion decision SHA-256:
- Decision owner and approval date:
- Farmer inference enabled: `false` unless every farmer gate passes

## 2. What was implemented and verified

List only work executed with attached test or receipt evidence. Include code SHA,
environment lock, model/artifact/policy hashes, and the exact commands used.

## 3. Dataset contract

- Dataset and snapshot IDs:
- Dataset fingerprint:
- Classes and independent group counts by split:
- Source/licence/consent status:
- Expert review/adjudication status:
- Farm, visit, plant, leaf, capture, duplicate and source-group leakage result:
- Sealed field-test access receipt:
- Known missing slices or metadata:

Do not convert unknown grouping into synthetic identifiers or claim that image
count equals independent biological sample count.

## 4. Evaluation

Report all-prediction accuracy, balanced accuracy and macro F1; per-class
precision, recall, F1 and support; confusion matrix; NLL, Brier and ECE;
accepted accuracy, errors, coverage and abstention; OOD false accepts; p50/p95/p99
latency; bootstrap confidence intervals; and every registered field slice.

For a hierarchical model, include each stage and end-to-end cascade metrics.

## 5. Baseline comparison and error analysis

- Current production/research baseline:
- Candidate movement with confidence intervals:
- False positives, false negatives and abstentions by class:
- Error clusters by source, farm, district, device, view and symptom stage:
- Label ambiguity, data defects, serving mismatches and OOD failures:
- Regressions added and next falsifiable experiment:

## 6. Promotion gates

Attach every metric and evidence gate with actual value, threshold, pass/fail,
policy owner, and reason code. Missing values are failures. State explicitly that
public-dataset evidence is not field validation.

## 7. Monitoring, feedback and privacy

- Prediction-event coverage and schema version:
- Availability, error, decision-code, latency, acceptance, abstention, OOD and
  quality-rejection metrics:
- Delayed expert-label arrival and correction metrics:
- Drift comparisons and alert owners:
- Consent, retention and deletion controls:
- Confirmation that farmer feedback was not used as ground truth:

## 8. Rollout and rollback

- Current, candidate and previous immutable artifact references:
- Shadow/canary scope:
- Stop rules and owners:
- Rollback trigger and traffic switch:
- Latest rollback-drill receipt and result:
- Post-rollback verification:

## 9. Accuracy-improvement status

Separate statements into:

1. `IMPLEMENTED_AND_VERIFIED`
2. `PREPARED_BUT_REQUIRES_NEW_DATA`
3. `BLOCKED_MANUAL_OR_EXTERNAL`

Never claim an accuracy increase unless a frozen candidate beats the baseline on
an untouched independent expert-labelled field test without a critical-slice or
safety-gate regression.

## 10. Open blockers and next actions

Name the owner, evidence needed, dependency, and completion test for every item.
