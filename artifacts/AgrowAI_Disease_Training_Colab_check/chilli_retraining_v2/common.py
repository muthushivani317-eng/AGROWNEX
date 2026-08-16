from __future__ import annotations
import csv, hashlib, json, os, random
from collections import defaultdict
from pathlib import Path

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def load_config(root):
    root=Path(root)
    return json.loads((root/"training_config.json").read_text()), root

def rows_for(root):
    cfg, root=load_config(root)
    manifest=root/cfg["split_manifest"]
    if sha256(manifest)!=cfg["split_manifest_sha256"]: raise RuntimeError("MANIFEST_HASH_MISMATCH")
    with manifest.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    return cfg,root,rows

def validate_rows(cfg,root,rows,data_root=None,verify_images=False,allow_sealed=False):
    if len(rows)!=cfg["expected_total"]: raise RuntimeError("ROW_COUNT_MISMATCH")
    counts={s:sum(r["split_name"]==s for r in rows) for s in cfg["expected_splits"]}
    if counts!=cfg["expected_splits"]: raise RuntimeError("SPLIT_COUNT_MISMATCH")
    if sorted({r["canonical_class"] for r in rows})!=sorted(cfg["classes"]): raise RuntimeError("CLASS_MAPPING_MISMATCH")
    for key in ("sha256","duplicate_family_id"):
        seen=defaultdict(set)
        for r in rows: seen[r[key]].add(r["split_name"])
        if any(len(v)>1 for v in seen.values()): raise RuntimeError(f"{key.upper()}_LEAKAGE")
    if verify_images:
        if not data_root: raise RuntimeError("DATA_ROOT_REQUIRED")
        base=Path(data_root).resolve()
        for r in rows:
            if r["split_name"]=="provisional_test" and not allow_sealed: continue
            p=(base/r["source_path"]).resolve()
            if base not in p.parents: raise RuntimeError("PATH_TRAVERSAL")
            if not p.is_file(): raise RuntimeError(f"IMAGE_MISSING:{r['image_id']}")
            if sha256(p)!=r["sha256"]: raise RuntimeError(f"IMAGE_HASH_MISMATCH:{r['image_id']}")
    return counts
