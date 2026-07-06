# Custom meshes and textures for MHST1 Remaster

This document is the current practical path for adding a unique visible monster model/texture set to **Monster Hunter Stories 1 Remaster PC**.

## Bottom line

There is now enough tooling to package and install **custom resource files** into the game folder, and enough reverse-engineering to safely inspect and same-layout rebuild `.mod` and `.tex` files.

The remaining hard blocker is a true arbitrary `.mod` exporter: changing vertex counts, index counts, material-slot counts, LOD counts, or skeleton layout requires a full writer. Public tools found so far are mostly importers/viewers or writers for other MT Framework variants.

## Public tools/research found

Use these as references, but do not assume format compatibility without testing on MHST1 Remaster files.

| Tool/source | What it helps with | Status for this toolkit |
|---|---|---|
| `Feuleur/blender-mhst1-tools-suite` | Blender import suite for MHST1 files. Imports `.mod`, `.tex`, and `.lmt`; README says monster models are in `mod/mo`, animations in `mot/mo`, maps in `stage`. | Best public game-specific importer found. It is import-focused, not a confirmed writer/exporter. |
| `xZombieAlix/MT-Framework-Mobile---Blender-Model-Script` | MT Framework Mobile Blender model script; credits Seth VanHeulen MH4U importer, HZDMeshTool export code, and Albam tri-list/tri-strip code. | Promising reference for a writer path, but not yet validated against MHST1 Remaster PC files. |
| `PredatorCZ/RevilMax` / LukasCone MT Framework tools | 3ds Max importer for many MT Framework games, including several 3DS/Mobile-era games. | Strong format reference; not MHST1 Remaster-specific and not a confirmed arbitrary writer for this variant. |
| RandomTBush `CapcomMTFrameworkSwitch_TEX.bms` | Documents many `.tex` header fields/formats and swizzle-to-DDS extraction logic. | Used as a reference for `mtf_tex.py` header decoding. |
| `svanheulen/mhff` | Monster Hunter 3DS file-format scripts. | Useful older reference for MT Framework Mobile-era assumptions. |
| ARCtool / FluffyQuack MT Framework ARC tooling | ARC/TEX/XFS workflow reference for MT Framework games. | Useful external reference; this toolkit already includes a native MHST1 ARC v7 implementation. |

## What the supplied files show

The supplied resources contain:

- `334` `.mod` model files.
- `652` `.tex` texture files.
- `334` `.mrl` material libraries.
- `103` `.lmt` animation files.
- `87` `.sbc` files and several `.ctc`, `.cli`, `.omi` files.

Important observed paths:

```text
mod/om/om###/*.mod + *.mrl + *.tex    object models
mod/som/som###/*.mod + *.mrl + *.tex   small/object-style model sets
mod/sd/sd###/*.mod + *.mrl + *.tex     SD model sets
mod/sd_low/sd###/*.mod + *.mrl + *.tex lower detail SD sets
stage/.../*.mod + *.tex                map/stage resources
battleai/*.bin                         AI script-like resources
system/system/texture/*.tex            shared system textures
```

The toolkit README previously described `mod/mo` for monster resources because public MHST1 import tools use that path. Your supplied package did not include a populated `mod/mo` model folder; it included `om`, `som`, `sd`, and `sd_low` model sets plus monster animation/camera folders. If your full game install has `mod/mo`, scan it with `tools/resource_scan.py` and use the same workflow.

## New tools added

### `mhst1_injector.mtf_mod`

Experimental `.mod` analyzer and conservative same-layout writer.

```bat
python -m mhst1_injector.mtf_mod info path\to\model.mod
python -m mhst1_injector.mtf_mod info path\to\model.mod --json > model.mod.json
python -m mhst1_injector.mtf_mod split path\to\model.mod split_model
python -m mhst1_injector.mtf_mod rebuild split_model rebuilt.mod
python -m mhst1_injector.mtf_mod splice-same-layout base.mod donor.mod out.mod
```

What it can safely do now:

- Parse the header and discovered section boundaries.
- Split `.mod` into opaque sections for hex-diffing and controlled experiments.
- Rebuild a split file byte-for-byte if section sizes are unchanged.
- Splice sections from a donor `.mod` into a base `.mod` only when section counts and section sizes match.

What it deliberately refuses:

- Arbitrary topology changes.
- Vertex count changes.
- New material-slot counts.
- New LOD counts.
- New skeleton/bone tables.

This is intentional. A partial writer that silently corrupts files is worse than no writer.

### `mhst1_injector.mtf_tex`

Experimental `.tex` inspector and conservative same-layout texture payload writer.

