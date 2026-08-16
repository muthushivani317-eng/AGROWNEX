"""Ingest self-captured crop-ID negatives into privacy-safe processed copies."""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil,tempfile
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image,ImageOps,UnidentifiedImageError

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_KINDS={"non_plant","unknown_crop"}
SUPPORTED={"banana","paddy","cotton","groundnut","chilli","redgram"}
EXT={".jpg",".jpeg",".png",".webp"}

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
def ahash(im:Image.Image)->str:
 px=list(ImageOps.grayscale(im).resize((8,8),Image.Resampling.LANCZOS).getdata()); avg=sum(px)/64
 return f"{sum((1<<i) for i,v in enumerate(px) if v>=avg):016x}"
def hamming(a:str,b:str)->int:
 return (int(a,16)^int(b,16)).bit_count()
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--kind",required=True,choices=sorted(ALLOWED_KINDS));p.add_argument("--input",type=Path,required=True);p.add_argument("--fine-label");a=p.parse_args()
 if not a.input.is_dir(): raise SystemExit("input directory does not exist")
 if a.kind=="unknown_crop" and (not a.fine_label or a.fine_label in SUPPORTED): raise SystemExit("unknown_crop requires a non-supported --fine-label")
 base=ROOT/"datasets/crop_identity_v2/local_collection"/a.kind; originals=base/"originals"; processed=base/"processed"; manifests=base/"manifests"; review=base/"review"
 for d in (originals,processed,manifests,review): d.mkdir(parents=True,exist_ok=True)
 rows=[]; seen={}
 for src in sorted(x for x in a.input.rglob("*") if x.is_file() and x.suffix.lower() in EXT):
  try:
   with Image.open(src) as im:
    im.load(); width,height=im.size; ph=ahash(im); digest=sha(src); image_id=digest[:24]
    op=originals/f"{image_id}{src.suffix.lower()}"; pp=processed/f"{image_id}.jpg"
    if not op.exists(): shutil.copy2(src,op)
    clean=ImageOps.exif_transpose(im).convert("RGB"); clean.save(pp,"JPEG",quality=95,optimize=True,exif=b"")
   family=next((fam for prior,fam in seen.items() if hamming(ph,prior)<=5),None)
   if family is None: family=f"phash:{ph}";seen[ph]=family
   rows.append({"image_id":image_id,"processed_path":str(pp),"original_path":str(op),"sha256":digest,"perceptual_hash":ph,"duplicate_family_id":family,"resolution":f"{width}x{height}","source":"SELF_CAPTURED","consent_status":"SELF_CAPTURED","fine_grained_crop_label":a.fine_label or "not_applicable","runtime_label":a.kind,"review_status":"PENDING_HUMAN_REVIEW","reviewer_notes":"","ingested_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")})
  except (UnidentifiedImageError,OSError): continue
 out=manifests/"ingestion_manifest.csv"; fields=list(rows[0]) if rows else ["image_id","processed_path","original_path","sha256","perceptual_hash","duplicate_family_id","resolution","source","consent_status","fine_grained_crop_label","runtime_label","review_status","reviewer_notes","ingested_at"]
 tmp=Path(tempfile.mkstemp(dir=manifests,suffix=".tmp")[1])
 with tmp.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 tmp.replace(out)
 (review/"review_packet.json").write_text(json.dumps({"notice":"INTERNAL NON-EXPERT REVIEW ONLY","rows":rows},indent=2),encoding="utf-8")
 print(json.dumps({"ingested":len(rows),"manifest":str(out),"exact_duplicate_count":len(rows)-len({r['sha256'] for r in rows}),"near_duplicate_family_count":len(rows)-len(set(r['duplicate_family_id'] for r in rows))},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
