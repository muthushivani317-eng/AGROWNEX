import argparse,json
from pathlib import Path
import numpy as np
def nll(logits,labels,t):
 z=logits/t;z=z-z.max(1,keepdims=True);return float(np.mean(-z[np.arange(len(labels)),labels]+np.log(np.exp(z).sum(1))))
def main():
 p=argparse.ArgumentParser();p.add_argument("--logits",required=True);p.add_argument("--output",required=True);a=p.parse_args();d=np.load(a.logits);x=d["logits"].astype(float);y=d["labels"].astype(int)
 if len(x)!=len(y) or x.ndim!=2:raise RuntimeError("INVALID_CALIBRATION_ARRAYS")
 grid=np.exp(np.linspace(np.log(.05),np.log(20),4000));vals=np.array([nll(x,y,t) for t in grid]);i=int(vals.argmin());before=nll(x,y,1.0);after=float(vals[i])
 if after>before+1e-10:raise RuntimeError("CALIBRATION_NLL_REGRESSION")
 out={"temperature":float(grid[i]),"nll_before":before,"nll_after":after,"nll_improved":after<=before+1e-10,"fit_split":"calibration"};Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=="__main__":main()
