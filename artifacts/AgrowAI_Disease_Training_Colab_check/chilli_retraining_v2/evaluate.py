from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import numpy as np
from common import rows_for,validate_rows,sha256
def main():
 p=argparse.ArgumentParser();p.add_argument("--package-root",default=str(Path(__file__).parent));p.add_argument("--data-root",required=True);p.add_argument("--checkpoint",required=True);p.add_argument("--split",choices=["development_validation","calibration","provisional_test"],default="development_validation");p.add_argument("--output-dir",required=True);p.add_argument("--allow-one-time-provisional-test",action="store_true");a=p.parse_args()
 cfg,root,rows=rows_for(a.package_root);validate_rows(cfg,root,rows,a.data_root,True,a.split=="provisional_test" and a.allow_one_time_provisional_test)
 out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True);receipt=out/"one_time_provisional_test_receipt.json"
 if a.split=="provisional_test" and (not a.allow_one_time_provisional_test or receipt.exists()):raise RuntimeError("SEALED_PROVISIONAL_TEST_ACCESS_REFUSED")
 import torch
 from PIL import Image
 from torch.utils.data import Dataset,DataLoader
 from torchvision import models,transforms
 from sklearn.metrics import accuracy_score,f1_score,precision_recall_fscore_support,confusion_matrix
 classes=cfg["classes"];c2i={c:i for i,c in enumerate(classes)};part=[r for r in rows if r["split_name"]==a.split]
 tf=transforms.Compose([transforms.Resize((256,256)),transforms.CenterCrop(cfg["image_size"]),transforms.ToTensor(),transforms.Normalize(cfg["normalization_mean"],cfg["normalization_std"])])
 class DS(Dataset):
  def __len__(self):return len(part)
  def __getitem__(self,i):r=part[i];return tf(Image.open(Path(a.data_root)/r["source_path"]).convert("RGB")),c2i[r["canonical_class"]],r["image_id"]
 dl=DataLoader(DS(),batch_size=cfg["batch_size"],shuffle=False,num_workers=cfg["num_workers"]);ck=torch.load(a.checkpoint,map_location="cpu",weights_only=False)
 if ck.get("model_name")!=cfg["model_name"] or ck.get("classes")!=classes:raise RuntimeError("CHECKPOINT_IDENTITY_MISMATCH")
 model=models.mobilenet_v3_small(weights=None);model.classifier[-1]=torch.nn.Linear(model.classifier[-1].in_features,len(classes));model.load_state_dict(ck["model_state_dict"]);model.eval()
 logits=[];labels=[];ids=[]
 with torch.inference_mode():
  for x,y,i in dl:logits.append(model(x).numpy());labels.extend(y.numpy());ids.extend(i)
 logits=np.concatenate(logits);labels=np.asarray(labels);pred=logits.argmax(1);top3=np.argsort(logits,axis=1)[:,-min(3,len(classes)):]
 pr,rc,f1,sup=precision_recall_fscore_support(labels,pred,labels=range(len(classes)),zero_division=0)
 metrics={"split":a.split,"sample_count":len(labels),"top1":accuracy_score(labels,pred),"top3":float(np.mean([y in t for y,t in zip(labels,top3)])),"macro_f1":f1_score(labels,pred,average="macro"),"per_class":{classes[i]:{"precision":pr[i],"recall":rc[i],"f1":f1[i],"support":int(sup[i])} for i in range(len(classes))},"confusion_matrix":confusion_matrix(labels,pred,labels=range(len(classes))).tolist(),"official_accuracy_claim":False}
 np.savez_compressed(out/f"{a.split}_logits.npz",logits=logits,labels=labels,sample_ids=np.asarray(ids))
 (out/f"{a.split}_metrics.json").write_text(json.dumps(metrics,indent=2))
 if a.split=="provisional_test":receipt.write_text(json.dumps({"evaluation_completed":True,"checkpoint_sha256":sha256(Path(a.checkpoint)),"manifest_sha256":cfg["split_manifest_sha256"],"tuning_after_test_forbidden":True,"official_accuracy_claim":False},indent=2))
 print(json.dumps(metrics,indent=2))
if __name__=="__main__":main()
