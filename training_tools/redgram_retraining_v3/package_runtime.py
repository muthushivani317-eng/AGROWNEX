import argparse,hashlib,json,shutil
from pathlib import Path
from common import sha256
def main():
 p=argparse.ArgumentParser();p.add_argument("--package-root",default=str(Path(__file__).parent));p.add_argument("--checkpoint",required=True);p.add_argument("--calibration",required=True);p.add_argument("--thresholds",required=True);p.add_argument("--evaluation",required=True);p.add_argument("--output-dir",required=True);a=p.parse_args();root=Path(a.package_root);cfg=json.loads((root/"training_config.json").read_text());out=Path(a.output_dir)
 if out.exists() and any(out.iterdir()):raise RuntimeError("RUNTIME_DESTINATION_NOT_EMPTY")
 out.mkdir(parents=True,exist_ok=True)
 for src,name in [(Path(a.checkpoint),"best.pt"),(root/"class_mapping.json","class_mapping.json"),(root/"preprocessing.json","preprocessing.json"),(Path(a.calibration),"calibration.json"),(Path(a.thresholds),"thresholds.json"),(Path(a.evaluation),"provisional_evaluation.json")]:shutil.copy2(src,out/name)
 meta={"model_name":cfg["model_name"],"official_accuracy_claim":False,"farmer_inference_enabled":False};(out/"model_metadata.json").write_text(json.dumps(meta,indent=2))
 files={p.name:sha256(p) for p in out.iterdir() if p.is_file()};(out/"integrity_manifest.json").write_text(json.dumps(files,indent=2));print(json.dumps(files,indent=2))
if __name__=="__main__":main()
