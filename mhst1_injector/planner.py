from dataclasses import dataclass
from pathlib import Path
from typing import List

from .mods import Mod


@dataclass
class Action:
    kind: str  # e.g. override_file
    game_path: str
    source_path: Path
    mod_id: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.game_path} <- {self.source_path} ({self.mod_id})"


def plan_actions(mods: List[Mod], backend) -> List[Action]:
    plan: List[Action] = []
    for mod in mods:
        for f in mod.files:
            src = mod.root / f.source
            plan.append(Action(kind="override_file", game_path=f.game_path, source_path=src, mod_id=mod.id))
    # backend can reorder/normalize if it wants
    return backend.normalize_plan(plan)
