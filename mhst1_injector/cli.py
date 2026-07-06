import argparse
import json
import os
from pathlib import Path

from .logging_utils import get_logger
from .mods import load_mods
from .planner import plan_actions
from .backends.registry import get_backend

log = get_logger(__name__)


def main(argv=None):
    p = argparse.ArgumentParser(prog="mhst1_injector", description="MHST1 mod injector (starter kit)")
    p.add_argument("--game-root", required=True, help="Path to extracted game assets/app data")
    p.add_argument("--mods", default="mods", help="Mods folder")
    p.add_argument("--backend", default="auto", help="Container backend to use (auto|arc|...)")
    p.add_argument("--dry-run", action="store_true", help="Plan only; make no changes")
    p.add_argument("--out", default=None, help="Optional output folder for rebuilt containers")
    p.add_argument("--validate-only", action="store_true", help="Validate mods and table patches, then exit")

    args = p.parse_args(argv)

    game_root = Path(args.game_root)
    mods_root = Path(args.mods)

    if not game_root.exists():
        raise SystemExit(f"game-root not found: {game_root}")

    mods = load_mods(mods_root)

    if args.validate_only:
        from .validate import validate_mods
        errors = validate_mods(mods_root)
        if errors:
            for e in errors:
                log.error(e)
            return 2
        log.info("Validation passed for %d mod(s)", len(mods))
        return 0

    backend = get_backend(args.backend, game_root)

    plan = plan_actions(mods, backend)

    log.info("Planned %d actions", len(plan))
    for a in plan:
        log.info("%s", a)

    if args.dry_run:
        return 0

    out_dir = Path(args.out) if args.out else None
    backend.apply(plan, dry_run=False, out_dir=out_dir)

    log.info("Done")
    return 0
