# MHST1 Remaster PC 1.1.0 technical format notes

These notes are based on the supplied `battleparm`, `event`, `lyt`, `message_R`, `story`, and archive folders.

## ARC v7 container

All sampled `.arc` files use plain `ARC\0`, not `ARCC`.

```text
0x00  char[4]  magic = "ARC\0"
0x04  u16      version = 7
0x06  u16      entry_count
0x08  entries[entry_count]
```

Each entry is `0x90` bytes:

```text
0x00  char[0x80]  internal path, null-padded, usually backslash-separated
0x80  u32         stored hash / lookup value
0x84  u32         compressed size
0x88  u32         uncompressed size ORed with flags
0x8C  u32         data offset
```

Known flag:

```text
0x40000000 = zlib compressed payload
0x3fffffff = uncompressed-size mask
```

Payload offsets are aligned. In the supplied samples, the first payload commonly starts at the next `0x8000` boundary after the entry table, and individual entries are aligned to `0x10`.

## XFS tables

Many decompressed table entries start with:

```text
58 46 53 00 = "XFS\0"
```

Observed fields:

```text
0x00  char[4]  XFS magic
0x04  u16/u16  version-ish values, commonly 0x10 and a table type/group
0x08  u32      row count in many tables
```

Field names often appear around `0x200`, e.g.:

```text
mVersion\0mpArray\0mQuality\0mAutoDelete\0mName\0...
```

Because XFS rows are not self-describing enough for perfect high-level editing yet, the loader uses **clone-row patches**. This is deliberate: clone a known valid row and edit specific offsets.

## Loose battleparm tables

The supplied `battleparm` folder contains fixed-row binary tables with a `u16` count at offset 0 and rows immediately after offset 2.

| File | Rows | Row size | Purpose |
|---|---:|---:|---|
| `MonsterData.bin` | 555 | 134 | enemy/monster battle parameters |
| `OtomonData.bin` | 256 | 146 | monstie/player-side monster parameters |
| `MonsterBaseData.bin` | 100 | 60 | base monster parameters |
| `PlayerData.bin` | 101 | 22 | rider/player parameters |
| `addParam.bin` | 256 | 4 | additive battle parameters |
| `adjustData.bin` | 256 | 4 | adjustment parameters |

## High-value table.arc entries

These are important for content expansion:

- `table\item_data` — item/material records
- `table\skill_table` — skills/moves
- `table\armor_data` — armor records
- `table\armor_param` — armor stats/parameters
- `table\armor_create` — crafting/create data
- `table\questList` — quest list
- `table\mainQuest` — main quest data
- `table\monster_book_data` — monster book/encyclopedia data
- `table\monster_enum_conversion_table_data` — maps monster IDs/enemy IDs/buddy IDs
- `table\egg` — egg data
- `table\battle_enemy_file` — enemy file/resource table
- `table\battle_enemy_set` — enemy encounter/party setups
- `table\battle_table_em###` — enemy battle table entries by monster/enemy number
- `table\battle_table_p_em###` — player/monstie-side battle entries by enemy number
- `table\battle_atk_em###` — enemy attack/moveset table
- `table\battle_atk_eff_em###` — enemy attack effects
- `table\battle_atk_rd###` — rider/monstie attack tables
- `table\battle_atk_eff_rd###` — rider/monstie attack effects

## Loader strategy

1. Use direct file/entry replacement when a mod ships a complete edited table.
2. Use clone-row patches for additive work.
3. Preserve ARC order/hash/compression for compatibility.
4. Keep original files in `_mhst1_backup` before writing.
