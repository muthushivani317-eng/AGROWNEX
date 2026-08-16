"""Calculate research split readiness from explicit human approvals only."""
from __future__ import annotations
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CLASSES=("banana","paddy","cotton","groundnut","chilli","redgram","unknown_crop","non_plant")
def calculate()->dict:
 rows=[]
 source=ROOT/"datasets/crop_identity_v2/manifests/candidate_review_manifest.csv"
 if source.exists():
  with source.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
 decisions={}
 for p in (ROOT/"datasets/crop_identity_v2/review_decisions").glob("*_review_decisions.json") if (ROOT/"datasets/crop_identity_v2/review_decisions").exists() else []:decisions.update(json.loads(p.read_text(encoding="utf-8")))
 for kind in ("unknown_crop","non_plant"):
  p=ROOT/"datasets/crop_identity_v2/local_collection"/kind/"manifests/ingestion_manifest.csv"
  if p.exists():
   with p.open(encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):r["proposed_class"]=kind;rows.append(r);decisions[r["image_id"]]={"crop_review_status":r.get("review_status","")}
 report={}
 for cls in CLASSES:
  candidates=[r for r in rows if r.get("proposed_class")==cls]
  approved=[r for r in candidates if decisions.get(r.get("image_id",""),{}).get("crop_review_status")=="APPROVE"]
  reviewed=sum(1 for r in candidates if r.get("image_id") in decisions)
  tags=Counter(t.strip().lower() for r in approved for t in (r.get("view_tags") or "").split(";") if t.strip())
  sources={r.get("source_dataset") or r.get("source") for r in approved if r.get("source_dataset") or r.get("source")}
  groups={r.get("duplicate_family_id") for r in approved if r.get("duplicate_family_id")}
  if not candidates:status="NO_DATA"
  elif reviewed<len(candidates):status="REVIEW_INCOMPLETE"
  elif len(approved)<100 or len(groups)<50:status="INSUFFICIENT"
  elif len(sources)<2:status="BASELINE_RESEARCH_ONLY"
  else:status="READY_FOR_SPLIT_DESIGN"
  report[cls]={"status":status,"candidate_images":len(candidates),"reviewed_images":reviewed,"approved_crop_id_images":len(approved),"independent_source_count":len(sources),"duplicate_family_count":len(groups),"trainable_unique_groups":len(groups),"whole_plant_count":tags["whole_plant"],"leaf_count":tags["leaf"],"field_view_count":tags["field_view"],"healthy_count":tags["healthy"],"diseased_count":tags["diseased"],"low_quality_safety_count":tags["low_quality_safety"],"geographic_diversity_known_count":sum(bool(r.get("geographic_source")) for r in approved)}
 return {"scope":"research split readiness only; never production readiness","classes":report,"training_readiness":"NOT_READY" if any(v["status"] in {"NO_DATA","INSUFFICIENT","REVIEW_INCOMPLETE"} for v in report.values()) else "READY_FOR_SPLIT_DESIGN"}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path);a=p.parse_args();d=calculate();raw=json.dumps(d,indent=2)
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(raw+"\n",encoding="utf-8")
 print(raw);return 0
if __name__=="__main__":raise SystemExit(main())
