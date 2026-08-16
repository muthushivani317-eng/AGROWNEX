# Review tool usage

Use a local-only browser; both servers bind to `127.0.0.1`.

```powershell
python scripts/crop_id_human_review.py --crop chilli --port 8765
python scripts/crop_id_human_review.py --crop redgram --port 8765
python scripts/review_recommendation_packets.py --port 8766
python scripts/calculate_crop_id_readiness.py --output readiness.json
```

Image review shortcuts: left/right move, Escape closes, Ctrl+Enter saves. The
source manifest is immutable; decisions reside under `review_decisions/`.
