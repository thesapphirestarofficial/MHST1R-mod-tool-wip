from __future__ import annotations

import json
from pathlib import Path
from .mods import load_mods


def validate_mods(mods_root: Path) -> list[str]:
    errors: list[str] = []
    mods = load_mods(mods_root)
    seen_ids = set()
    writes = {}

    for mod in mods:
        if mod.id in seen_ids:
            errors.append(f"duplicate mod id: {mod.id}")
        seen_ids.add(mod.id)

        for f in mod.files:
            src = mod.root / f.source
            if not src.exists():
                errors.append(f"{mod.id}: missing file source {f.source}")
            writes.setdefault(f.game_path, []).append(mod.id)

        manifest = json.loads((mod.root / "mod.json").read_text(encoding="utf-8"))
        for patch in manifest.get("table_patches", []):
            p = mod.root / patch
            if not p.exists():
                errors.append(f"{mod.id}: missing table patch {patch}")
                continue
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                errors.append(f"{mod.id}: invalid JSON in {patch}: {e}")
                continue
            if "schema" not in obj:
                errors.append(f"{mod.id}: table patch {patch} missing schema")
            if not any(k in obj for k in ("add", "replace", "patch")):
                errors.append(f"{mod.id}: table patch {patch} has no add/replace/patch operation")

    for game_path, mod_ids in writes.items():
        if len(mod_ids) > 1:
            errors.append(f"conflicting file override for {game_path}: {', '.join(mod_ids)}")

    return errors
