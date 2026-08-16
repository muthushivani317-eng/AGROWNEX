# Chilli reproducible retraining package

This package trains `chilli_mobilenetv3_small_v2` from the frozen, family-grouped manifest. It is provisional public-dataset research only and never enables farmer inference.

Execution order: verify inputs; train on `training`; select on `development_validation`; export calibration logits and fit temperature/abstention on `calibration`; freeze; perform exactly one `provisional_test` evaluation; package and verify the runtime.

The verifier skips sealed `provisional_test` image bytes unless the explicit one-time evaluation flag is supplied. Upload this folder and its `images/` tree to Google Drive without altering relative paths.
