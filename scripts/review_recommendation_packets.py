"""Local structured reviewer for existing recommendation evidence packets."""
from __future__ import annotations
import argparse,json,os,tempfile
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKETS=ROOT/"recommendation_knowledge/review_packets"
OUT=ROOT/"recommendation_knowledge/reviewer_decisions"
STATUSES={"APPROVE","REJECT","NEEDS_BETTER_SOURCE","CONFLICT_REQUIRES_RESOLUTION","AGRICULTURAL_REVIEW_REQUIRED","TAMIL_REVIEW_REQUIRED"}
FIELDS=["runtime_label","candidate_canonical_disease","source_authority","source_file","page_number","exact_passage","symptom_candidate","immediate_action_candidate","prevention_candidate","cultural_control_candidate","biological_control_candidate","chemical_control_candidate","safety_note_candidate","english_review_status","tamil_review_status","agricultural_review_status","conflict_status","reviewer_notes"]
HTML='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Recommendation review</title><style>body{font-family:system-ui;max-width:1000px;margin:auto;padding:20px;background:#142018;color:#eef}header{background:#6b1d1d;padding:15px}label{display:block;font-weight:bold;margin-top:12px}textarea,input,select{box-sizing:border-box;width:100%;padding:8px}textarea{height:100px}pre{white-space:pre-wrap;background:#07120a;padding:12px}</style><header>INTERNAL NON-EXPERT REVIEW ONLY<br>OFFICIAL AGRICULTURAL EXPERT VERIFICATION NOT COMPLETED</header><select id="pick"></select><div id="form"></div><button onclick="save()">Save explicit human review</button><pre id="msg"></pre><script>
let packets=[],current;const fields=__FIELDS__,statuses=__STATUSES__;async function boot(){packets=await(await fetch('/api/packets')).json();pick.innerHTML=packets.map((p,i)=>`<option value="${i}">${p.runtime_label}</option>`).join('');pick.onchange=render;render()}
function render(){current=packets[+pick.value||0];form.innerHTML=fields.map(f=>{let v=current[f]??'';if(f.endsWith('_status')||f==='conflict_status')return `<label>${f}</label><select id="${f}"><option value="">UNREVIEWED</option>${statuses.map(s=>`<option>${s}</option>`).join('')}</select>`;return `<label>${f}</label><textarea id="${f}" ${['runtime_label','source_authority','source_file','page_number','exact_passage'].includes(f)?'readonly':''}>${String(Array.isArray(v)?v.join('\n'):v).replaceAll('&','&amp;').replaceAll('<','&lt;')}</textarea>`}).join('');}
async function save(){let body={};for(let f of fields)body[f]=document.getElementById(f).value;let r=await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});msg.textContent=await r.text()};boot()</script>'''

def inventory()->list[dict]:
 out=[]
 for crop in ("banana","paddy","cotton","groundnut","chilli","redgram"):
  for p in sorted((PACKETS/crop).glob("*/packet.json")):
   d=json.loads(p.read_text(encoding="utf-8")); ev=(d.get("candidate_evidence") or [{}])[0]
   chemical=d.get("chemical_control_candidate") or []
   out.append({"runtime_label":d.get("exact_runtime_label") or p.parent.name,"candidate_canonical_disease":d.get("candidate_canonical_disease"),"source_authority":ev.get("source_authority","UNRESOLVED"),"source_file":ev.get("source_filename",""),"page_number":ev.get("printed_page") or ev.get("page_number"),"exact_passage":ev.get("exact_relevant_passage",""),"symptom_candidate":d.get("symptom_candidate",[]),"immediate_action_candidate":d.get("immediate_action_candidate",[]),"prevention_candidate":d.get("prevention_candidate",[]),"cultural_control_candidate":d.get("cultural_control_candidate",[]),"biological_control_candidate":d.get("biological_control_candidate",[]),"chemical_control_candidate":chemical,"safety_note_candidate":list(dict.fromkeys((d.get("safety_note_candidate") or [])+(["VERIFY AGAINST OFFICIAL SOURCE"] if chemical else []))),"english_review_status":"","tamil_review_status":"","agricultural_review_status":"","conflict_status":"","reviewer_notes":"","packet_path":str(p)})
 return out
def atomic(path:Path,data:dict)->None:
 path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=path.parent,suffix=".tmp")
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write("\n")
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
class H(BaseHTTPRequestHandler):
 packets=inventory()
 def sendj(self,d,code=200):
  b=json.dumps(d,ensure_ascii=False).encode();self.send_response(code);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):
  if self.path=="/":
   b=HTML.replace("__FIELDS__",json.dumps(FIELDS)).replace("__STATUSES__",json.dumps(sorted(STATUSES))).encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
  elif self.path=="/api/packets":self.sendj(self.packets)
  else:self.send_error(404)
 def do_POST(self):
  if self.path!="/api/decision":self.send_error(404);return
  try:
   n=int(self.headers.get("Content-Length","0"));d=json.loads(self.rfile.read(n));label=d.get("runtime_label","")
   source=next((p for p in self.packets if p["runtime_label"]==label),None)
   if not source:raise ValueError("unknown runtime_label")
   for f in ("english_review_status","tamil_review_status","agricultural_review_status","conflict_status"):
    if d.get(f) not in STATUSES:raise ValueError(f"{f} requires an explicit allowed status")
   if "cercospora" in label and d.get("agricultural_review_status")=="APPROVE":raise ValueError("Chilli Cercospora remains blocked pending authoritative source")
   if d.get("chemical_control_candidate") and "VERIFY AGAINST OFFICIAL SOURCE" not in d.get("safety_note_candidate",""):raise ValueError("chemical content requires VERIFY AGAINST OFFICIAL SOURCE")
   record={k:d.get(k,"") for k in FIELDS};record.update({"review_timestamp":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"source_packet_sha256":__import__('hashlib').sha256(Path(source['packet_path']).read_bytes()).hexdigest()})
   atomic(OUT/f"{label}.json",record);self.sendj(record)
  except (ValueError,json.JSONDecodeError) as e:self.sendj({"error":str(e)},400)
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--port",type=int,default=8766);a=p.parse_args();print(f"Review {len(H.packets)} packets at http://127.0.0.1:{a.port}");ThreadingHTTPServer(("127.0.0.1",a.port),H).serve_forever();return 0
if __name__=="__main__":raise SystemExit(main())
