# Required per-crop artifact layout

For each of `paddy`, `cotton`, `groundnut`, `chilli`, and `redgram`:

```text
<crop>/
  ARTIFACT_CONTRACT.json
  manifests/
    approved_manifest.csv
    split_manifest.csv
    leakage_report.json
  checkpoint/
    best.pt
  runtime/
    class_mapping.json
    runtime_config.json
  calibration/
    temperature.json
  thresholds/
    abstention_policy.json
  onnx/
    model.onnx
    parity_receipt.json
  bundle/
    artifact_manifest.json
    SHA256SUMS.txt
    bundle_verification.json
  integration/
    backend_adapter_receipt.json
    app_adapter_receipt.json
    test_receipt.json
```

Names describe the contract only. No empty artifact files are created because that could be mistaken for evidence. ONNX must use opset 17. Every immutable artifact must be covered by a lowercase SHA-256 receipt. No manual override is permitted.
