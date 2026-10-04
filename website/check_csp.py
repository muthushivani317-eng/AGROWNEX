"""CI check: every inline script / on* handler in the site is allowed by the nginx CSP.

Run: python website/check_csp.py   (exit 1 lists any hash missing from default.conf.template)
"""
from __future__ import annotations

import base64
import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _hash(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def main() -> int:
    conf = (HERE / "default.conf.template").read_text(encoding="utf-8")
    csp = re.search(r'Content-Security-Policy "([^"]+)"', conf)
    if not csp:
        print("CSP header missing from default.conf.template")
        return 1
    missing = []
    for page in sorted(HERE.glob("*.html")):
        html = page.read_text(encoding="utf-8")
        # JSON-LD data blocks are never executed, so CSP does not apply to them.
        inline = re.findall(r'<script(?![^>]*\b(?:src=|type="application/ld\+json"))[^>]*>(.*?)</script>', html, re.S)
        handlers = re.findall(r'\son[a-z]+="([^"]*)"', html)
        for snippet in inline + handlers:
            if _hash(snippet) not in csp.group(1):
                missing.append(f"{page.name}: {_hash(snippet)}  {snippet[:60]!r}")
    if missing:
        print("Inline code not allowed by CSP (update the hashes in default.conf.template):")
        print("\n".join(missing))
        return 1
    print("CSP covers all inline code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
