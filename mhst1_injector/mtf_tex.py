from __future__ import annotations

import argparse, json, struct
from dataclasses import dataclass, asdict
from pathlib import Path

MAGIC=b'TEX\0'
FORMAT_NAMES={
    0x07:'R8G8B8A8_UNORM',0x13:'BC1/DXT1',0x14:'BC1/DXT1_sRGB?',0x15:'BC2/DXT3',
    0x17:'BC3/DXT5',0x18:'BC3/DXT5_sRGB?',0x19:'BC4/ATI1',0x1F:'BC5/ATI2',
    0x28:'B8G8R8A8_UNORM',0x2A:'BC3/DXT5',0x2B:'BC3_sRGB_DX10',0x30:'BC7_UNORM',
    0x31:'BC7_UNORM_SRGB',0x36:'observed_MHST1_unknown_or_mobile_variant'
}

@dataclass
class TexInfo:
    path: str
    size: int
    width: int
    height: int
    mip_count: int
    format: int
    format_name: str
    data_offset: int
    mip_offsets: list[int]
    notes: list[str]


def parse_tex(path: str|Path) -> TexInfo:
    p=Path(path); b=p.read_bytes()
    if len(b)<0x18 or b[:4]!=MAGIC: raise ValueError(f'Not a TEX file: {p}')
    packed=struct.unpack_from('<I',b,0x08)[0]
    mip_count=packed & 0x3f
    width=(packed & 0x0007FFC0)>>6
    height=(packed & 0xFFF80000)>>19
    fmt=b[0x0d]
    data_offset=struct.unpack_from('<I',b,0x10)[0]
    # MHST1 stores mip offsets as u64-ish pairs after 0x18 when data_offset > 0x18.
    mip_offsets=[]
    if data_offset>=0x18 and data_offset<=len(b):
        for off in range(0x18, min(data_offset, len(b)-7), 8):
            lo,hi=struct.unpack_from('<II',b,off)
            if hi==0 and lo < len(b): mip_offsets.append(lo)
    notes=[]
    notes.append('Header packing matches RandomTBush MT Framework Switch TEX notes: mip bits 0..5, width bits 6..18, height bits 19..31; format byte at 0x0D.')
    notes.append('Writing is intentionally conservative: same-header/same-size TEX replacement is supported; arbitrary DDS-to-TEX swizzle/encode is not yet implemented here.')
    return TexInfo(str(p),len(b),width,height,mip_count,fmt,FORMAT_NAMES.get(fmt,f'unknown_0x{fmt:02x}'),data_offset,mip_offsets,notes)


def replace_payload_same_layout(base_tex: str|Path, donor_tex: str|Path, out_tex: str|Path) -> None:
    base=Path(base_tex).read_bytes(); donor=Path(donor_tex).read_bytes()
    bi=parse_tex(base_tex); di=parse_tex(donor_tex)
    checks=['width','height','mip_count','format','data_offset','size']
    for c in checks:
        if getattr(bi,c)!=getattr(di,c):
            raise SystemExit(f'{c} mismatch base={getattr(bi,c)} donor={getattr(di,c)}; use same-layout donor TEX')
    # Preserve base header bytes and transplant donor payload. This keeps paths/archive context stable.
    out=bytearray(base)
    out[bi.data_offset:]=donor[di.data_offset:]
    Path(out_tex).write_bytes(out)


def cmd_info(args):
    info=parse_tex(args.tex)
    if args.json: print(json.dumps(asdict(info),indent=2))
    else:
        print(f'{info.path}: {info.width}x{info.height} mips={info.mip_count} fmt=0x{info.format:02x} {info.format_name} data=0x{info.data_offset:x} size={info.size}')
        if info.mip_offsets: print('mip offsets:', ', '.join(hex(x) for x in info.mip_offsets))
        for n in info.notes: print('note:',n)

def cmd_replace(args): replace_payload_same_layout(args.base,args.donor,args.out)

def main(argv=None):
    p=argparse.ArgumentParser(description='MHST1/MT Framework Mobile TEX inspector and conservative same-layout writer')
    sub=p.add_subparsers(required=True)
    s=sub.add_parser('info'); s.add_argument('tex'); s.add_argument('--json',action='store_true'); s.set_defaults(func=cmd_info)
    s=sub.add_parser('replace-same-layout'); s.add_argument('base'); s.add_argument('donor'); s.add_argument('out'); s.set_defaults(func=cmd_replace)
    args=p.parse_args(argv); args.func(args); return 0
if __name__=='__main__': raise SystemExit(main())