```bat
python -m mhst1_injector.mtf_tex info path\to\texture.tex
python -m mhst1_injector.mtf_tex info path\to\texture.tex --json > texture.tex.json
python -m mhst1_injector.mtf_tex replace-same-layout base.tex donor.tex out.tex
```

What it can safely do now:

- Decode common header fields:
  - width
  - height
  - mip count
  - format byte
  - data offset
  - mip offsets
- Replace a texture payload only when the donor has the same dimensions, mip count, format, data offset, and total size.

What is not implemented yet:

- Full DDS/PNG → `.tex` encoding.
- Full reverse swizzle for every observed MHST1 format.

Use external texture tools for conversion while this gets expanded.

## Current `.mod` structure notes

All sampled `.mod` files start with:

```text
0x00 char[4] = "MOD\0"
```

The first 0x60 bytes contain counts and a table of 64-bit little-endian section offsets. In the supplied files, the high dword of each offset is zero.

Typical observed header slots:

```text
0x00  magic = MOD\0
0x04  packed/version-ish field; often 214, 65750, 131286, etc.
0x08  packed count-ish field; often looks like two u16 values
0x0C  count-ish value; correlates with mesh/vertex/table data
0x10  count-ish value; correlates with mesh/vertex/table data
0x14  count-ish value; correlates with mesh/vertex/table data
0x18  large payload length in many files
0x20  material/submesh/LOD-ish count in many files
0x28..0x60  likely 64-bit section offsets
```

Example for `om002.mod` from the supplied files:

```text
size: 260616
u32[0:24]: [4476749, 65750, 65546, 10155, 25421, 17120, 203100, 0, 4, 0, 164, 0, 4412, 0, 4540, 0, 4668, 0, 6668, 0, 209768, 0, 260612, 0]

section 00: off=0x000000a4 size=4248
section 01: off=0x0000113c size=128
section 02: off=0x000011bc size=128
section 03: off=0x0000123c size=2000
section 04: off=0x00001a0c size=203100
section 05: off=0x00033368 size=50844
section 06: off=0x0003fa04 size=4
```

Based on size behavior across files, section 04 is very likely the largest geometry/index payload in many models, but section names are intentionally not finalized yet. Validate against Blender/importer code before assigning semantic labels.

## Current `.tex` structure notes

All sampled `.tex` files start with:

```text
0x00 char[4] = "TEX\0"
```

Header decoding follows the RandomTBush MT Framework Switch TEX script pattern:

```text
0x08 packed data block:
  bits 0..5    mip count
  bits 6..18   width
  bits 19..31  height
0x0D format byte
0x10 data offset
0x18 mip-offset table begins in many files
```

Example for `om002_BM.tex`:

```text
64x64, 7 mips, format 0x13 (BC1/DXT1), data offset 0x48, size 2816
mip offsets: 0x848, 0xa48, 0xac8, 0xae8, 0xaf0, 0xaf8
```

Observed format bytes in supplied samples include known MT Framework values such as `0x07`, `0x13`, `0x14`, `0x17`, `0x19`, `0x2A`, and `0x36`. `0x36` appears in several MHST1 map marker/map textures and needs specific validation.

## Practical custom mesh path: existing skeleton

This is the path to use first.

### 1. Pick a base monster/skeleton

Pick an existing monster with a similar body plan:

- Flying wyvern → flying wyvern base.
- Fanged beast → fanged beast base.
- Leviathan-like → closest long-body base.

The point is to reuse:

- bone hierarchy
- animation set
- hit/camera assumptions
- material-slot expectations
- LOD structure

### 2. Import the base model into Blender

Use the best game-specific importer available, currently `Feuleur/blender-mhst1-tools-suite` for MHST1 import.

Import:

- base `.mod`
- associated `.mrl`
- `.tex` files
- relevant `.lmt` animation for checking deformation

### 3. Build the custom mesh on the existing armature

In Blender:

- Keep the original armature/bone names and hierarchy.
- Create your custom mesh in the same coordinate scale/orientation.
- Transfer weights from the base mesh where possible.
- Limit each vertex to the same max bone influence count used by the base file. If unknown, assume 4 and test.
- Normalize weights.
- Keep material slot count and LOD count unchanged for same-layout experiments.

### 4. Export through the closest writer available

If `xZombieAlix/MT-Framework-Mobile---Blender-Model-Script` can export a same-layout `.mod` for this variant, use it as the donor output.

If it exports but the game crashes, do not keep blindly changing art. Split and compare:

```bat
python -m mhst1_injector.mtf_mod split base.mod split_base
python -m mhst1_injector.mtf_mod split exported.mod split_export
```

