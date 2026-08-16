from __future__ import annotations

import csv, hashlib, json, math, shutil, time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

ROOT=Path(__file__).resolve().parents[2]
PIPE=ROOT/"agrowai_autonomous_pipeline"; DATA=PIPE/"CROP_ID_EMERGENCY_INTERNAL_SIX_CLASS"; CAND=DATA/"candidate_mobilenetv3_small"
EVID=PIPE/"EVIDENCE"/"CROP_ID_EMERGENCY_INTERNAL_SIX_CLASS"; RUNTIME=ROOT/"backend"/"model_artifacts"/"frozen_runtime"/"crop_identity_six_class_internal_v1"
CLASSES=["banana","paddy","cotton","groundnut","chilli","redgram"]; C2I={c:i for i,c in enumerate(CLASSES)}
MEAN=[.485,.456,.406]; STD=[.229,.224,.225]

def save(path,value): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
class DS(Dataset):
 def __init__(self,rows): self.rows=rows; self.tf=transforms.Compose([transforms.Resize(184),transforms.CenterCrop(160),transforms.ToTensor(),transforms.Normalize(MEAN,STD)])
 def __len__(self): return len(self.rows)
 def __getitem__(self,i):
  r=self.rows[i]
  with Image.open(PIPE/r["path"]) as im: x=self.tf(im.convert("RGB"))
  return x,C2I[r["crop_class"]],r
def collate(b): return torch.stack([x[0] for x in b]),torch.tensor([x[1] for x in b]),[x[2] for x in b]
def model():
 m=models.mobilenet_v3_small(weights=None);m.classifier[3]=nn.Linear(m.classifier[3].in_features,6);ck=torch.load(CAND/"best.pt",map_location="cpu",weights_only=False);m.load_state_dict(ck["model_state_dict"]);m.eval();return m
def infer(m,rows):
 ys=[];zs=[];meta=[]
 with torch.inference_mode():
  for x,y,r in DataLoader(DS(rows),batch_size=64,shuffle=False,num_workers=2,collate_fn=collate): ys.append(y);zs.append(m(x));meta+=r
 return torch.cat(zs),torch.cat(ys),meta
def probs(logits,t): return torch.softmax(logits/t,1)
def nll(logits,y,t=1.): return float(nn.functional.cross_entropy(logits/t,y))
def ece(p,y,bins=15):
 c,pred=p.max(1); total=0.
 for lo in torch.linspace(0,1,bins+1)[:-1]:
  hi=lo+1/bins;mask=(c>=lo)&(c<(hi if hi<1 else hi+1e-6))
  if mask.any(): total+=float(mask.float().mean()*abs(c[mask].mean()-(pred[mask]==y[mask]).float().mean()))
 return total
def metric(y,pred):
 cm=torch.zeros(6,6,dtype=torch.long)
 for a,b in zip(y,pred,strict=True):cm[int(a),int(b)]+=1
 v=cm.float();s=v.sum(1);pr=v.sum(0);tp=v.diag();precision=tp/pr.clamp_min(1);recall=tp/s.clamp_min(1);f1=2*precision*recall/(precision+recall).clamp_min(1e-12)
 return {"accuracy":float(tp.sum()/v.sum()),"balanced_accuracy":float(recall.mean()),"macro_precision":float(precision.mean()),"macro_recall":float(recall.mean()),"macro_f1":float(f1.mean()),"per_class":{c:{"precision":float(precision[i]),"recall":float(recall[i]),"f1":float(f1[i]),"support":int(s[i])}for i,c in enumerate(CLASSES)},"confusion_matrix":cm.tolist()}
def fit_temperature(z,y):
 before=nll(z,y); best=(before,1.0)
 for t in np.geomspace(.25,5,1000):
  value=nll(z,y,float(t))
  if value<best[0]:best=(value,float(t))
 if best[0]>before+1e-8:raise RuntimeError("CALIBRATION_NLL_WORSENED")
 return best[1],before,best[0]
