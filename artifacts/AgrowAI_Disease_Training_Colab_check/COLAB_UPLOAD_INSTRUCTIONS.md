# AgrowAI disease-model Colab bundle

This bundle contains reproducible training packages for chilli and redgram.
It does **not** include the training images or any model weights.

## Upload to Google Drive

1. In Google Drive, create `MyDrive/AgrowAI_V1`.
2. Upload this zip file there and extract it.
3. For each crop, place the source images below its package directory so that
   every path in `frozen_split_manifest.csv` exists and has the recorded SHA-256.
4. In Colab select **Runtime -> Change runtime type -> T4 GPU**.
5. Open the appropriate `AGROWAI_*_TRAINING.ipynb` notebook and run cells in order.

The notebooks verify every non-sealed image before training. They refuse to
evaluate the one-time provisional test split until `ALLOW_ONE_TIME_PROVISIONAL_TEST`
is deliberately changed to `True`, after training, calibration, and thresholds
are frozen. Do not use personal photos as training images; keep them only as a
separate regression/challenge set.

Successful training is still provisional and does not authorize farmer-facing
predictions. Send the generated `outputs/` folder back for independent review
and integration.
