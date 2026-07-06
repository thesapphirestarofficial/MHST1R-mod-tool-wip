from __future__ import annotations

import argparse
import json
import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC = b'XFS\0'

@dataclass
class XfsInfo:
    row_count: int
    row_stride: int
    row_base: int
    field_names: list[str]


def cstrings(data: bytes, start: int, end: int) -> list[str]:
    out=[]
    for part in data[start:end].split(b'\0'):
        if len(part) >= 2:
            try:
                s=part.decode('utf-8')
            except Exception:
                try: s=part.decode('shift_jis')
                except Exception: continue
            if all((31 < ord(ch) < 0x30000) for ch in s): out.append(s)
    return out


def analyze(data: bytes) -> XfsInfo:
    if data[:4] != MAGIC:
        raise ValueError('not XFS')
    row_count = struct.unpack_from('<I', data, 8)[0]
    # Samples show metadata ends around 0x200 and field strings begin there.
    names = cstrings(data, 0x200, min(len(data), 0x800))
    # Best-effort row_base: first occurrence after field strings of repeated row marker 01 00 00 00.
    # For all shipped MHST1 tables, 0x248/0x300 are common. Use conservative scan.
    candidates=[]
    for off in range(0x240, min(len(data), 0x2000), 4):
        if off < len(data) and data[off:off+4] in (b'\x01\x00\x00\x00', b'\x00\x00\x00\x00'):
            rem = len(data)-off
            if row_count and rem > row_count and rem % row_count == 0:
                candidates.append((off, rem//row_count))
    if candidates:
        row_base,row_stride=candidates[0]
    else:
        # fallback: use final length/count approximation, modders can override in patch json
        row_base=0x300
        row_stride=max(1,(len(data)-row_base)//max(1,row_count))
    return XfsInfo(row_count,row_stride,row_base,names)


def patch_scalar(buf: bytearray, off: int, typ: str, value):
    fmt = {'u8':'<B','s8':'<b','u16':'<H','s16':'<h','u32':'<I','s32':'<i','f32':'<f'}[typ]
    struct.pack_into(fmt, buf, off, value)


def clone_rows(data: bytes, spec: dict) -> bytes:
    info = analyze(data)
    row_count = int(spec.get('row_count', info.row_count))
    row_stride = int(spec.get('row_stride', info.row_stride))
    row_base = int(spec.get('row_base', info.row_base))
    out = bytearray(data)
    adds = spec.get('clone_rows') or spec.get('add') or []
    for add in adds:
        base_index = int(add.get('base_index', row_count - 1))
        if 'base_id' in add and 'id_offset' in add:
            # find first row whose ID field equals base_id
            idoff=int(add.get('id_offset',0)); typ=add.get('id_type','u32')
            fmt={'u16':'<H','u32':'<I'}[typ]
            for i in range(row_count):
                if struct.unpack_from(fmt, out, row_base+i*row_stride+idoff)[0] == int(add['base_id']):
                    base_index=i; break
        base = bytes(out[row_base+base_index*row_stride:row_base+(base_index+1)*row_stride])
        new = bytearray(base)
        for edit in add.get('set', []):
            patch_scalar(new, int(edit['offset']), edit.get('type','u32'), edit['value'])
        out.extend(new)
        row_count += 1
    # update row count at standard header offset
    struct.pack_into('<I', out, 8, row_count)
    return bytes(out)


def cmd_info(args):
    data=Path(args.file).read_bytes(); info=analyze(data)
    print(json.dumps(info.__dict__, indent=2))


def cmd_clone(args):
    data=Path(args.input).read_bytes(); spec=json.loads(Path(args.patch).read_text(encoding='utf-8'))
    Path(args.output).write_bytes(clone_rows(data,spec))


def main(argv=None):
    p=argparse.ArgumentParser(description='MHST1 XFS table inspector/clone patcher')
    sub=p.add_subparsers(required=True)
    s=sub.add_parser('info'); s.add_argument('file'); s.set_defaults(func=cmd_info)
    s=sub.add_parser('clone'); s.add_argument('input'); s.add_argument('patch'); s.add_argument('output'); s.set_defaults(func=cmd_clone)
    a=p.parse_args(argv); a.func(a); return 0
if __name__=='__main__': raise SystemExit(main())
