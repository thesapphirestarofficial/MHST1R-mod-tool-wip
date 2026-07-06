import shutil
from pathlib import Path
from typing import List, Optional

from ..planner import Action
from ..logging_utils import get_logger

log = get_logger(__name__)


class SimpleFSBackend:
    """Backend that applies overrides by copying files into a mirror folder.

    This is useful for:
    - emulators
    - frameworks that support loose-file overrides
    - staging outputs before repacking archives

    It does NOT modify proprietary containers yet.
    """

    def __init__(self, game_root: Path):
        self.game_root = game_root

    def normalize_plan(self, plan: List[Action]) -> List[Action]:
        return plan

    def apply(self, plan: List[Action], dry_run: bool, out_dir: Optional[Path] = None):
        out = out_dir or self.game_root

        for a in plan:
            if a.kind != "override_file":
                continue
            if not a.source_path.exists():
                raise SystemExit(f"Missing mod file: {a.source_path}")

            # game_path syntax: "native:/path/inside/game" or plain relative.
            rel = a.game_path
            if rel.startswith("native:"):
                rel = rel.split(":", 1)[1].lstrip("/")
            rel = rel.lstrip("/")

            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            log.info("Copy %s -> %s", a.source_path, dest)
            if not dry_run:
                shutil.copy2(a.source_path, dest)
