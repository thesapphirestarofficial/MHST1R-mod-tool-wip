from __future__ import annotations

import argparse
import json
import math
import os
import struct
import zlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

FLAG_ZLIB = 0x40000000
SIZE_MASK = 0x3FFFFFFF
ENTRY_SIZE = 0x90
NAME_SIZE = 0x80
DATA_ALIGN = 0x8000
ENTRY_ALIGN = 0x10

@dataclass
class ArcEntry:
    name: str
    hash: int
    compressed_size: int
    uncompressed_size: int
    flags: int
    offset: int
    index: int = 0

    @property
    def compressed(self) -> bool:
        return bool(self.flags & FLAG_ZLIB)


def align(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def mt_hash(name: str) -> int:
    # Placeholder/reference hash. MHST1 ARC stores a hash but the game also keeps names.
    # When replacing existing entries we preserve the original hash. For new entries this
    # deterministic CRC32 is used unless a mod explicitly provides hash_override.
    return zlib.crc32(name.encode('utf-8')) & 0xffffffff


class ArcArchive:
    def __init__(self, path: Path, entries: list[ArcEntry], data: bytes):
        self.path = Path(path)
        self.entries = entries
        self.data = data

    @classmethod
    def read(cls, path: str | Path) -> 'ArcArchive':
        path = Path(path)
        data = path.read_bytes()
        if len(data) < 8 or data[:4] != b'ARC\0':
            raise ValueError(f'Not a plain MHST/MT ARC file: {path}')
        version = struct.unpack_from('<H', data, 4)[0]
        if version != 7:
            # Do not hard-fail; PC Remaster samples are v7, but keep tool useful.
            pass
        count = struct.unpack_from('<H', data, 6)[0]
        entries: list[ArcEntry] = []
        for i in range(count):
            off = 8 + i * ENTRY_SIZE
            raw_name = data[off:off+NAME_SIZE].split(b'\0', 1)[0]
            name = raw_name.decode('utf-8', errors='replace')
            h, csize, usize_flags, data_off = struct.unpack_from('<IIII', data, off + NAME_SIZE)
            entries.append(ArcEntry(name, h, csize, usize_flags & SIZE_MASK, usize_flags & ~SIZE_MASK, data_off, i))
        return cls(path, entries, data)

    def list(self) -> list[dict]:
        return [asdict(e) | {'compressed': e.compressed} for e in self.entries]

    def get_entry(self, name: str) -> ArcEntry:
        norm = name.replace('/', '\\')
        for e in self.entries:
            if e.name == norm:
                return e
        raise KeyError(name)

    def read_entry(self, entry: ArcEntry | str, decompress: bool = True) -> bytes:
        if isinstance(entry, str):
            entry = self.get_entry(entry)
        blob = self.data[entry.offset:entry.offset + entry.compressed_size]
        if decompress and entry.compressed:
            return zlib.decompress(blob)
        return blob

    def extract_all(self, out_dir: Path, with_meta: bool = True) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = []
        for e in self.entries:
            raw = self.read_entry(e, True)
            dest = out_dir / e.name.replace('\\', '/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            manifest.append(asdict(e) | {'compressed': e.compressed})
        if with_meta:
            (out_dir / 'arc_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            (out_dir / 'orderlog.txt').write_text('\n'.join(e.name for e in self.entries) + '\n', encoding='utf-8')

    def rebuild(self, out_path: Path, replacements: dict[str, bytes] | None = None, add: dict[str, bytes] | None = None, compress_new: bool = True) -> None:
        replacements = {k.replace('/', '\\'): v for k, v in (replacements or {}).items()}
        add = {k.replace('/', '\\'): v for k, v in (add or {}).items()}
        new_entries: list[tuple[ArcEntry, bytes]] = []
        seen = set()
        for e in self.entries:
            raw = replacements.get(e.name, self.read_entry(e, True))
            seen.add(e.name)
            use_compress = e.compressed
            payload = zlib.compress(raw, 9) if use_compress else raw
            new = ArcEntry(e.name, e.hash, len(payload), len(raw), FLAG_ZLIB if use_compress else 0, 0, e.index)
            new_entries.append((new, payload))
        for name, raw in add.items():
            if name in seen:
                continue
            use_compress = compress_new
            payload = zlib.compress(raw, 9) if use_compress else raw
            new = ArcEntry(name, mt_hash(name), len(payload), len(raw), FLAG_ZLIB if use_compress else 0, 0, len(new_entries))
            new_entries.append((new, payload))

        header_size = 8 + len(new_entries) * ENTRY_SIZE
        data_off = align(header_size, DATA_ALIGN)
        parts = [bytearray(data_off)]
        out = parts[0]
        out[:4] = b'ARC\0'
        struct.pack_into('<HH', out, 4, 7, len(new_entries))
        cur = data_off
        payload_parts: list[bytes] = []
        for idx, (e, payload) in enumerate(new_entries):
            cur = align(cur, ENTRY_ALIGN)
            e.offset = cur
            e.index = idx
            ent_off = 8 + idx * ENTRY_SIZE
            nb = e.name.encode('utf-8')[:NAME_SIZE-1]
            out[ent_off:ent_off+len(nb)] = nb
            struct.pack_into('<IIII', out, ent_off + NAME_SIZE, e.hash, e.compressed_size, e.uncompressed_size | e.flags, e.offset)
            pad = cur - (data_off + sum(len(x) for x in payload_parts))
            if pad > 0:
                payload_parts.append(b'\0' * pad)
            payload_parts.append(payload)
            cur += len(payload)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(bytes(out) + b''.join(payload_parts))


def cmd_list(args):
    arc = ArcArchive.read(args.arc)
    if args.json:
        print(json.dumps(arc.list(), indent=2))
    else:
        for e in arc.entries:
            c = 'zlib' if e.compressed else 'raw'
            print(f'{e.index:04d} {e.name} off=0x{e.offset:x} csize={e.compressed_size} usize={e.uncompressed_size} {c}')


def cmd_extract(args):
    ArcArchive.read(args.arc).extract_all(Path(args.out))


def cmd_pack(args):
    src = Path(args.folder)
    manifest_path = src / 'arc_manifest.json'
    if not manifest_path.exists():
        raise SystemExit('arc_manifest.json missing; extract first so order/hash/compression are preserved')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    # Create a tiny dummy archive object from manifest and file payloads.
    entries = []
    blobs = bytearray()
    for i, m in enumerate(manifest):
        name = m['name']
        raw = (src / name.replace('\\','/')).read_bytes()
        comp = bool(m.get('compressed') or (m.get('flags',0) & FLAG_ZLIB))
        payload = zlib.compress(raw, 9) if comp else raw
        off = len(blobs); blobs += payload
        entries.append(ArcEntry(name, int(m['hash']), len(payload), len(raw), FLAG_ZLIB if comp else 0, off, i))
    dummy = ArcArchive(Path(args.folder), entries, bytes(blobs))
    # monkey read_entry because dummy offsets point into compact blob
    dummy.rebuild(Path(args.out), replacements={e.name: (src/e.name.replace('\\','/')).read_bytes() for e in entries})


def main(argv=None):
    p = argparse.ArgumentParser(description='MHST1 Remaster ARC v7 unpack/repack tool')
    sub = p.add_subparsers(required=True)
    s = sub.add_parser('list'); s.add_argument('arc'); s.add_argument('--json', action='store_true'); s.set_defaults(func=cmd_list)
    s = sub.add_parser('extract'); s.add_argument('arc'); s.add_argument('out'); s.set_defaults(func=cmd_extract)
    s = sub.add_parser('pack'); s.add_argument('folder'); s.add_argument('out'); s.set_defaults(func=cmd_pack)
    args = p.parse_args(argv); args.func(args); return 0

if __name__ == '__main__':
    raise SystemExit(main())
