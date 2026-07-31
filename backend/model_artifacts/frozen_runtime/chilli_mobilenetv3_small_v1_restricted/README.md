# Canonical Restricted Chilli Runtime

Runtime ID: `chilli_mobilenetv3_small_v1_restricted`  
Runtime status: `RESTRICTED_FAIL_CLOSED_RUNTIME`  
Model: `chilli_mobilenetv3_small_v1`  
Architecture: `MobileNetV3 Small`  
Checkpoint epoch: `5`  
Checkpoint SHA-256: `adab7c3eefa009b78e1c9d335fc088d74b5f2b456eb7196950da385ed761ec26`  
Temperature: `1.0000321865081787`  
Minimum confidence: `0.99`  
Minimum margin: `0.99`  

## Canonical class registry

0. `chilli__bacterial_spot`
1. `chilli__cercospora_leaf_spot`
2. `chilli__healthy`
3. `chilli__leaf_curl_virus`

## Fail-closed acceptance policy

A result is accepted only when both conditions pass:

- calibrated confidence is at least `0.99`;
- calibrated margin is at least `0.99`.

Every other result must abstain.

## Evidence

- Development: 180 images, 100% Top-1 and macro F1.
- Calibration: 91 images.
- Frozen policy accepted 90 images with zero accepted errors.
- One-time provisional test: 89 images.
- Raw provisional accuracy: 97.75%.
- Raw provisional macro F1: 96.21%.
- Frozen policy accepted 87 images and abstained on 2.
- Accepted provisional errors: 0.

## Restrictions

These are public-dataset provisional results.

This package is not evidence of:

- Tamil Nadu field accuracy;
- farmer-photo accuracy;
- official agricultural validation;
- expert verification;
- production readiness without backend, mobile and safety testing.

The provisional test must not be rerun or used for tuning.

Any symptom, disease explanation, treatment, prevention or pesticide
recommendation must be **VERIFY AGAINST OFFICIAL SOURCE**.

Frozen at UTC: `20260730T132857Z`
