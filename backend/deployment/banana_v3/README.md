# Banana V3 deployment

Build from the backend root only after the artifact verifier and complete test
suite pass:

```powershell
docker build -f deployment/banana_v3/Dockerfile -t agrowai-banana-v3 .
```

The container must receive the same authentication and HTTPS boundary as the
main AgrowAI API. It fails closed when artifacts are missing or mismatched.
It stores no raw image by default and returns localization keys, not prose.

Status: `PRODUCTION_INTEGRATED_FIELD_VALIDATION_IN_PROGRESS`. This is not an
official Tamil Nadu field-accuracy claim.
