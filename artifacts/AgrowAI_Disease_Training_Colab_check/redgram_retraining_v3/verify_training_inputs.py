from pathlib import Path
import argparse, json
from common import rows_for, validate_rows
def main():
 p=argparse.ArgumentParser(); p.add_argument("--package-root",default=str(Path(__file__).parent)); p.add_argument("--data-root"); p.add_argument("--verify-images",action="store_true"); a=p.parse_args()
 cfg,root,rows=rows_for(a.package_root); counts=validate_rows(cfg,root,rows,a.data_root,a.verify_images,False)
 print(json.dumps({"status":"PASS","split_counts":counts,"sealed_images_opened":False},indent=2))
if __name__=="__main__": main()
