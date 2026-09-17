import { en } from '../localization/locales/en.ts';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

function flatten(obj, prefix = '', out = {}) {
  for (const k of Object.keys(obj)) {
    const v = obj[k];
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out);
    else out[key] = true;
  }
  return out;
}
const keys = flatten(en);

function walk(dir, files = []) {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name === '__tests__') continue;
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, files);
    else if (/\.(tsx|ts)$/.test(name)) files.push(p);
  }
  return files;
}

const featureDirs = process.argv.slice(2);
const missing = new Set();
const used = new Set();
const re = /\bt\(\s*["'`]([a-zA-Z0-9_.]+)["'`]/g;
for (const dir of featureDirs) {
  let files;
  try { files = walk(dir); } catch { continue; }
  for (const f of files) {
    const content = readFileSync(f, 'utf8');
    let m;
    while ((m = re.exec(content))) {
      const key = m[1];
      used.add(key);
      if (!keys[key]) missing.add(`${key}  (${f})`);
    }
  }
}
console.log('TOTAL USED:', used.size);
console.log('MISSING KEYS:');
for (const m of [...missing].sort()) console.log(' -', m);
