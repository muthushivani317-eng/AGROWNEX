# Banana V3 Consent and Label Checklist

Technical field document in English; use Tamil-first explanations with participants.

## A. Before taking photos

- [ ] Purpose explained in the participant's preferred language.
- [ ] Farmer participation confirmed as voluntary.
- [ ] Farmer informed that the farmer pays nothing.
- [ ] Consent recorded.
- [ ] Permitted uses selected: training / internal research / publication / sealed testing.
- [ ] No pesticide-brand promotion or recommendation made.
- [ ] Coded farm identifier created.
- [ ] No unnecessary personal data collected.
- [ ] Exact coordinates omitted or handled privately with restricted access.
- [ ] Crop confirmed as banana.

Consent record ID: ____________________  
Withdrawal requested: Yes / No

## B. Capture identification

- [ ] District code: ____________________
- [ ] Farm code: ____________________
- [ ] Visit ID: ____________________
- [ ] Plant ID: ____________________
- [ ] Leaf ID: ____________________
- [ ] Capture group ID: ____________________
- [ ] Image IDs assigned: ____________________
- [ ] All related images share the same capture group.

## C. Required photo set

- [ ] Full plant view.
- [ ] Full leaf front.
- [ ] Symptom close-up.
- [ ] Leaf back where relevant.
- [ ] Environmental view.
- [ ] Original files retained.
- [ ] No filters or beauty mode.
- [ ] No screenshots or compressed messaging-app copies.
- [ ] No visible branded pesticide product.
- [ ] No severe blur.

Optional additional views: ________________________________________________

## D. Field observations

- [ ] Variety recorded: ____________________
- [ ] Growth stage recorded: ____________________
- [ ] Leaf position recorded: ____________________
- [ ] Lesion shape recorded: ____________________
- [ ] Lesion colour recorded: ____________________
- [ ] Halo recorded: present / absent / unknown
- [ ] Lesion distribution recorded: ____________________
- [ ] Edge involvement recorded: ____________________
- [ ] Possible mixed symptoms recorded: yes / no / unknown
- [ ] Environmental damage recorded: yes / no / unknown
- [ ] Pest signs recorded: yes / no / unknown
- [ ] Observation clearly marked provisional only.

Provisional observation: _________________________________________________

## E. Expert label review

- [ ] Image group reviewed independently.
- [ ] Model prediction was not used as ground truth.
- [ ] Decision selected: KEEP / RELABEL / EXCLUDE / UNCERTAIN / MULTIPLE_DISEASES_POSSIBLE / EXPERT_REVIEW_ONLY.
- [ ] Corrected label recorded if relabelled.
- [ ] Uncertainty recorded.
- [ ] Multiple-disease possibility recorded.
- [ ] Confidence recorded.
- [ ] Expert name and organization recorded.
- [ ] Review date recorded.
- [ ] Notes recorded.
- [ ] Disease definition verified against official source or qualified plant-pathology expert.

Expert label status: ____________________________________  
Corrected label, if applicable: __________________________  
Confidence: _____________________________________________  
Expert name: ____________________________________________  
Organization: ___________________________________________  
Review date: ____________________________________________  
Notes: __________________________________________________

**Verify against official source or qualified plant-pathology expert.**

## F. Dataset role and leakage

- [ ] Dataset role assigned before model development.
- [ ] Related images remain in the same role.
- [ ] Exact duplicate check completed.
- [ ] Perceptual duplicate check completed.
- [ ] Same-leaf group checked.
- [ ] Same-plant group checked.
- [ ] Same-visit group checked.
- [ ] Sealed field-test restrictions explained.
- [ ] Sealed test not used for training.
- [ ] Sealed test not used for calibration.
- [ ] Sealed test not used for threshold selection.
- [ ] Sealed test not used for debugging.
- [ ] Sealed test not used for model selection or preprocessing tuning.

## G. Final decision

- [ ] Approved for training candidate.
- [ ] Approved for development-validation candidate.
- [ ] Approved for calibration candidate.
- [ ] Approved for sealed field test.
- [ ] Expert review only.
- [ ] Excluded.
- [ ] Uncertain.

Final decision: __________________________________________  
Rejection code: __________________________________________  
Reviewer: ________________________________________________  
Date: ____________________________________________________  
Signature or digital confirmation: ________________________  
Notes: ___________________________________________________

## H. Farmer-facing safeguards

- [ ] No diagnosis shown from unverified data.
- [ ] No pesticide-brand recommendation.
- [ ] Uncertainty communicated clearly.
- [ ] Clearer photo requested when needed.
- [ ] Farmer never charged.
- [ ] Field result not presented as official accuracy.
