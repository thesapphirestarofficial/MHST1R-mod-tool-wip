# MHST1 Remaster New Monster Toolkit

This is a practical toolkit for **Monster Hunter Stories 1 Remaster PC** modders who want to add/clone monsters, models, materials, textures, eggs, drops, equipment, and quests.

## What I confirmed from the supplied files

The supplied `mod` folders contain loose MT Framework resources:

- `sd` / `sd_low`: small/SD model sets, each usually `.mod + .mrl + .tex`.
- `om`: object/model folders, each usually `.mod + .mrl + .tex`; some include `.ctc`/`.cli`.
- `mo`: monster animation/camera folders. These are mostly `.lmt` animation and `.lcm` camera files under `mo###/em###` and `mo###/sy###`.
- `scale`: body scale animation data under `scale/mo/mo###/mo###_body.lmt`.

Common file signatures found:

| Ext | Magic | Role |
|---|---|---|
| `.mod` | `MOD\0` | MT Framework model/mesh resource |
| `.mrl` | `MRL\0` | Material library; contains texture paths like `mod\sd\sd001\sd001_BM` |
| `.tex` | `TEX\0` | MT Framework texture |
| `.lmt` | `LMT\0` | Animation/motion data |
| `.lcm` | `LCM\0` | Camera/cut-in motion data |
| `.omi` | `OMI\0` | Object-map/index style data |

## Important reality check

Adding a monster is not only dropping in a model. A working monster/monstie needs a **data graph**:

1. Loose resources: model/material/textures/animations/camera/scale.
2. Battle params: `battleparm/MonsterData.bin`, `OtomonData.bin`, etc.
3. Table links in `table.arc`: monster enum conversion, battle tables, attack tables, egg data, item data, monster book data, quest/drop data.
4. Text/message entries for names/descriptions.

The included loader can install loose files, replace ARC entries, and clone fixed-row/XFS table rows once the exact row offsets are mapped for your target table.

## Safest workflow: clone first, then customize

1. Pick a base monster with a similar skeleton/body type.
2. Clone its resource folder(s) and keep naming length stable where possible (`mo048` → `mo901` is equal length; good).
3. Use its existing `.lmt` animations and `.lcm` camera data first.
4. Only change textures/material references after the cloned monster appears in-game.
5. Clone table rows for IDs and references. Do not hand-build rows from zero.
6. Add one subsystem at a time: resource clone → battle enemy → monstie data → egg → drops → quest.


## Custom mesh/texture pipeline

This package now includes experimental `.mod` and `.tex` research tools:

```bat
python -m mhst1_injector.mtf_mod info path\to\model.mod
python -m mhst1_injector.mtf_mod split path\to\model.mod split_model
python -m mhst1_injector.mtf_mod rebuild split_model rebuilt.mod
python -m mhst1_injector.mtf_mod splice-same-layout base.mod donor.mod out.mod

python -m mhst1_injector.mtf_tex info path\to\texture.tex
python -m mhst1_injector.mtf_tex replace-same-layout base.tex donor.tex out.tex
```

Read `docs/MESH_TEXTURE_PIPELINE.md` before attempting a custom model. The supported first target is **a custom mesh rigged to an existing MHST1 skeleton** with unchanged material/LOD/section layout. Full arbitrary topology and custom-skeleton writing still require deeper `.mod` writer work.

## Player install instructions

1. Put this toolkit folder next to the game executable or next to `table.arc`, `battleparm`, and `mod`.
2. Put mod folders under `mods/`.
3. Run `MHST1ModLoader.bat` or `MHST1ModLoader.exe`.
4. Choose **Install mods**.
5. To uninstall, run again and choose **Restore backups / uninstall mods**.

Backups are stored under `_mhst1_backup`.

## Modder quick start

### 1) Scan your resources

```bat
python tools\resource_scan.py "C:\path\to\Monster Hunter Stories\mod" --out-json RESOURCE_MAP.json --out-md RESOURCE_MAP.md
```

### 2) Generate a starter mod folder

Example: clone `mo048` resources into a new `mo901` resource namespace:

```bat
python tools\make_new_monster_mod.py ^
  --out mods\sapphin.test_monster ^
  --id sapphin.test_monster ^
  --name "Test Monster" ^
  --base-mo mo048 ^
  --new-mo mo901 ^
  --base-resource-folder "C:\path\to\Monster Hunter Stories\mod\mo\mo048" ^
  --species-id 9001
```

### 3) Patch material paths if needed

If an `.mrl` still points at old texture paths:

```bat
python tools\patch_mrl_paths.py mods\sapphin.test_monster\files\mod\sd\sd901\sd901.mrl ^
  --backup ^
  --replace "mod\sd\sd048\sd048_BM" "mod\sd\sd901\sd901_BM"
```

New strings must be the same length or shorter than old strings.

### 4) Finish table patches

The generated `tables/TODO_*.json` files are templates. They intentionally contain TODOs because offsets must be verified from your actual `table.arc`/`battleparm` files.

Use the included research helpers:

```bat
python -m mhst1_injector.arc list table.arc
python -m mhst1_injector.arc extract table.arc extracted_table
python -m mhst1_injector.xfs info extracted_table\table\monster_enum_conversion_table_data
python -m mhst1_injector.battleparm info battleparm\MonsterData.bin battleparm\OtomonData.bin
```

Then set:

- `row_base`
- `row_size`
- field offsets (`mID`, `mBattleEmNo`, `mBuddyId`, etc.)
- base row index to clone

Finally add the finished patch paths to `mod.json` under `table_patches`.

## Recommended ID range

Use high IDs to reduce conflicts:

```json
{
  "monster_species": 9001,
  "battle_enemy": 9001,
  "buddy_id": 9001,
  "item_start": 90001,
  "equipment_start": 91001,
  "quest_start": 92001,
  "skill_start": 93001
}
```

## Public tooling/resources worth using

- **ARCtool by FluffyQuack**: useful reference for MT Framework ARC/TEX/XFS workflows.
- **Noesis**: useful for viewing/exporting many game model/texture formats when a matching plugin exists.
- **Karameru / Kuriimu-family tools**: reported by MHST1 rippers as useful for archive/resource exploration.
- **MT Framework 3DS/Noesis plugins**: useful reference for `.tex` and `.mod` variants, but expect per-game differences.

## Known limitations

- This toolkit does **not** include copyrighted game assets.
- It does not guarantee importing arbitrary brand-new skeletons. Start with an existing skeleton/animation set.
- It cannot map every `table.arc` field without the real `table.arc` and `battleparm` files. The supplied files were mostly loose resources plus the existing loader.
- New ARC-entry insertion uses a deterministic CRC32 fallback for the entry hash. Existing-entry replacement preserves the original hash. If the game requires a different hash for new entries, provide `hash_override` in the manifest or prefer full-table replacement after mapping the correct hash.

## New monster checklist

- [ ] New/clone resource folder present under `files/mod/...`.
- [ ] `.mrl` points to the intended texture paths.
- [ ] `.tex` files exist for every material reference.
- [ ] Existing `.lmt`/`.lcm` animation/camera data reused or provided.
- [ ] `MonsterData.bin` row cloned and ID changed.
- [ ] `OtomonData.bin` row cloned if rideable.
- [ ] `monster_enum_conversion_table_data` row links species → battle enemy → buddy ID.
- [ ] Battle tables/movesets exist for enemy and rider sides.
- [ ] Egg, drops, item/material, equipment, quest, and text rows are patched.
- [ ] Install/uninstall tested from a clean backup.
