# MHST1 Remaster Mod Loader / Injector

Target: **Monster Hunter Stories 1 Remaster on Steam / PC, game version 1.1.0**  
Engine family: **Capcom MT Framework Mobile variant**

This package contains a Windows-friendly mod loader/injector plus research and authoring docs for adding/overriding MHST1 data.

## Fast start for players

1. Copy this whole folder into your game folder, next to the game executable or next to the folders that contain `table.arc`, `message_R`, `battleparm`, etc.
2. Put mods into the `mods/` folder.
3. Double-click **`MHST1ModLoader.exe`**.
4. Choose **Install mods**.
5. To undo installed mods, run the loader again and choose **Restore backups / uninstall mods**.

If Windows blocks the tiny launcher exe, run **`MHST1ModLoader.bat`** instead. The loader itself is the included PowerShell script, so users do **not** need Python or Java.

## What the loader can do now

- Install loose-file/native overrides.
- Replace entries inside MHST1 plain `ARC\0` v7 archives.
- Rebuild ARC files while preserving entry order, names, hashes, compression mode, and backups.
- Apply clone-row table patches to:
  - loose fixed-row binary tables like `battleparm/MonsterData.bin`, `OtomonData.bin`, etc.
  - decompressed XFS tables inside ARC entries such as `table.arc::table\item_data` or `table.arc::table\battle_table_em001`.
- Restore original files from `_mhst1_backup`.

## What was confirmed from the supplied files

- PC Remaster 1.1.0 uses plain `ARC\0` archives, version `7`.
- ARC header:
  - magic: `ARC\0`
  - version: `u16` at `0x04`
  - file count: `u16` at `0x06`
  - entries start at `0x08`
  - each entry is `0x90` bytes
  - entry name is `0x80` bytes UTF-8/null-padded
  - entry metadata is hash, compressed size, uncompressed-size-plus-flags, data offset
- Most ARC payloads are zlib-compressed and flagged with `0x40000000`.
- `table.arc` contains many important XFS tables, including `item_data`, `skill_table`, `armor_data`, `armor_param`, `questList`, `mainQuest`, `battle_enemy_file`, `battle_enemy_set`, `battle_table_em###`, `battle_atk_em###`, and `battle_atk_eff_em###`.
- `battleparm` loose `.bin` files are fixed-row tables:
  - `MonsterData.bin`: 555 rows, 134 bytes/row
  - `OtomonData.bin`: 256 rows, 146 bytes/row
  - `MonsterBaseData.bin`: 100 rows, 60 bytes/row
  - `PlayerData.bin`: 101 rows, 22 bytes/row
  - `addParam.bin`: 256 rows, 4 bytes/row
  - `adjustData.bin`: 256 rows, 4 bytes/row

## Mod folder format

```text
mods/
  my.mod.id/
    mod.json
    files/
    tables/
```

Example:

```json
{
  "id": "author.example",
  "name": "Example Mod",
  "version": "1.0.0",
  "priority": 100,
  "files": [
    {
      "arc": "table.arc",
      "entry": "table/item_data",
      "source": "files/table/item_data"
    },
    {
      "game_path": "native:/battleparm/MonsterData.bin",
      "source": "files/battleparm/MonsterData.bin"
    }
  ],
  "table_patches": [
    "tables/clone_monsterdata.json"
  ]
}
```

### File override targets

Use `game_path` for loose files:

```json
{ "game_path": "native:/battleparm/MonsterData.bin", "source": "files/MonsterData.bin" }
```

Use `arc` + `entry` for archive entries:

```json
{ "arc": "table.arc", "entry": "table/item_data", "source": "files/table/item_data" }
```

The loader normalizes `/` to `\` for ARC internal paths.

## Clone-row table patch format

Clone-row patches are the safest first format for adding data because they copy a known-good existing row, then edit only the fields you specify.

For loose `battleparm` files:

```json
{
  "target_file": "battleparm/MonsterData.bin",
  "row_count_offset": 0,
  "count_type": "u16",
  "row_base": 2,
  "row_size": 134,
  "clone_rows": [
    {
      "base_index": 0,
      "set": [
        { "offset": 0, "type": "u16", "value": 9001 }
      ]
    }
  ]
}
```

For XFS tables inside `table.arc`:

```json
{
  "target_arc": "table.arc",
  "target_entry": "table/item_data",
  "row_count_offset": 8,
  "count_type": "u32",
  "row_base": 2240,
  "row_size": 172,
  "clone_rows": [
    {
      "base_index": 100,
      "set": [
        { "offset": 0, "type": "u32", "value": 90001 }
      ]
    }
  ]
}
```

`row_base` and `row_size` must be discovered per table. The included optional Python tools can inspect XFS files and ARC contents.

## Optional developer tools

The Windows loader is self-contained, but the source also includes Python tools for modders/researchers:

```bash
python -m mhst1_injector.arc list table.arc
python -m mhst1_injector.arc extract table.arc out_table
python -m mhst1_injector.arc pack out_table table_rebuilt.arc
python -m mhst1_injector.xfs info out_table/table/item_data
python -m mhst1_injector.battleparm info battleparm/*.bin
```

## Key docs

- `docs/TECHNICAL_FORMATS.md` — file formats discovered from the supplied data.

- `docs/MESH_TEXTURE_PIPELINE.md` — custom `.mod`/`.tex` mesh and texture pipeline, public tool survey, current reverse-engineering status, and same-layout writer usage.
- `docs/ADDING_CONTENT_GUIDE.md` — full monster/monstie/material/equipment/quest authoring plan.
- `docs/MOD_FORMAT.md` — manifest and patch schema.
- `examples/` — starter templates.

## Important modding note

Adding brand-new monsters/monsties is a graph problem. A complete monster requires species/book rows, battle rows, movesets, enemy AI, ally/monstie data, egg data, drops, item/material text, equipment recipes, quest unlocks, and resources. The loader supports the patching mechanics; mod authors still need to map exact per-field offsets for each target table. The docs explain how to do that by cloning existing rows first.


---

## New monster toolkit additions

See `README_NEW_MONSTER_TOOLKIT.md` for the added monster/model/resource workflow, helper scripts, and modder checklist.
