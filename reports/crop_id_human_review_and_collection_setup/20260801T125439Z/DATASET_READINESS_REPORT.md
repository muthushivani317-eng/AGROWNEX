# Dataset readiness report

The calculator uses explicit `crop_review_status=APPROVE` decisions only.
Candidates and quarantined images never count as approved.

| Class | Candidates | Reviewed | Approved | Status |
|---|---:|---:|---:|---|
| banana | 0 | 0 | 0 | NO_DATA |
| paddy | 0 | 0 | 0 | NO_DATA |
| cotton | 0 | 0 | 0 | NO_DATA |
| groundnut | 0 | 0 | 0 | NO_DATA |
| chilli | 4,032 | 0 | 0 | REVIEW_INCOMPLETE |
| redgram | 18 | 0 | 0 | REVIEW_INCOMPLETE |
| unknown_crop | 0 | 0 | 0 | NO_DATA |
| non_plant | 0 | 0 | 0 | NO_DATA |

Overall: `TRAINING_READINESS=NOT_READY`. This is research split readiness only,
not production readiness.
