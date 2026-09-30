# AgrowNex price relay (Cloud Run, Mumbai)

**Why:** data.gov.in and eNAM are hosted by NIC, which refuses connections from
non-Indian addresses. Our Railway worker runs in the US, so every price fetch
was reset in ~0.3 s. This relay runs in `asia-south1` (Mumbai) and forwards
the worker's requests. It only talks to `api.data.gov.in` and `enam.gov.in`,
and only with the secret token.

## 1. Check the sources from your laptop (India)

```powershell
python relay\check_sources.py
```

You should see `eNAM OK - <date>: N rows`. (Set `DATA_GOV_API_KEY` first to test data.gov.in too.)

## 2. Deploy (once)

Needs the Google Cloud CLI (`gcloud`) and a project with billing on (the
Firebase project on the Blaze plan works; usage fits the free tier).

```powershell
gcloud auth login
$TOKEN = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
gcloud run deploy agrownex-price-relay --source relay --region asia-south1 `
  --project YOUR_PROJECT_ID --allow-unauthenticated `
  --max-instances 2 --memory 256Mi --timeout 120 `
  --set-env-vars "RELAY_TOKEN=$TOKEN"
echo $TOKEN
```

`--allow-unauthenticated` is required so Railway can call it; the token is
what protects it (requests without it get 401, and it can only reach the two
price hosts).

## 3. Test the relay, then connect Railway

```powershell
python relay\check_sources.py --relay https://agrownex-price-relay-XXXX.a.run.app $TOKEN
```

Then set on **both** Railway services, AgrowAI-App and AgrowAI-Worker:

```
MARKET_RELAY_URL=https://agrownex-price-relay-XXXX.a.run.app
MARKET_RELAY_TOKEN=<the token>
```

The next worker run (every 2 hours) syncs Tamil Nadu from **both**
data.gov.in and eNAM. If one is down, the other still fills the prices.

## Tests

```
python -m pytest relay/tests
```
