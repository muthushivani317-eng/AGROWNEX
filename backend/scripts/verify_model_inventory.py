"""Exit non-zero unless the complete controlled-pilot model inventory is ready."""
from __future__ import annotations

import json

from app.crop_runtime.inventory import (
    get_model_inventory,
    inventory_ready,
    refresh_model_inventory,
)
from app.crop_runtime.readiness_cache import refresh_technical_readiness


def main() -> int:
    refresh_technical_readiness()
    refresh_model_inventory()
    inventory = get_model_inventory()
    print(json.dumps(inventory.public_dict(), sort_keys=True))
    return 0 if inventory_ready(inventory) else 1


if __name__ == "__main__":
    raise SystemExit(main())
