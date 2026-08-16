# Unknown-crop local collection guide

Status: `PACKAGE_READY_NO_PHOTOGRAPHS_COLLECTED`

Target multiple unsupported families: maize, coconut, blackgram, tomato, brinjal,
sugarcane, sesame, sunflower, onion, turmeric, sorghum, and pearl millet. Do not
collect banana, paddy, cotton, groundnut, chilli, or redgram into this class.

For every fine-grained crop, capture whole plant, leaf, stem, field context, and
close-up views across varied lighting, growth stages, and—with permission—multiple
farms. Do not publish location or farm identity by default. Do not capture an
identifiable farmer without recorded consent.

Ingest each crop separately:

```powershell
python scripts/ingest_local_crop_id_collection.py --kind unknown_crop --fine-label maize --input <folder>
```

The manifest preserves `fine_grained_crop_label=maize` and sets
`runtime_label=unknown_crop`. Hashing, EXIF removal, deduplication, and review
packet creation are automatic; approval is always human.
