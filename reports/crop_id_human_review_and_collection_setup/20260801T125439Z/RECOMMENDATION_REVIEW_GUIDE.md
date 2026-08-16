# Recommendation review guide

Run `python scripts/review_recommendation_packets.py --port 8766`.
The interface loads existing packets only and requires explicit English, Tamil,
agricultural, and conflict decisions. It displays runtime label, canonical
candidate, authority, source, printed page, exact passage, symptoms, immediate
actions, prevention, cultural/biological/chemical controls, safety notes, and
reviewer notes. Decisions are stored separately and source packet hashes are
recorded.

No facts are generated or approved automatically. Chemical candidates must keep
`VERIFY AGAINST OFFICIAL SOURCE`. Chilli Cercospora approval is hard-blocked until
a suitable authoritative source is supplied. Pesticide brands are not added.
