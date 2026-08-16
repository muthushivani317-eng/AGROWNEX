# Pending model artifact contract

Applies to crop identification, Coconut disease detection, Chilli disease detection, Redgram disease detection and Plant Identifier.

Promotion requires a verified dataset registry and licence, exact class mapping, fixed grouped splits, checkpoint hash, preprocessing contract, calibration artifact, abstention policy, ONNX opset 17 export, numerical parity receipt, bundle hashes, API adapter tests and release-readiness approval.

No placeholder, example configuration, approximate class mapping, reconstructed metric or unverified source content may satisfy a gate. Until every gate passes, the API must return a typed model-not-available response.

Expected per-model structure:

```text
artifacts/<model_id>/
  checkpoint/
  class_mapping.json
  preprocessing.json
  calibration.json
  abstention_policy.json
  onnx/model.onnx
  parity_receipt.json
  dataset_registry.json
  split_manifest.json
  SHA256SUMS.txt
  release_readiness.json
```
