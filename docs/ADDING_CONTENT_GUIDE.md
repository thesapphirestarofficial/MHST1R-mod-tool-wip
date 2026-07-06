# Adding new monsters, monsties, moves, AI, materials, equipment, and quests

This guide is written for MHST1 Remaster PC 1.1.0. The loader can install file overrides, ARC entry replacements, and clone-row patches. The easiest safe workflow is **clone an existing working monster chain, then edit IDs and references**.

## The data graph

A complete new monster/monstie is a connected graph:

```text
Monster identity
 ├─ monster enum conversion row
 ├─ monster book row
 ├─ localized message/text rows
 ├─ enemy battle parameter row(s)
 ├─ enemy battle table: table\battle_table_em###
 ├─ enemy moveset: table\battle_atk_em###
 ├─ enemy attack effects: table\battle_atk_eff_em###
 ├─ monstie/buddy parameter row: OtomonData.bin
 ├─ player-side battle table: table\battle_table_p_em###
 ├─ player-side/ride attacks: table\battle_atk_rd###
 ├─ egg row: table\egg
 ├─ drop/reward data
 ├─ materials: table\item_data + message text
 ├─ weapons/armor: armor/weapon tables + recipes
 └─ quests: questList/mainQuest/subquest-related tables
```

## Recommended ID policy

Use a reserved mod range so multiple mods can avoid collisions:

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

If two mods use the same IDs, the later priority wins or the game may read conflicting data. Keep IDs documented in your mod README.

## Workflow: add a new monster by cloning

### 1. Pick a base monster

Pick an existing monster that already has similar behavior, skeleton, and encounter logic. For example, if adding a Lagiacrus-like monster, clone a monster with similar body type and attack style.

Record:

- its enemy number (`em###`)
- its buddy/monstie ID if rideable
- its battleparm rows
- its battle table entries
- its attack/effect tables
- its item/material drops
- its monster book rows
- its text keys

### 2. Clone battle parameters

Create a patch like:

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

Then repeat for:

- `battleparm/MonsterBaseData.bin` if the base monster has a matching base row
- `battleparm/OtomonData.bin` if it is a monstie

### 3. Clone monster ID mapping

Patch `table.arc::table/monster_enum_conversion_table_data`. This table contains field names like:

```text
mID, mFieldEmSetNo, mBattleEmNo, mBuddyId
```

Use it to connect your new monster species ID to the battle enemy number and buddy/monstie ID.

### 4. Clone enemy battle table and AI/moveset

For enemy-side behavior, copy the relevant entries:

```text
table\battle_table_em###
table\battle_atk_em###
table\battle_atk_eff_em###
```

The simplest method is to ship full replacement/addition entries once you have edited them. If you are changing rows inside an existing XFS table, use clone-row patches.

### 5. Clone player/monstie battle data

For the rideable version, copy/edit:

```text
table\battle_table_p_em###
table\battle_atk_rd###
table\battle_atk_eff_rd###
```

The `rd###` tables appear to define rider/monstie attack behavior and effects.

### 6. Add egg data

Patch `table.arc::table/egg` by cloning an existing egg row. Update:

- egg ID
- buddy/monster ID reference
- rarity
- pattern/color references
- message/name references if present

### 7. Add materials

Patch `table.arc::table/item_data` for each material. Clone a similar material row and update:

- item ID
- item category/type
- rarity
- sell value
- message/text key references
- icon/category references if mapped

### 8. Add weapons and armor

Use the armor/equipment-related tables discovered in `table.arc`:

```text
table\armor_data
table\armor_param
table\armor_create
```

Weapon tables are partly represented through battle weapon entries and cheat-check tables; map exact weapon data by cloning existing weapon rows and comparing changed values.

For each equipment piece:

- clone base equipment row
- assign new equipment ID
- link materials in create/recipe table
- update stats in param table
- add localized name/description text

### 9. Add quests

Use:

```text
table\questList
table\mainQuest
table\fordev\fornative\sub_quest_flag
table\fordev\fornative\subQuestCount
table\dungeonQuest
```

Start by cloning an existing subquest with the same structure: hunt target, reward, unlock condition. Then update target monster ID and reward material IDs.

### 10. Add text

Text is in language archives such as:

```text
message_R/message_all_eng.arc
```

The loader can replace ARC entries. Message editing is best handled by extracting the message archive, editing the relevant message table once mapped, then shipping the edited entry as an ARC replacement.

## Example mod layout

```text
mods/AddAzureLagiacrus/
  mod.json
  tables/
    001_monsterdata.json
    002_otomondata.json
    003_monster_enum.json
    004_item_materials.json
    005_egg.json
    006_armor.json
    007_quest.json
  files/
    table/
      battle_table_em9001
      battle_atk_em9001
      battle_atk_eff_em9001
```

## Validation checklist

- [ ] Every new ID is unique.
- [ ] Every enemy-side ID has a matching battle table and moveset.
- [ ] Every monstie-side ID has OtomonData and player-side battle data.
- [ ] Egg row points to the new buddy/monstie.
- [ ] Item/material rows exist before recipes reference them.
- [ ] Equipment recipes reference valid materials.
- [ ] Quest target references valid monster/enemy IDs.
- [ ] Text/message keys exist for names and descriptions.
- [ ] The mod installs cleanly and backups are created.

## Practical advice

Do not start by making a totally new monster from nothing. First make a clone mod where the new ID behaves exactly like an existing monster. Once that loads, change one table at a time: stats, then name, then egg, then moves, then drops, then equipment/quest integration.
