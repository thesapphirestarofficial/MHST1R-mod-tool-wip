import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class FileOverride:
    game_path: str
    source: str


@dataclass
class Mod:
    id: str
    name: str
    version: str
    priority: int
    root: Path
    files: List[FileOverride]


def load_mods(mods_root: Path) -> List[Mod]:
    mods: List[Mod] = []
    if not mods_root.exists():
        return []

    for mod_dir in sorted([p for p in mods_root.iterdir() if p.is_dir()]):
        manifest = mod_dir / "mod.json"
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        files = [FileOverride(**f) for f in data.get("files", [])]
        mods.append(
            Mod(
                id=data["id"],
                name=data.get("name", data["id"]),
                version=data.get("version", "0.0.0"),
                priority=int(data.get("priority", 0)),
                root=mod_dir,
                files=files,
            )
        )

    mods.sort(key=lambda m: m.priority)
    return mods