def choose_threshold(p,y):
 order=p.argsort(1,descending=True);pred=order[:,0];conf=p.gather(1,order[:,:1]).squeeze();margin=conf-p.gather(1,order[:,1:2]).squeeze();best=None
 for ct in np.arange(.50,.991,.01):
  for mt in np.arange(0,.51,.05):
   accept=(conf>=ct)&(margin>=mt); cover=float(accept.float().mean()); ok=True; pcs={}
   for i,c in enumerate(CLASSES):
    mask=y==i; a=accept&mask; acc=float((pred[a]==y[a]).float().mean()) if a.any() else 0.; cov=float(a.sum()/mask.sum());pcs[c]={"coverage":cov,"accepted_accuracy":acc,"accepted":int(a.sum())}
    if cov<.50 or acc<.90:ok=False
   if ok and (best is None or cover>best[0]):best=(cover,float(ct),float(mt),pcs)
 if best is None:return .99,.50,{},"NO_GATE_SATISFIED"
 return best[1],best[2],best[3],"CALIBRATION_GATE_SATISFIED"
def main():
 receipt=DATA/"sealed_test_receipt.json"
 if receipt.exists():raise RuntimeError("SEALED_TEST_ALREADY_CONSUMED_REFUSAL")
 manifest=json.loads((DATA/"split_manifest.json").read_text(encoding="utf-8")); assert manifest["sealed_test_access_count"]==0
 m=model(); cal=[r for r in manifest["rows"] if r["split"]=="calibration"]; z,y,meta=infer(m,cal);t,before,after=fit_temperature(z,y);p=probs(z,t);ct,mt,per,gate=choose_threshold(p,y)
 calibration={"split":"calibration","rows":len(y),"temperature":t,"nll_before":before,"nll_after":after,"nll_improved":after<=before+1e-8,"ece_before":ece(probs(z,1),y),"ece_after":ece(p,y),"multiclass_brier_after":float(((p-nn.functional.one_hot(y,6))**2).sum(1).mean()),"confidence_threshold":ct,"margin_threshold":mt,"threshold_gate":gate,"per_class_gate":per}
 save(DATA/"calibration.json",calibration);save(DATA/"abstention_thresholds.json",{"confidence_threshold":ct,"margin_threshold":mt,"fallback":"CROP_IDENTITY_UNCERTAIN","fit_split":"calibration","class_order":CLASSES})
 frozen={"frozen_at_utc":datetime.now(UTC).isoformat(),"model_sha256":sha(CAND/"best.pt"),"manifest_sha256":sha(DATA/"split_manifest.json"),"class_order_sha256":sha(DATA/"class_order.json"),"calibration_sha256":sha(DATA/"calibration.json"),"threshold_sha256":sha(DATA/"abstention_thresholds.json"),"sealed_test_access_count":0,"tuning_complete":True,"official_accuracy_claim":False,"scope":"INTERNAL_ONLY"};save(DATA/"pre_test_freeze.json",frozen)
 # Safety: unreadable items are correctly rejected at decode; readable excluded evidence must abstain.
 safety=json.loads((DATA/"safety_manifest.json").read_text(encoding="utf-8"))["rows"]; readable=[];decode_rejected=0
 for r in safety:
  try:
   with Image.open(PIPE/r["path"]) as im: im.verify()
   readable.append(r)
  except Exception:decode_rejected+=1
 accepted=[]
 if readable:
  sz,sy,sm=infer(m,readable);sp=probs(sz,t);o=sp.argsort(1,descending=True);sc=sp.gather(1,o[:,:1]).squeeze();mar=sc-sp.gather(1,o[:,1:2]).squeeze();mask=(sc>=ct)&(mar>=mt)
  accepted=[{"image_id":sm[i]["image_id"],"predicted":CLASSES[int(o[i,0])],"confidence":float(sc[i]),"margin":float(mar[i]),"exclusion_reasons":sm[i].get("exclusion_reasons",[])}for i in range(len(sm))if mask[i]]
 safety_result={"rows":len(safety),"decode_rejected":decode_rejected,"readable_excluded_rows":len(readable),"incorrectly_accepted":len(accepted),"incorrect_acceptance_rate":len(accepted)/max(1,len(readable)),"status":"PASS" if not accepted else "PARTIAL","accepted_details":accepted,"limitations":["No independently licensed unsupported-crop or non-plant benchmark is available.","Safety evidence is excluded repository data, not a field benchmark."]};save(DATA/"safety_results.json",safety_result)
 # Exactly-once sealed evaluation, only after all tuning records are frozen.
 event={"opened_at_utc":datetime.now(UTC).isoformat(),"access_count":1,"purpose":"ONE_TIME_PROVISIONAL_INTERNAL_EVALUATION","pre_test_freeze_sha256":sha(DATA/"pre_test_freeze.json")};save(receipt,event)
 test=[r for r in manifest["rows"] if r["split"]=="sealed_test"];tz,ty,tm=infer(m,test);tp=probs(tz,t);order=tp.argsort(1,descending=True);pred=order[:,0];conf=tp.gather(1,order[:,:1]).squeeze();margin=conf-tp.gather(1,order[:,1:2]).squeeze();accept=(conf>=ct)&(margin>=mt);base=metric(ty,pred);base.update({"top2_accuracy":float((order[:,:2]==ty[:,None]).any(1).float().mean()),"nll":nll(tz,ty,t),"ece":ece(tp,ty),"brier":float(((tp-nn.functional.one_hot(ty,6))**2).sum(1).mean()),"accepted_count":int(accept.sum()),"abstained_count":int((~accept).sum()),"coverage":float(accept.float().mean()),"accepted_accuracy":float((pred[accept]==ty[accept]).float().mean()) if accept.any() else None,"accepted_errors":int((pred[accept]!=ty[accept]).sum()),"false_confident_errors":int((pred[accept]!=ty[accept]).sum()),"sealed_test_access_count":1,"official_accuracy_claim":False,"scope":"PROVISIONAL_INTERNAL_ONLY"})
 mistakes=[{"image_id":tm[i]["image_id"],"actual":CLASSES[int(ty[i])],"predicted":CLASSES[int(pred[i])],"confidence":float(conf[i]),"accepted":bool(accept[i])}for i in range(len(ty))if pred[i]!=ty[i]];base["misclassifications"]=mistakes;save(DATA/"sealed_test_metrics.json",base)
 # Restricted runtime: safety partial and provisional evidence prohibit production/farmer use.
 if RUNTIME.exists():raise RuntimeError("RUNTIME_DESTINATION_ALREADY_EXISTS")
 RUNTIME.mkdir(parents=True);shutil.copy2(CAND/"best.pt",RUNTIME/"model.pt")
 for src,dst in [(DATA/"class_order.json","class_order.json"),(DATA/"calibration.json","calibration.json"),(DATA/"abstention_thresholds.json","abstention_thresholds.json"),(DATA/"dataset_hashes.json","dataset_hashes.json")]:shutil.copy2(src,RUNTIME/dst)
 runtime={"model_id":"crop_id_six_class_internal_v1","model_version":"1.0.0-internal","architecture":"mobilenet_v3_small","class_order":CLASSES,"preprocessing":{"resize":184,"center_crop":160,"mean":MEAN,"std":STD},"temperature":t,"confidence_threshold":ct,"margin_threshold":mt,"farmer_confirmation_required":True,"general_farmer_release":"BLOCKED","official_accuracy_claim":False,"acceptance":"PARTIAL_RESTRICTED_INTERNAL_ONLY","banana_data_quality":"LIMITED","licence_and_identity":"PROVISIONAL_INTERNAL_USE_ONLY"};save(RUNTIME/"runtime_config.json",runtime)
 hashes={p.name:sha(p)for p in RUNTIME.iterdir()if p.is_file()};save(RUNTIME/"SHA256SUMS.json",hashes);save(RUNTIME/"rollback.json",{"disable_runtime":True,"fallback":"RUNTIME_UNAVAILABLE","does_not_authorize_gemini":True})
 print("CALIBRATION_TEMPERATURE="+str(t));print("CONFIDENCE_THRESHOLD="+str(ct));print("MARGIN_THRESHOLD="+str(mt));print("SAFETY_STATUS="+safety_result["status"]);print("SEALED_MACRO_F1="+str(base["macro_f1"]));print("SEALED_BALANCED_ACCURACY="+str(base["balanced_accuracy"]));print("SEALED_TEST_ACCESS_COUNT=1");print("FINAL_MODEL_STATUS=PARTIAL_RESTRICTED_INTERNAL_ONLY")
if __name__=="__main__":main()
