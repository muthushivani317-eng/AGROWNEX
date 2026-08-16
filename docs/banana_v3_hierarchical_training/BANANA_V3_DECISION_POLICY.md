# Banana V3 Decision Policy

## 1. Principles

- Return an exact disease only when evidence is strong.
- Never force a prediction.
- Abstention is a valid and safe outcome.
- Symptom conflict blocks exact diagnosis.
- Freeze temperatures and thresholds before sealed evaluation.
- Do not tune after sealed evaluation.
- Preserve specific disease classes as the final product goal.

## 2. Required model outputs

For each learned stage record:

- raw logits;
- calibrated probabilities;
- predicted class;
- Top-1 confidence;
- Top-2 class and probability;
- Top-1 minus Top-2 margin;
- accepted or abstained;
- reason code.

## 3. Quality-gate reason codes

- `QG_PASS`
- `QG_WARNING`
- `QG_BLUR`
- `QG_EXPOSURE`
- `QG_OCCLUSION`
- `QG_SYMPTOM_TOO_SMALL`
- `QG_MULTIPLE_LEAVES`
- `QG_NON_LEAF`
- `QG_SCREENSHOT`
- `QG_COMPRESSION`
- `QG_CORRUPT`
- `QG_OTHER`

## 4. Healthy-gate decisions

- `HG_HEALTHY_ACCEPTED`
- `HG_DISEASED_ACCEPTED`
- `HG_UNCERTAIN`
- `HG_THRESHOLD_FAIL`
- `HG_MARGIN_FAIL`

Unfitted policy values:

```yaml
healthy_gate_confidence_threshold: TO_BE_SELECTED_FROM_CALIBRATION
healthy_gate_margin_threshold: TO_BE_SELECTED_FROM_CALIBRATION
diseased_gate_confidence_threshold: TO_BE_SELECTED_FROM_CALIBRATION
diseased_gate_margin_threshold: TO_BE_SELECTED_FROM_CALIBRATION
```

No final numeric threshold is selected in this specification.

## 5. Disease-class decisions

| Class | Confidence threshold | Margin threshold | Symptom agreement requirement |
|---|---|---|---|
| Cordana | `TO_BE_SELECTED_FROM_CALIBRATION` | `TO_BE_SELECTED_FROM_CALIBRATION` | `TO_BE_SELECTED_FROM_CALIBRATION` |
| Pestalotiopsis | `TO_BE_SELECTED_FROM_CALIBRATION` | `TO_BE_SELECTED_FROM_CALIBRATION` | `TO_BE_SELECTED_FROM_CALIBRATION` |
| Sigatoka | `TO_BE_SELECTED_FROM_CALIBRATION` | `TO_BE_SELECTED_FROM_CALIBRATION` | `TO_BE_SELECTED_FROM_CALIBRATION` |

## 6. Symptom agreement states

- `SYMPTOM_SUPPORTS`
- `SYMPTOM_NEUTRAL`
- `SYMPTOM_CONTRADICTS`
- `SYMPTOM_INCOMPLETE`
- `SYMPTOM_MIXED`
- `SYMPTOM_NOT_AVAILABLE`

Any future symptom-to-disease rule must state: **Verify against official source or qualified plant-pathology expert.**

## 7. Exact disease acceptance rule

```text
if (
    quality_passed
    AND crop_confirmed
    AND healthy_gate_diseased_accepted
    AND disease_confidence_passed
    AND disease_margin_passed
    AND symptom_state in [SYMPTOM_SUPPORTS, SYMPTOM_NEUTRAL]
    AND mixed_symptoms is false
):
    accept likely exact disease
else:
    abstain with the most specific safe reason code
```

The Top-1 class alone is never sufficient.

## 8. Abstention reasons

- `ABSTAIN_IMAGE_QUALITY`
- `ABSTAIN_CROP_MISMATCH`
- `ABSTAIN_HEALTHY_GATE_UNCERTAIN`
- `ABSTAIN_DISEASE_LOW_CONFIDENCE`
- `ABSTAIN_DISEASE_LOW_MARGIN`
- `ABSTAIN_SYMPTOM_CONFLICT`
- `ABSTAIN_MIXED_SYMPTOMS`
- `ABSTAIN_NON_DIAGNOSTIC`
- `ABSTAIN_MODEL_DISAGREEMENT`
- `ABSTAIN_RUNTIME_ERROR`

## 9. Farmer-facing response rules

**Healthy accepted**

> No clear disease pattern was detected in this image. This does not guarantee that the plant is healthy. Please monitor the plant and provide another clear image if symptoms continue.

**Exact disease accepted**

> The image is likely consistent with the accepted disease category. Verify against official source or qualified plant-pathology expert. Obtain verified advice before taking management action.

Never promote or recommend a pesticide brand.

**Abstained**

> The available evidence is not sufficient for a reliable disease result. Please provide a clearer image or the requested symptom details.

An abstention response must not show a disease name.

## 10. Logging

Record:

- `request_id`;
- timestamp;
- model and preprocessing versions;
- gate outputs;
- raw logits and calibrated probabilities where permitted;
- applied thresholds;
- symptom answers and missing states;
- final decision and reason code;
- image checksum where permitted.

Do not record unnecessary personal data. Farmer never pays. This policy does not authorize deployment or a Tamil Nadu field-accuracy claim.
