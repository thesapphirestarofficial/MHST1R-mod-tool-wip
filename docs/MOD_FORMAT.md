# MHST1 Mod Package Format

A mod is a folder under `mods/` containing `mod.json` plus optional payload folders.

```text
mods/
  my.mod.id/
    mod.json
    files/          # raw replacement/addition files
    tables/         # structured table patches
    scripts/        # optional future scripting hooks
```

## `mod.json`

```json
{
  "id": "author.mod_name",
  "name": "Readable Mod Name",
  "version": "1.0.0",
  "priority": 100,
  "description": "What this mod does",
  "requires": [],
  "conflicts": [],
  "files": [
    {
      "game_path": "native:/data/example/example.bin",
      "source": "files/example.bin"
    }
  ],
  "table_patches": [
    "tables/monsters.json",
    "tables/monsties.json",
    "tables/items.json"
  ]
}
```

## Load order
- Lower `priority` applies first.
- Higher `priority` wins conflicts.
- The planner reports duplicate writes so modders can resolve collisions.

## Game path conventions
- `native:/...` means a path inside extracted/staged game assets.
- `arc:/archive.arc::internal/path` is reserved for archive-entry injection once the ARC backend is finalized.

Examples:
```text
native:/romfs/native/data/foo.bin
arc:/native/archive.arc::data/monster/m001.bin
```
