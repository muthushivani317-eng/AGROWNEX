"""Local, fail-closed review server for crop-identification candidates.

The source manifest is never edited. Human decisions are written to a separate
JSON file with atomic replacement, making review resumable and auditable.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import os
import tempfile
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "datasets/crop_identity_v2/manifests/candidate_review_manifest.csv"
DECISION_DIR = ROOT / "datasets/crop_identity_v2/review_decisions"
ALLOWED_CROPS = {"chilli", "redgram"}
DECISIONS = {
    "APPROVE", "REJECT_WRONG_CLASS", "REJECT_LOW_QUALITY", "REJECT_DUPLICATE",
    "REJECT_AUGMENTED", "REJECT_SCREENSHOT", "REJECT_COLLAGE", "REJECT_WATERMARK",
    "REJECT_LICENCE", "QUARANTINE_UNCERTAIN",
}
NOTICE = "INTERNAL NON-EXPERT REVIEW ONLY — OFFICIAL AGRICULTURAL EXPERT VERIFICATION NOT COMPLETED"


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_rows(crop: str) -> list[dict[str, str]]:
    if crop not in ALLOWED_CROPS:
        raise ValueError("crop must be chilli or redgram")
    with MANIFEST.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("proposed_class") == crop]
    for row in rows:
        # The acquisition manifest has crop-level provenance but no independently
        # verified disease label. Preserve that uncertainty instead of deriving a
        # disease from folder names.
        row["proposed_disease_label"] = row.get("proposed_disease_label") or "UNAVAILABLE_NOT_PROVEN"
    if crop == "redgram" and len(rows) != 18:
        raise RuntimeError(f"expected 18 Redgram candidates, found {len(rows)}")
    if crop == "chilli" and len(rows) != 4032:
        raise RuntimeError(f"expected 4032 Chilli candidates, found {len(rows)}")
    return rows


def decision_path(crop: str) -> Path:
    return DECISION_DIR / f"{crop}_review_decisions.json"


def load_decisions(crop: str) -> dict[str, dict]:
    path = decision_path(crop)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


HTML = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>AgrowAI internal image review</title><style>
body{font-family:system-ui;margin:0;background:#101812;color:#eef7ef}header{position:sticky;top:0;background:#661b1b;padding:10px;z-index:3}main{padding:12px}.controls{display:flex;gap:8px;flex-wrap:wrap}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}.card{background:#1b2a1e;padding:6px;border:2px solid transparent}.card.reviewed{border-color:#58a66a}.card img{width:100%;height:120px;object-fit:contain;background:#000}.modal{position:fixed;inset:0;background:#000d;display:none;z-index:4;padding:3vh}.modal.open{display:block}.modal img{max-width:55vw;max-height:82vh}.panel{display:flex;gap:18px;height:94vh}.meta{overflow:auto;flex:1}.warn{color:#ffd47a}button,select,input,textarea{font:inherit;padding:7px}textarea{width:95%;height:80px}.small{font-size:12px;overflow-wrap:anywhere}</style></head>
<body><header><b>INTERNAL NON-EXPERT REVIEW ONLY</b><br>OFFICIAL AGRICULTURAL EXPERT VERIFICATION NOT COMPLETED</header>
<main><div class="controls"><select id="label"><option value="">all labels</option></select><select id="quarantine"><option value="">all quarantine states</option></select><input id="family" placeholder="duplicate family"><input id="source" placeholder="source dataset"><button onclick="applyFilters()">Filter</button><button onclick="exportData()">Export CSV + JSON</button></div><p id="summary"></p><div id="grid" class="grid"></div></main>
<div id="modal" class="modal"><div class="panel"><img id="full"><div class="meta"><button onclick="closeModal()">Close (Esc)</button><button onclick="move(-1)">Previous (←)</button><button onclick="move(1)">Next (→)</button><pre id="details" class="small"></pre><p><b>Crop-level decision</b></p><select id="cropDecision"></select><p><b>Disease-label decision</b> (may remain quarantined while crop is approved)</p><select id="diseaseDecision"></select><textarea id="notes" placeholder="Reviewer notes"></textarea><br><button onclick="save()">Save (Ctrl+Enter)</button><p id="saveStatus"></p></div></div></div>
<script>
const CROP='__CROP__', allowed=__DECISIONS__; let rows=[],shown=[],idx=0,decisions={};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function boot(){let d=await(await fetch('/api/rows')).json(); rows=d.rows; decisions=d.decisions; let ls=[...new Set(rows.map(x=>x.proposed_disease_label))],qs=[...new Set(rows.map(x=>x.source_screening_decision))]; label.innerHTML+=""+ls.map(x=>`<option>${esc(x)}</option>`).join('');quarantine.innerHTML+=""+qs.map(x=>`<option>${esc(x)}</option>`).join(''); for(let id of ['cropDecision','diseaseDecision'])document.getElementById(id).innerHTML='<option value="">UNREVIEWED</option>'+allowed.map(x=>`<option>${x}</option>`).join(''); applyFilters(); let last=localStorage.getItem('agrowai-review-'+CROP); if(last){let n=shown.findIndex(x=>x.image_id===last);if(n>=0)openAt(n)}}
function applyFilters(){shown=rows.filter(r=>(!label.value||r.proposed_disease_label===label.value)&&(!quarantine.value||r.source_screening_decision===quarantine.value)&&(!family.value||r.duplicate_family_id.includes(family.value))&&(!source.value||r.source_dataset.includes(source.value))); render()}
function render(){summary.textContent=`${shown.length} visible / ${rows.length}; ${Object.keys(decisions).length} reviewed. ${CROP==='redgram'?'REDGRAM_CLASS_DATA_INSUFFICIENT':''}`;grid.innerHTML=shown.map((r,i)=>`<div class="card ${decisions[r.image_id]?'reviewed':''}" onclick="openAt(${i})"><img loading="lazy" src="/image?id=${encodeURIComponent(r.image_id)}"><b>${esc(r.proposed_class)}</b><div class="small">${esc(r.source_dataset)}<br>${esc(r.quality_warnings)}<br>${esc(r.duplicate_family_id)}</div></div>`).join('')}
function openAt(i){idx=Math.max(0,Math.min(shown.length-1,i));let r=shown[idx],d=decisions[r.image_id]||{}; full.src='/image?id='+encodeURIComponent(r.image_id);details.textContent=JSON.stringify(r,null,2);cropDecision.value=d.crop_review_status||'';diseaseDecision.value=d.disease_review_status||'';notes.value=d.reviewer_notes||'';modal.classList.add('open');localStorage.setItem('agrowai-review-'+CROP,r.image_id)}
function closeModal(){modal.classList.remove('open')} function move(n){openAt(idx+n)}
async function save(){let r=shown[idx],body={image_id:r.image_id,crop_review_status:cropDecision.value,disease_review_status:diseaseDecision.value,reviewer_notes:notes.value};let q=await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let d=await q.json();if(!q.ok){saveStatus.textContent=d.error;return}decisions[r.image_id]=d.record;saveStatus.textContent='Saved';render();move(1)}
function exportData(){location.href='/api/export?format=json';setTimeout(()=>location.href='/api/export?format=csv',400)}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();if(e.key==='ArrowLeft')move(-1);if(e.key==='ArrowRight')move(1);if(e.ctrlKey&&e.key==='Enter')save()});boot();
</script></body></html>'''


class ReviewHandler(BaseHTTPRequestHandler):
    rows: list[dict[str, str]] = []
    crop = ""

    def _json(self, value: object, status: int = 200) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        if u.path == "/":
            raw = HTML.replace("__CROP__", self.crop).replace("__DECISIONS__", json.dumps(sorted(DECISIONS))).encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if u.path == "/api/rows":
            self._json({"notice": NOTICE, "rows": self.rows, "decisions": load_decisions(self.crop)}); return
        if u.path == "/image":
            image_id = parse_qs(u.query).get("id", [""])[0]
            row = next((r for r in self.rows if r["image_id"] == image_id), None)
            if not row: self.send_error(404); return
            path = Path(row["original_path"])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                self.send_error(409, "missing image or SHA-256 mismatch"); return
            raw = path.read_bytes(); self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if u.path == "/api/export":
            fmt = parse_qs(u.query).get("format", ["json"])[0]; decisions = load_decisions(self.crop)
            records = [{**r, **decisions.get(r["image_id"], {})} for r in self.rows]
            if fmt == "csv":
                import io
                out=io.StringIO(); fields=list(records[0]) if records else []
                w=csv.DictWriter(out,fieldnames=fields); w.writeheader(); w.writerows(records); raw=out.getvalue().encode("utf-8-sig"); ctype="text/csv"
            else: raw=json.dumps(records,ensure_ascii=False,indent=2).encode(); ctype="application/json"
            self.send_response(200); self.send_header("Content-Type",ctype); self.send_header("Content-Disposition",f'attachment; filename="{self.crop}_review_export.{fmt}"'); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/decision": self.send_error(404); return
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size > 65536: raise ValueError("request too large")
            body=json.loads(self.rfile.read(size)); image_id=str(body.get("image_id",""))
            if image_id not in {r["image_id"] for r in self.rows}: raise ValueError("unknown image_id")
            crop_status=body.get("crop_review_status",""); disease_status=body.get("disease_review_status","")
            if crop_status not in DECISIONS or disease_status not in DECISIONS: raise ValueError("both review decisions must be explicit allowed values")
            notes=str(body.get("reviewer_notes","")).strip()
            if len(notes)>4000: raise ValueError("reviewer notes exceed 4000 characters")
            record={"image_id":image_id,"crop_review_status":crop_status,"disease_review_status":disease_status,"reviewer_notes":notes,"review_timestamp":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"review_scope":"INTERNAL_NON_EXPERT"}
            data=load_decisions(self.crop); data[image_id]=record; atomic_json(decision_path(self.crop),data); self._json({"record":record})
        except (ValueError,json.JSONDecodeError) as exc: self._json({"error":str(exc)},400)


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--crop",required=True,choices=sorted(ALLOWED_CROPS)); p.add_argument("--port",type=int,default=8765); args=p.parse_args()
    ReviewHandler.crop=args.crop; ReviewHandler.rows=load_rows(args.crop)
    print(NOTICE); print(f"Reviewing {len(ReviewHandler.rows)} {args.crop} candidates at http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1",args.port),ReviewHandler).serve_forever(); return 0

if __name__ == "__main__": raise SystemExit(main())
