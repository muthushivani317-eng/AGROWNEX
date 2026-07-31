from pathlib import Path
import hashlib
import json
import sys


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


package_root = Path(
    sys.argv[1] if len(sys.argv) > 1 else "."
).resolve()

checksums_path = (
    package_root / "integrity" / "SHA256SUMS.json"
)

if not checksums_path.is_file():
    raise SystemExit("SHA256SUMS_MISSING")

checksums = json.loads(
    checksums_path.read_text(encoding="utf-8")
)

errors = []

for relative_path, expected_hash in checksums.items():
    path = package_root / relative_path

    if not path.is_file():
        errors.append(
            f"MISSING: {relative_path}"
        )
        continue

    actual_hash = sha256_file(path)

    if actual_hash != expected_hash:
        errors.append(
            f"HASH_MISMATCH: {relative_path}"
        )

if errors:
    print("PACKAGE_VERIFICATION=FAIL")

    for error in errors:
        print(error)

    raise SystemExit(1)

print("PACKAGE_VERIFICATION=PASS")
print("VERIFIED_FILE_COUNT=", len(checksums))
