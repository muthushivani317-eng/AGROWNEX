# Legacy Joint Crop-Constrained Recalibration

Final decision: **READY_FOR_BACKEND_INTEGRATION**

All temperatures and thresholds were selected from calibration evidence only.
Development subsets were used only for development-labelled reporting.
Provisional-test material was not opened or used.

## Crop results

### Paddy

- Calibration: `{"calibration_logits_sha256": "d9981a2235a843be375d65e2b713225df6aad4e22870153f0a0ed4df8be77e9f", "checkpoint_sha256": "f9719d48d3a8d274d039f0bd36d78cc5fa1282a8f15b2f471ab27d5c043e8117", "crop": "paddy", "ece_after": 0.028447575825039446, "ece_before": 0.03742589972388991, "improved_nll": true, "nll_after": 0.3012893557022243, "nll_before": 0.3067891002455891, "optimizer": "torch.optim.LBFGS on log_temperature", "per_class_counts": {"paddy_healthy": 118, "rice_blast": 99, "rice_brown_leaf_spot": 163, "rice_tungro": 168}, "provisional_test_used": false, "sample_count": 548, "seed": 0, "source_split": "calibration", "temperature": 1.185621730465097}`
- Policy: `{"accepted": 455, "accepted_accuracy": 0.9494505494505494, "accepted_errors": 23, "confidence_threshold": 0.75, "coverage": 0.8302919708029197, "crop": "paddy", "flow": "crop_constrained", "margin_threshold": 0.0, "passes_gate": true, "provisional_test_used": false, "source_split": "calibration", "support": 548, "temperature": 1.185621730465097, "user_crop_confirmation_required": true, "worst_class_accepted_accuracy": 0.9078947368421053, "worst_class_coverage": 0.7676767676767676, "zero_accepted_classes": 0}`
- Development-only: `{"abstention_count": 232, "accepted_accuracy": 0.9444444444444444, "accepted_count": 864, "accepted_errors": 48, "coverage": 0.7883211678832117, "ece": 0.019410089385501993, "false_confident_errors": 48, "label": "DEVELOPMENT_ONLY_NOT_AN_OFFICIAL_ACCURACY_CLAIM", "macro_f1_all_predictions": 0.8691918644860013, "nll": 0.33160484900441106, "per_class": [{"class_index": 0, "class_name": "paddy_healthy", "f1": 0.9090909090909091, "precision": 0.9292035398230089, "recall": 0.8898305084745762, "support": 236}, {"class_index": 1, "class_name": "rice_blast", "f1": 0.8217054263565892, "precision": 0.8412698412698413, "recall": 0.803030303030303, "support": 198}, {"class_index": 2, "class_name": "rice_brown_leaf_spot", "f1": 0.8407079646017699, "precision": 0.8096590909090909, "recall": 0.8742331288343558, "support": 326}, {"class_index": 3, "class_name": "rice_tungro", "f1": 0.9052631578947369, "precision": 0.9148936170212766, "recall": 0.8958333333333334, "support": 336}], "sample_count": 1096}`

### Cotton

- Calibration: `{"calibration_logits_sha256": "d9981a2235a843be375d65e2b713225df6aad4e22870153f0a0ed4df8be77e9f", "checkpoint_sha256": "f9719d48d3a8d274d039f0bd36d78cc5fa1282a8f15b2f471ab27d5c043e8117", "crop": "cotton", "ece_after": 1.518341008477364e-12, "ece_before": 0.001172995130897747, "improved_nll": true, "nll_after": 1.5183936970276853e-12, "nll_before": 0.0012066243414073185, "optimizer": "torch.optim.LBFGS on log_temperature", "per_class_counts": {"cotton_fusarium_wilt": 24, "cotton_healthy": 13, "cotton_verticillium_wilt": 22}, "provisional_test_used": false, "sample_count": 59, "seed": 0, "source_split": "calibration", "temperature": 0.11945409775578275}`
- Policy: `{"accepted": 59, "accepted_accuracy": 1.0, "accepted_errors": 0, "confidence_threshold": 0.5, "coverage": 1.0, "crop": "cotton", "flow": "crop_constrained", "margin_threshold": 0.0, "passes_gate": true, "provisional_test_used": false, "source_split": "calibration", "support": 59, "temperature": 0.11945409775578275, "user_crop_confirmation_required": true, "worst_class_accepted_accuracy": 1.0, "worst_class_coverage": 1.0, "zero_accepted_classes": 0}`
- Development-only: `{"abstention_count": 0, "accepted_accuracy": 1.0, "accepted_count": 116, "accepted_errors": 0, "coverage": 1.0, "ece": 0.0, "false_confident_errors": 0, "label": "DEVELOPMENT_ONLY_NOT_AN_OFFICIAL_ACCURACY_CLAIM", "macro_f1_all_predictions": 1.0, "nll": 0.0, "per_class": [{"class_index": 0, "class_name": "cotton_fusarium_wilt", "f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 47}, {"class_index": 1, "class_name": "cotton_healthy", "f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 26}, {"class_index": 2, "class_name": "cotton_verticillium_wilt", "f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 43}], "sample_count": 116}`

### Groundnut

- Calibration: `{"calibration_logits_sha256": "d9981a2235a843be375d65e2b713225df6aad4e22870153f0a0ed4df8be77e9f", "checkpoint_sha256": "f9719d48d3a8d274d039f0bd36d78cc5fa1282a8f15b2f471ab27d5c043e8117", "crop": "groundnut", "ece_after": 1.8655077482776505e-12, "ece_before": 2.4963331335392525e-07, "improved_nll": true, "nll_after": 1.865442810704512e-12, "nll_before": 2.4963364554522275e-07, "optimizer": "torch.optim.LBFGS on log_temperature", "per_class_counts": {"groundnut_healthy": 45, "groundnut_rust": 8}, "provisional_test_used": false, "sample_count": 53, "seed": 0, "source_split": "calibration", "temperature": 0.5215946352798655}`
- Policy: `{"accepted": 53, "accepted_accuracy": 1.0, "accepted_errors": 0, "confidence_threshold": 0.5, "coverage": 1.0, "crop": "groundnut", "flow": "crop_constrained", "margin_threshold": 0.0, "passes_gate": true, "provisional_test_used": false, "source_split": "calibration", "support": 53, "temperature": 0.5215946352798655, "user_crop_confirmation_required": true, "worst_class_accepted_accuracy": 1.0, "worst_class_coverage": 1.0, "zero_accepted_classes": 0}`
- Development-only: `{"abstention_count": 0, "accepted_accuracy": 1.0, "accepted_count": 108, "accepted_errors": 0, "coverage": 1.0, "ece": 0.00013611048975747941, "false_confident_errors": 0, "label": "DEVELOPMENT_ONLY_NOT_AN_OFFICIAL_ACCURACY_CLAIM", "macro_f1_all_predictions": 1.0, "nll": 0.00013712081041657216, "per_class": [{"class_index": 0, "class_name": "groundnut_healthy", "f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 90}, {"class_index": 1, "class_name": "groundnut_rust", "f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 18}], "sample_count": 108}`

## ONNX

- Previous export inspection: `{"actual_opset": 18, "exists": true, "opset_imports": {"ai.onnx": 18}, "path": "/content/drive/MyDrive/AgrowAI_V1/exports/mobilenetv3_small_v1/agrowai_v1_classifier.onnx", "sha256": "a1f99ad3b6f429ed364c223da13f2bdf4556479512d01ea0f0460e990f7b8282"}`
- New export actual opset: `17`
- Synthetic parity passed: `True`
