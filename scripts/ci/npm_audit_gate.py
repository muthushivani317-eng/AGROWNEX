"""Fail CI on any high/critical npm advisory in shipped dependencies, except
advisories reviewed and accepted below (with a reason and a re-check date).

Usage: npm audit --omit=dev --json | python scripts/ci/npm_audit_gate.py
"""
from __future__ import annotations

import json
import sys

# advisory URL -> why it is accepted. Re-review monthly; remove when fixed upstream.
ACCEPTED = {
    # image-size is used only by the Metro bundler at build time (not shipped in
    # the APK); the fix needs a Metro major upgrade. Review: 2026-11.
    "https://github.com/advisories/GHSA-5p2g-fcmc-qvqq": "build-time only (metro)",
    "https://github.com/advisories/GHSA-w3rx-r6r6-pgpr": "build-time only (metro)",
    # node-forge <=1.4.0 (no fixed release yet) is pulled only by @expo/cli for
    # EAS update code signing, which this app does not enable; never bundled
    # into the APK. Re-check when node-forge ships a fix. Review: 2026-11.
    "https://github.com/advisories/GHSA-86w9-cpqp-85rv": "build-time only (expo cli)",
}
BLOCKING = {"high", "critical"}


def main() -> int:
    report = json.load(sys.stdin)
    problems = []
    for name, vuln in report.get("vulnerabilities", {}).items():
        for via in vuln.get("via", []):
            if not isinstance(via, dict):
                continue  # transitive pointer; the root advisory is listed itself
            if via.get("severity") in BLOCKING and via.get("url") not in ACCEPTED:
                problems.append(f"{via['severity']:8} {name}: {via.get('title')} {via.get('url')}")
    if problems:
        print("Blocking npm advisories:\n" + "\n".join(sorted(set(problems))))
        return 1
    print("npm audit gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
