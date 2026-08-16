# Disease-model MLE contracts

This package provides dependency-free, fail-closed lifecycle tooling. It does
not train a model and cannot turn public-dataset evaluation into field evidence.

## Commands

Run commands from the repository root:

```powershell
python -m training_tools.mle_contracts.cli validate-dataset dataset.json --output validation.json
python -m training_tools.mle_contracts.cli evaluate evaluation_input.json --output evaluation.json
python -m training_tools.mle_contracts.cli promote evaluation.json policy.json evidence.json --output promotion_decision.json
python -m training_tools.mle_contracts.cli validate-event prediction_event.json
python -m training_tools.mle_contracts.cli rollback-drill registry.json banana --output rollback_drill.json
```

`evaluation_input.json` contains `labels`, `lineage`, and `records`. Every record
contains a unique `sample_id`, `evaluation_group_id`, a probability map covering
every label, `accepted`, `is_ood`, and `latency_ms`. In-distribution records carry
a known `true_label`; OOD records must use `true_label: null`. Metrics and
calibration exclude OOD records, while OOD false acceptance is reported separately.
Confidence intervals use a deterministic cluster bootstrap over
`evaluation_group_id`, never an image-level bootstrap.

Promotion policies intentionally contain no repository default thresholds and are
canonical-hashed alongside canonical-hashed evidence records. The evaluation
lineage must bind to that exact policy hash and the registry binds any promotion
to the candidate model and artifact hashes.
Plant-pathology, product-safety, and operations owners must approve crop-specific
values before use. A missing threshold or evidence value blocks promotion.

The dataset validator requires independently meaningful source, farm, visit,
plant, leaf, capture, and duplicate-family identifiers. Use `UNKNOWN` only while
preparing an inventory; it will group all such rows together and normally reveal
that a safe split cannot yet be demonstrated.

## Required human work

- Confirm licences, consent, privacy, and botanical labels.
- Define mistake costs and approve crop/class promotion thresholds.
- Collect independent field groups and freeze the sealed field test.
- Review failure examples and sign off a KVK pilot.
- Authorize any transition to farmer inference.

The local CLI cannot authorize farmer inference. A FARMER decision remains failed
unless the calling release control plane supplies a trusted verifier for the
approved evidence. The rollback drill validates only an in-memory state
transition; it is not evidence that persistent registry reload, runtime model
loading, backend readiness, or traffic disablement succeeded.
