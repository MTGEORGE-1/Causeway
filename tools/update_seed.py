#!/usr/bin/env python3
"""Copy the accumulated profile cache into the committed seed.

Company profiles come from an endpoint that rate-limits by IP, so no single
machine can collect all 2,782 in one go — coverage builds up over many runs.
The working cache lives under `data/`, which is gitignored, so that hard-won
coverage never reaches CI: the runner starts empty, gets cut off after a couple
of hundred, and the deployed site ends up with a fraction of what this machine
has.

Committing the cache as a seed fixes that. Run this whenever local coverage has
grown meaningfully, then commit `seed/profiles.json`.

    python tools/update_seed.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "hkcache" / "profiles.json"
SEED = ROOT / "seed" / "profiles.json"


def main() -> None:
    if not CACHE.exists():
        raise SystemExit("No local cache yet — run `python run.py` first.")

    cache = json.loads(CACHE.read_text())
    seed = {}
    if SEED.exists():
        seed = json.loads(SEED.read_text())

    merged = {**seed, **cache}
    SEED.parent.mkdir(parents=True, exist_ok=True)
    SEED.write_text(json.dumps(merged, ensure_ascii=False, separators=(",", ":")))

    size = SEED.stat().st_size / 1024 / 1024
    print(f"seed/profiles.json: {len(seed)} -> {len(merged)} profiles ({size:.1f} MB)")
    if len(merged) > len(seed):
        print(f"  +{len(merged) - len(seed)} new. Commit it so CI starts from here.")


if __name__ == "__main__":
    main()
