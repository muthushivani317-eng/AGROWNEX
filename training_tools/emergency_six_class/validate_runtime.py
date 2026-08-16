import hashlib,json,shutil,tempfile
from pathlib import Path
import torch
from training_tools.emergency_six_class.freeze_and_evaluate import CAND,RUNTIME,CLASSES,model

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[p for p in RUNTIME.iterdir() if p.is_file() and p.name!="SHA256SUMS.json"]
(RUNTIME/"SHA256SUMS.json").write_text(json.dumps({p.name:sha(p) for p in files},indent=2)+"\n",encoding="utf-8")
from backend.app.crop_identity_six_class_internal.runtime import Runtime,verify,IntegrityError
verify(RUNTIME)
source=model();installed=Runtime(RUNTIME);installed.load()
torch.manual_seed(20260805);x=torch.randn(3,3,160,160)
with torch.inference_mode():a=source(x);b=installed._model(x)
max_diff=float((a-b).abs().max());equivalent=max_diff<=1e-7
tamper={}
for name in ["model.pt","runtime_config.json","class_order.json","calibration.json","abstention_thresholds.json","dataset_hashes.json","rollback.json"]:
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/"bundle";shutil.copytree(RUNTIME,root)
  with (root/name).open("ab") as h:h.write(b"tamper")
  try:verify(root);tamper[name]=False
  except IntegrityError:tamper[name]=True
result={"source_runtime_equivalence":"PASS" if equivalent else "FAIL","max_absolute_logit_difference":max_diff,"source_checkpoint_sha256":sha(CAND/"best.pt"),"runtime_model_sha256":sha(RUNTIME/"model.pt"),"tamper_detection":tamper,"tamper_detection_status":"PASS" if all(tamper.values()) else "FAIL"}
(RUNTIME/"verification_receipt.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2))
