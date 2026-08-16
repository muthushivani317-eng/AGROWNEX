from __future__ import annotations

import argparse, csv, hashlib, json, os, platform, random, sys, time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms

CLASSES = ["banana", "paddy", "cotton", "groundnut", "chilli", "redgram"]
C2I = {name: i for i, name in enumerate(CLASSES)}
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

class DS(Dataset):
    def __init__(self, manifest: Path, split: str, root: Path, training=False):
        self.rows = [r for r in json.loads(manifest.read_text(encoding="utf-8"))["rows"] if r["split"] == split]
        self.root = root
        self.tf = transforms.Compose([
            transforms.RandomResizedCrop(160, scale=(0.70, 1.0)), transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10), transforms.ColorJitter(.15, .15, .1, .04), transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]) if training else transforms.Compose([
            transforms.Resize(184), transforms.CenterCrop(160), transforms.ToTensor(), transforms.Normalize(MEAN, STD)
        ])
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        row = self.rows[i]
        with Image.open(self.root / row["path"]) as im: x = self.tf(im.convert("RGB"))
        return x, C2I[row["crop_class"]], row["image_id"]

def collate(batch):
    return torch.stack([x[0] for x in batch]), torch.tensor([x[1] for x in batch]), [x[2] for x in batch]

def metrics(labels, logits):
    pred = logits.argmax(1); top2 = logits.topk(2, 1).indices
    cm = torch.zeros(6, 6, dtype=torch.long)
    for y, p in zip(labels, pred, strict=True): cm[int(y), int(p)] += 1
    v = cm.float(); support=v.sum(1); predicted=v.sum(0); tp=v.diag()
    precision=tp/predicted.clamp_min(1); recall=tp/support.clamp_min(1); f1=2*precision*recall/(precision+recall).clamp_min(1e-12)
    return {"accuracy":float(tp.sum()/v.sum()), "balanced_accuracy":float(recall.mean()), "macro_precision":float(precision.mean()),
            "macro_recall":float(recall.mean()), "macro_f1":float(f1.mean()), "top2_accuracy":float((top2==labels[:,None]).any(1).float().mean()),
            "per_class":{c:{"precision":float(precision[i]),"recall":float(recall[i]),"f1":float(f1[i]),"support":int(support[i])} for i,c in enumerate(CLASSES)},
            "confusion_matrix":cm.tolist()}

