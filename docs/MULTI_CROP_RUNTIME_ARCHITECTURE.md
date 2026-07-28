# Multi-Crop Runtime Architecture

The central registry is the model-independent source of crop availability. API responses expose crop status and limitations but redact internal runtime paths.

Runtime resolution is fail closed:

1. Normalize and validate the crop ID against the registry.
2. Require `FROZEN_RUNTIME_READY`, crop enablement, and disease-detection enablement.
3. Resolve only that crop's configured directory under the backend project root.
4. Reject sealed-test path components.
5. Require the complete runtime contract and verify every recorded SHA-256.
6. Load only crop-specific class mapping, preprocessing, calibration, thresholds, and abstention policy.

No resolver falls back to Banana or another crop. Banana's existing production runtime and behavior are not changed by this layer.

Agricultural content is outside this registry. Any such content requires the marker: `verify against official source`.
