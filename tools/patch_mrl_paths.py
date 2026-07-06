#!/usr/bin/env python3
"""Patch texture paths inside MHST1 .mrl material files.

The MRL files store null-padded ASCII texture paths. This tool does binary-safe replacement.
New paths must not be longer than the original path unless you are deliberately editing the
MRL structure by hand. Shorter paths are padded with NUL bytes.
"""
from __future__ import annotations
import argparse
from pathlib import Path

def patch_bytes(data: bytes, old: bytes, new: bytes):
    if len(new)>len(old):
        raise SystemExit(f'New path is longer than old path ({len(new)} > {len(old)}). Keep folder/id names equal length or patch manually.')
    return data.replace(old, new + b'\0'*(len(old)-len(new)))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('file', help='.mrl file to patch in-place')
    ap.add_argument('--replace', action='append', nargs=2, metavar=('OLD','NEW'), required=True,
                    help='Replace OLD texture path with NEW texture path. Repeatable.')
    ap.add_argument('--backup', action='store_true')
    args=ap.parse_args()
    p=Path(args.file)
    data=p.read_bytes()
    if args.backup:
        p.with_suffix(p.suffix+'.bak').write_bytes(data)
    for old,new in args.replace:
        oldb=old.encode('ascii')
        newb=new.encode('ascii')
        if oldb not in data:
            print(f'WARN: not found: {old}')
        data=patch_bytes(data, oldb, newb)
    p.write_bytes(data)
    print(f'Patched {p}')
if __name__=='__main__': main()
