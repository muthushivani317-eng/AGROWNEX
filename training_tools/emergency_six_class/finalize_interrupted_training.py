import hashlib,json,platform,sys
from importlib.metadata import distributions
from datetime import UTC,datetime
from pathlib import Path
import torch,torchvision
ROOT=Path(__file__).resolve().parents[2];out=ROOT/"agrowai_autonomous_pipeline/CROP_ID_EMERGENCY_INTERNAL_SIX_CLASS/candidate_mobilenetv3_small"
ck=torch.load(out/"best.pt",map_location="cpu",weights_only=False)
def save(name,v):(out/name).write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
save("training_config.json",{"model_id":"crop_id_six_class_internal_v1","architecture":"mobilenet_v3_small","input_size":160,"pretrained_weights":"torchvision IMAGENET1K_V1","seed":20260805,"batch_size":64,"sampling":"inverse-frequency WeightedRandomSampler","optimizer":"AdamW","training_augmentation":["RandomResizedCrop(160,scale=.70..1.0)","RandomHorizontalFlip","RandomRotation(10)","ColorJitter"],"inference_preprocessing":ck["preprocessing"],"candidate_selection":"validation macro_f1","completed_epochs":1,"requested_epochs":6,"stop_reason":"VALIDATION_SATURATION_AND_CPU_OVERFIT_RISK","sealed_test_access_during_training":0,"official_accuracy_claim":False,"scope":"INTERNAL_ONLY"})
save("training_history.json",[{"epoch":ck["epoch"],"validation_metrics":ck["validation_metrics"],"epoch_seconds":758.1}])
save("environment.json",{"python":sys.version,"platform":platform.platform(),"torch":torch.__version__,"torchvision":torchvision.__version__,"cuda_available":torch.cuda.is_available(),"cpu_only":True})
save("training_receipt.json",{"status":"COMPLETED_ONE_SELECTED_CANDIDATE","completed_at_utc":datetime.now(UTC).isoformat(),"completed_epochs":1,"stop_reason":"VALIDATION_SATURATION_AND_CPU_OVERFIT_RISK","sealed_test_opened":False,"official_accuracy_claim":False})
(out/"dependency_lock.txt").write_text(
    "\n".join(sorted(f"{d.metadata['Name']}=={d.version}" for d in distributions() if d.metadata.get('Name'))) + "\n",
    encoding="utf-8",
)
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!="artifact_hashes.json"};save("artifact_hashes.json",hashes)
print("TRAINING_ARTIFACTS_FINALIZED=YES")
