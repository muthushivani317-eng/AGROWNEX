# Restricted Redgram Runtime

Runtime ID: `redgram_mobilenetv3_small_v1_restricted`  
Model: `redgram_mobilenetv3_small_v1`  
Architecture: `MobileNetV3 Small`  
Frozen checkpoint epoch: `11`  
Checkpoint SHA-256: `5b95e1658f6bb0d83a3cef8b455533599482d102b86a326f184477f214269e72`  
Temperature: `3.1163787841796875`

## Runtime behaviour

- `redgram__healthy`: accepted only when the frozen rule passes.
- `redgram__sterility_mosaic`: accepted only when the frozen rule passes.
- `redgram__leaf_spot`: always abstains.
- Unknown classes, missing policies, invalid temperature and integrity
  failures must fail closed.

## Evidence limits

- The deployed safety policy answered 25 of 52 one-time provisional images and
  made zero errors among those 25 answered cases.
- It deliberately abstains whenever leaf spot is suspected rather than guessing.
- The underlying classifier's raw public-dataset provisional accuracy was 86.54%,
  but that number does not describe the deployed selective behavior by itself.
- This was a small, single-source public-dataset evaluation; real field performance
  is still being established under supervision.
- Selective coverage on that provisional set was 48.08%.
- The provisional test must not be rerun or used for tuning.
- This runtime is not a complete three-class automatic diagnosis model.
- It is not field validated.
- It is not Tamil Nadu accuracy.
- It is not farmer accuracy.
- It is not official accuracy.

Any disease wording, symptoms, treatment or prevention recommendations
must be **VERIFY AGAINST OFFICIAL SOURCE**.

Frozen at UTC: `20260730T112949Z`
