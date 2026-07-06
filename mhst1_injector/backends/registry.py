from pathlib import Path
from .simple_fs import SimpleFSBackend


def get_backend(name: str, game_root: Path):
    # For now we default to a filesystem overlay backend.
    # Once we identify the container formats, we will add e.g. ArcBackend.
    if name in ("auto", "fs", "simple_fs"):
        return SimpleFSBackend(game_root)

    raise SystemExit(
        f"Unknown backend: {name}. Implement it under mhst1_injector/backends and register it here."
    )
