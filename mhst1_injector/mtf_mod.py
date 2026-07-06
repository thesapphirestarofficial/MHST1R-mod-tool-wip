from __future__ import annotations

import argparse, json, struct, shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

MAGIC = b"MOD\0"
HEADER_SCAN_LIMIT = 0x100
OFFSET_TABLE_START = 0x28
OFFSET_TABLE_END = 0x60

@dataclass
class ModSection:
    index: int
    offset: int
    size: int
    sha256_hint: str | None = None

@dataclass
class ModInfo:
    path: str
    size: int
    magic: str
    u32_header: list[int]
    sections: list[ModSection]
    notes: list[str]


def _u32s(data: bytes, count: int = 64) -> list[int]:
    n = min(len(data) // 4, count)
    return list(struct.unpack_from('<' + 'I' * n, data, 0))


def discover_section_offsets(data: bytes) -> list[int]:
    """Discover likely section offsets in an MHST1/MTF Mobile MOD.

    The supplied files store a sequence of little-endian 64-bit offsets between
    0x28 and 0x60.  Most high dwords are zero.  Not every slot is populated.
    This intentionally keeps unknown sections opaque; it is a safe foundation
    for same-layout patching and RE notes without pretending the format is
    fully solved.
    """
    size = len(data)
    offsets: list[int] = []
    for off in range(OFFSET_TABLE_START, min(OFFSET_TABLE_END, size - 7), 8):
        lo, hi = struct.unpack_from('<II', data, off)
        if hi != 0:
            continue
        if 0 < lo < size:
            offsets.append(lo)
    # Some files end with a 4-byte sentinel/padding and the last section offset
    # points to size-4. Keep size as the terminal boundary.
    offsets = sorted(set(offsets))
    if not offsets or offsets[0] > 0x4000:
        offsets.insert(0, 0xA4 if size > 0xA4 else 0)
    return offsets


def parse_mod(path: str | Path) -> ModInfo:
    p = Path(path)
    data = p.read_bytes()
    if len(data) < 4 or data[:4] != MAGIC:
        raise ValueError(f'Not an MHST1/MTF MOD file: {p}')
    offs = discover_section_offsets(data)
    bounds = offs + [len(data)]
    sections: list[ModSection] = []
    for i, off in enumerate(offs):
        nxt = bounds[i + 1]
        if nxt > off:
            sections.append(ModSection(i, off, nxt - off))
    notes = []
    hdr = _u32s(data[:HEADER_SCAN_LIMIT])
    if len(hdr) > 6:
        notes.append('u32[3], u32[4], u32[5], u32[6] correlate strongly with mesh/table counts and the largest binary payload length in supplied samples.')
    notes.append('Section labels are intentionally opaque until validated against Blender/importer code or in-game load tests.')
    return ModInfo(str(p), len(data), 'MOD\\0', hdr, sections, notes)


def write_manifest(path: str | Path, out_json: str | Path) -> None:
    info = parse_mod(path)
    Path(out_json).write_text(json.dumps(asdict(info), indent=2), encoding='utf-8')


def split_sections(path: str | Path, out_dir: str | Path) -> None:
    p = Path(path); out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    data = p.read_bytes(); info = parse_mod(p)
    (out / 'manifest.json').write_text(json.dumps(asdict(info), indent=2), encoding='utf-8')
    # Preserve the header/prefix before the first discovered section.
    first = info.sections[0].offset if info.sections else len(data)
    (out / 'header.bin').write_bytes(data[:first])
    for s in info.sections:
        (out / f'section_{s.index:02d}_0x{s.offset:08x}.bin').write_bytes(data[s.offset:s.offset+s.size])


def rebuild_from_split(folder: str | Path, out_mod: str | Path) -> None:
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    header = (folder / 'header.bin').read_bytes()
    size = manifest['size']
    out = bytearray(b'\0' * size)
    out[:len(header)] = header
    for s in manifest['sections']:
        candidates = list(folder.glob(f"section_{s['index']:02d}_0x{s['offset']:08x}.bin"))
        if not candidates:
            raise SystemExit(f"Missing section {s['index']} at 0x{s['offset']:x}")
        blob = candidates[0].read_bytes()
        if len(blob) != s['size']:
            raise SystemExit(f"Section {s['index']} size changed: got {len(blob)}, expected {s['size']}. Same-layout rebuild only.")
        out[s['offset']:s['offset']+s['size']] = blob
    Path(out_mod).write_bytes(out)


def same_layout_replace(base_mod: str | Path, donor_mod: str | Path, out_mod: str | Path, *, replace_sections: Iterable[int] | None = None) -> None:
    """Create a MOD by copying selected opaque sections from a donor MOD.

    This is useful for controlled experiments: if a Blender/exporter can produce
    a same-layout MOD (same section sizes/counts), this safely splices its mesh
    payload into a known-good base while preserving base metadata. It deliberately
    refuses arbitrary topology changes.
    """
    base = Path(base_mod).read_bytes(); donor = Path(donor_mod).read_bytes()
    bi = parse_mod(base_mod); di = parse_mod(donor_mod)
    if len(bi.sections) != len(di.sections):
        raise SystemExit('Section count mismatch; refusing unsafe splice')
    want = set(replace_sections) if replace_sections is not None else {s.index for s in bi.sections}
    out = bytearray(base)
    for bs, ds in zip(bi.sections, di.sections):
        if bs.index not in want:
            continue
        if bs.size != ds.size:
            raise SystemExit(f'Section {bs.index} size mismatch base={bs.size} donor={ds.size}')
        out[bs.offset:bs.offset+bs.size] = donor[ds.offset:ds.offset+ds.size]
    Path(out_mod).write_bytes(out)


def cmd_info(args):
    info = parse_mod(args.mod)
    if args.json:
        print(json.dumps(asdict(info), indent=2))
    else:
        print(f"{info.path}: {info.size} bytes")
        print('header u32[0:24]=', info.u32_header[:24])
        for s in info.sections:
            print(f"section {s.index:02d}: off=0x{s.offset:08x} size=0x{s.size:x} ({s.size})")
        for n in info.notes:
            print('note:', n)

def cmd_split(args): split_sections(args.mod, args.out)
def cmd_rebuild(args): rebuild_from_split(args.folder, args.out)
def cmd_splice(args):
    sections = None if not args.sections else [int(x,0) for x in args.sections.split(',')]
    same_layout_replace(args.base, args.donor, args.out, replace_sections=sections)


def main(argv=None):
    p = argparse.ArgumentParser(description='Experimental MHST1/MT Framework Mobile MOD analyzer and same-layout writer')
    sub = p.add_subparsers(required=True)
    s=sub.add_parser('info'); s.add_argument('mod'); s.add_argument('--json', action='store_true'); s.set_defaults(func=cmd_info)
    s=sub.add_parser('split'); s.add_argument('mod'); s.add_argument('out'); s.set_defaults(func=cmd_split)
    s=sub.add_parser('rebuild'); s.add_argument('folder'); s.add_argument('out'); s.set_defaults(func=cmd_rebuild)
    s=sub.add_parser('splice-same-layout'); s.add_argument('base'); s.add_argument('donor'); s.add_argument('out'); s.add_argument('--sections', help='comma-separated section indexes; default all'); s.set_defaults(func=cmd_splice)
    args=p.parse_args(argv); args.func(args); return 0

if __name__ == '__main__':
    raise SystemExit(main())
