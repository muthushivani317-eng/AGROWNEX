import argparse,json
from pathlib import Path
from common import sha256
def main():
 p=argparse.ArgumentParser();p.add_argument("runtime");a=p.parse_args();root=Path(a.runtime);m=json.loads((root/"integrity_manifest.json").read_text())
 for name,digest in m.items():
  if sha256(root/name)!=digest:raise RuntimeError(f"RUNTIME_HASH_MISMATCH:{name}")
 meta=json.loads((root/"model_metadata.json").read_text())
 if meta.get("farmer_inference_enabled") or meta.get("official_accuracy_claim"):raise RuntimeError("UNSAFE_RUNTIME_METADATA")
 print("RUNTIME_VERIFICATION_PASS")
if __name__=="__main__":main()