Then compare section sizes and binary layout. The first target is a same-layout export where all section sizes match.

### 5. Same-layout splice test

When donor section sizes match:

```bat
python -m mhst1_injector.mtf_mod splice-same-layout base.mod exported.mod custom.mod
```

Install `custom.mod` in the new monster resource folder and test.

This is the safest first custom mesh writer workflow because it preserves base metadata and only swaps compatible payload sections.

### 6. Package into a new monster mod

Create a mod folder:

```text
mods/my.custom.monster/
  mod.json
  files/
    mod/
      mo/
        mo901/
          mo901.mod
          mo901.mrl
          mo901_BM.tex
          mo901_CMM.tex
  tables/
    ...finished clone-row patches...
```

`mod.json` should include the resource files:

```json
{
  "id": "author.custom_monster",
  "name": "Custom Monster",
  "version": "0.1.0",
  "priority": 100,
  "files": [
    { "game_path": "native:/mod/mo/mo901/mo901.mod", "source": "files/mod/mo/mo901/mo901.mod" },
    { "game_path": "native:/mod/mo/mo901/mo901.mrl", "source": "files/mod/mo/mo901/mo901.mrl" },
    { "game_path": "native:/mod/mo/mo901/mo901_BM.tex", "source": "files/mod/mo/mo901/mo901_BM.tex" },
    { "game_path": "native:/mod/mo/mo901/mo901_CMM.tex", "source": "files/mod/mo/mo901/mo901_CMM.tex" }
  ],
  "table_patches": [
    "tables/monsterdata.json",
    "tables/otomondata.json",
    "tables/monster_enum.json",
    "tables/egg.json",
    "tables/drops.json",
    "tables/quests.json"
  ]
}
```

Then use existing clone-row patches for the data graph.

## Practical custom texture path

### Same-layout texture replacement

1. Pick a base `.tex` with the desired dimensions and format.
2. Use an external TEX workflow/importer to create a donor `.tex` with exactly the same layout.
3. Validate:

```bat
python -m mhst1_injector.mtf_tex info base.tex
python -m mhst1_injector.mtf_tex info donor.tex
```

4. Replace payload conservatively:

```bat
python -m mhst1_injector.mtf_tex replace-same-layout base.tex donor.tex out.tex
```

5. Put `out.tex` into your mod folder and point the `.mrl` at it.

### Material path patching

Use:

```bat
python tools\patch_mrl_paths.py path\to\file.mrl --backup --replace "old\path\old_BM" "new\path\new_BM"
```

New string must be the same length or shorter unless the `.mrl` writer is expanded.

## Custom skeleton path

Avoid custom skeletons until same-layout mesh replacement works reliably.

If someone insists on a custom skeleton, the required work is:

1. Fully label `.mod` skeleton/bone table sections.
2. Identify bone-name/index storage and parent indices.
3. Identify inverse bind pose matrix layout.
4. Identify per-vertex bone index and weight streams.
5. Identify animation `.lmt` bone-channel mapping.
6. Export a model with one extra non-used bone and confirm the game still loads.
7. Export a model where vertices reference that extra bone and confirm deformation.
8. Only then attempt a real new skeleton.

Do not start with an imported skeleton from another game. Start with one extra dummy bone in an existing MHST1 skeleton and prove the table/linkage is understood.

## Map/stage RE notes for later

Map work is separate from monster work. Your supplied `stage.zip` contains stage models and textures, including:

```text
stage/stage/.../*.mod
stage/stage/.../*.tex
stage/stage/.../map/*.mod
stage/stage/.../col_g/*.mod
```

Likely investigation order:

1. Inventory stage folders and correlate names with in-game areas.
2. Split map `.mod` files with `mhst1_injector.mtf_mod split`.
3. Compare render map models vs `col_g` collision models.
4. Search for navmesh/zone/streaming references in adjacent non-`.mod` files.
5. Import stage `.mod` with the MHST1 Blender importer and compare visible geometry to collision resources.
6. Treat collision/navmesh as separate binary formats until proven otherwise.

Do not block monster work on map RE.

## Validation checklist

For every custom mesh/texture experiment:

- [ ] Back up vanilla files.
- [ ] Confirm the base model loads before editing.
- [ ] Keep skeleton, material-slot count, LOD count, and section sizes unchanged for first test.
- [ ] Run `mtf_mod info` before and after export.
- [ ] Run `mtf_tex info` before and after texture changes.
- [ ] Install as loose files first, not inside an ARC, if the game accepts loose overrides.
- [ ] Test boot → load save → encounter/preview monster → trigger animation → battle → mount/ride if applicable.
- [ ] If it crashes, compare section sizes first before editing art again.
