import argparse,itertools,json
from pathlib import Path
import numpy as np
def main():
 p=argparse.ArgumentParser();p.add_argument("--logits",required=True);p.add_argument("--calibration",required=True);p.add_argument("--output",required=True);a=p.parse_args();d=np.load(a.logits);x=d["logits"];y=d["labels"].astype(int);t=json.loads(Path(a.calibration).read_text())["temperature"];z=x/t;z-=z.max(1,keepdims=True);p1=np.exp(z);p1/=p1.sum(1,keepdims=True);order=np.argsort(p1,axis=1);pred=order[:,-1];conf=p1[np.arange(len(y)),pred];margin=conf-p1[np.arange(len(y)),order[:,-2]]
 rows=[]
 for c,m in itertools.product([.5,.6,.7,.8,.9,.95],[0,.1,.2]):
  take=(conf>=c)&(margin>=m);rows.append({"confidence_threshold":c,"margin_threshold":m,"coverage":float(take.mean()),"accepted_accuracy":float((pred[take]==y[take]).mean()) if take.any() else None,"accepted_errors":int(((pred!=y)&take).sum()),"fit_split":"calibration"})
 per_class={}
 for k in sorted(set(y.tolist())):
  candidates=[]
  for c,m in itertools.product([.5,.6,.7,.8,.9,.95],[0,.1,.2]):
   take=(pred==k)&(conf>=c)&(margin>=m); candidates.append({"class_index":k,"confidence_threshold":c,"margin_threshold":m,"accepted_count":int(take.sum()),"accepted_accuracy":float((pred[take]==y[take]).mean()) if take.any() else None,"false_confident_errors":int(((pred!=y)&take).sum()),"fit_split":"calibration"})
  per_class[str(k)]=candidates
 out={"global_candidates":rows,"class_specific_candidates":per_class,"fallback":"ABSTAIN","provisional_test_used":False};Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=="__main__":main()