def evaluate(model, loader):
    model.eval(); ys=[]; zs=[]; loss=0.; start=time.perf_counter()
    with torch.inference_mode():
        for x,y,_ in loader:
            z=model(x); loss += float(nn.functional.cross_entropy(z,y))*len(y); ys.append(y); zs.append(z)
    y,z=torch.cat(ys),torch.cat(zs); result=metrics(y,z); result["nll"]=loss/len(y); result["latency_ms_per_image"]=(time.perf_counter()-start)*1000/len(y)
    return result

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, value): path.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",type=Path,required=True); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--epochs",type=int,default=6); ap.add_argument("--batch",type=int,default=64); ap.add_argument("--workers",type=int,default=2); a=ap.parse_args()
    seed=20260805; random.seed(seed); torch.manual_seed(seed); torch.set_num_threads(max(1,min(8,os.cpu_count() or 1))); torch.use_deterministic_algorithms(True,warn_only=True)
    a.out.mkdir(parents=True,exist_ok=True); train=DS(a.manifest,"train",a.root,True); val=DS(a.manifest,"validation",a.root)
    counts=Counter(r["crop_class"] for r in train.rows); weights=[1/counts[r["crop_class"]] for r in train.rows]
    sampler=WeightedRandomSampler(weights,num_samples=len(train),replacement=True,generator=torch.Generator().manual_seed(seed))
    tl=DataLoader(train,batch_size=a.batch,sampler=sampler,num_workers=a.workers,collate_fn=collate,persistent_workers=a.workers>0)
    vl=DataLoader(val,batch_size=a.batch,shuffle=False,num_workers=a.workers,collate_fn=collate,persistent_workers=a.workers>0)
    model=models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1); model.classifier[3]=nn.Linear(model.classifier[3].in_features,6)
    for p in model.features.parameters(): p.requires_grad=False
    opt=AdamW(model.classifier.parameters(),lr=8e-4,weight_decay=1e-4); history=[]; best=-1.; stale=0
    for epoch in range(1,a.epochs+1):
        if epoch==3:
            for p in model.features[-3:].parameters(): p.requires_grad=True
            opt=AdamW((p for p in model.parameters() if p.requires_grad),lr=1.5e-4,weight_decay=1e-4)
        model.train(); total=seen=0; started=time.perf_counter()
        for x,y,_ in tl:
            opt.zero_grad(set_to_none=True); z=model(x); loss=nn.functional.cross_entropy(z,y,label_smoothing=.05); loss.backward(); opt.step(); total+=float(loss)*len(y); seen+=len(y)
        vm=evaluate(model,vl); row={"epoch":epoch,"train_loss":total/seen,"seconds":time.perf_counter()-started,**vm}; history.append(row)
        ck={"model_state_dict":model.state_dict(),"architecture":"mobilenet_v3_small","model_id":"crop_id_six_class_internal_v1","class_to_index":C2I,"epoch":epoch,"validation_metrics":vm,"preprocessing":{"resize":184,"center_crop":160,"mean":MEAN,"std":STD}}
        torch.save(ck,a.out/"last.pt")
        if vm["macro_f1"]>best+1e-5: best=vm["macro_f1"]; stale=0; torch.save(ck,a.out/"best.pt")
        else: stale+=1
        print(f"EPOCH={epoch} MACRO_F1={vm['macro_f1']:.6f} BALANCED={vm['balanced_accuracy']:.6f} SECONDS={row['seconds']:.1f}",flush=True)
        if stale>=2 and epoch>=4: break
    best_ck=torch.load(a.out/"best.pt",map_location="cpu",weights_only=False); model.load_state_dict(best_ck["model_state_dict"]); final=evaluate(model,vl)
    save(a.out/"training_history.json",history); save(a.out/"validation_metrics.json",final); save(a.out/"class_to_index.json",C2I)
    config={"model_id":"crop_id_six_class_internal_v1","architecture":"mobilenet_v3_small","input_size":160,"weights":"torchvision MobileNet_V3_Small_Weights.IMAGENET1K_V1","weights_licence":"BSD-3-Clause torchvision code; ImageNet pretrained weights use subject to upstream terms","seed":seed,"epochs_requested":a.epochs,"batch_size":a.batch,"sampling":"inverse-frequency WeightedRandomSampler","training_augmentation":["RandomResizedCrop(160,scale=.70..1.0)","RandomHorizontalFlip","RandomRotation(10)","ColorJitter"],"inference_preprocessing":best_ck["preprocessing"],"selection":"maximum validation macro_f1","sealed_test_access_count":0,"official_accuracy_claim":False,"scope":"INTERNAL_ONLY"}
    save(a.out/"training_config.json",config); save(a.out/"environment.json",{"python":sys.version,"platform":platform.platform(),"torch":torch.__version__,"torchvision":__import__('torchvision').__version__,"cuda":False,"cpu_threads":torch.get_num_threads()})
    save(a.out/"checkpoint_hashes.json",{"best.pt":sha(a.out/"best.pt"),"last.pt":sha(a.out/"last.pt")}); save(a.out/"training_receipt.json",{"completed_at_utc":datetime.now(UTC).isoformat(),"status":"PROVISIONAL_INTERNAL_USE_ONLY","sealed_test_opened":False})
    print("TRAINING_COMPLETE=YES"); print("BEST_SHA256="+sha(a.out/"best.pt")); print("VALIDATION_MACRO_F1="+str(final["macro_f1"]))

if __name__=="__main__": main()
