# Research notes: Monster Hunter Stories 1 / MT Framework Mobile modding

## Confirmed / useful leads

### MT Framework Mobile archives
- Capcom's mobile/3DS MT Framework titles commonly use `.arc` containers; encrypted variants may identify as `ARCC`.
- `jamesu/mtmobile-tools` is directly relevant: it targets MT Framework Mobile files, says it can extract/repack MT Framework mobile `.arc` files for iOS, and documents `decryptArcTool` for `create`, `extract`, and `dump`. It notes Blowfish-encrypted archives and a separate DLC/IAP key path.
- Kuriimu issue discussion says `ARCC` is an encrypted Capcom MT ARC variant and that Kuriimu2 can detect/decrypt/load those archives in at least some cases.
- FluffyQuack ARCtool added support for 3DS Monster Hunter 4 `.arc` files and may support other MT Framework Mobile games; this is a strong lead for 3DS/Mobile-adjacent archive behavior.

### General MT Framework ARC tooling
- `gibbed/Gibbed.MT` provides experimental `.arc` unpacker/packer tools for MT Framework games.
- FluffyQuack `ARCtool` is a long-standing MT Framework archive extractor/repacker; reported support varies by game/version.
- `Silvris/MH-Tools-and-Scripts` contains Monster Hunter file scripts and is cited by MHS2 tools.
- `Fexty12573/mhst2-arc-tool` wraps/extends Silvris' Monster Hunter Stories 2 ARC scripts and shows the common workflow: unpack archive, preserve `orderlog.txt`, repack using original order.

### MHST1-specific state of the community
- MHST1 has a small modding scene compared to newer Monster Hunter titles.
- Nexus currently has MHS1 remaster mods, but public tooling appears thinner than MHS2/World/Rise/Wilds.
- VG Resource threads show people have extracted MHST1 `.arc` folders, then hit walls on `.tex`/`.mod` assets. This suggests archive extraction is possible for at least some platform/builds, while inner resource formats need more work.

## Practical conclusion
The safe engineering path is:
1. Build a platform-neutral injector scaffold now.
2. Make the archive backend pluggable.
3. Add an `arc_probe` tool that identifies magic/version/endian/compression/encryption hints from user-owned samples.
4. Implement loose-file staging immediately.
5. Implement true ARC repack/injection after confirming exact MHST1 container variant and table formats.

## Open-source components worth integrating/adapting
- `jamesu/mtmobile-tools` — MT Framework Mobile ARC extraction/repacking concepts.
- `gibbed/Gibbed.MT` — MT Framework ARC pack/unpack architecture.
- `Silvris/MH-Tools-and-Scripts` — Monster Hunter data/archive scripts.
- `Kuriimu2` / `Every File Explorer` / `Karameru` — format exploration and plugin ideas.
- `ARCtool` — compatibility reference for MT Framework `.arc` behavior.

## Legal/safety boundary for this project
This toolkit is designed for user-owned files and personal/interoperability modding. It should not distribute copyrighted game assets, keys, decrypted assets, or DRM circumvention material. The injector should operate on files the user supplies locally.
