from __future__ import annotations
import argparse, json, struct
from pathlib import Path

KNOWN = {
 'MonsterData.bin': {'header':2,'count_type':'u16','row_size':134,'domain':'enemy/monster battle parameters'},
 'OtomonData.bin': {'header':2,'count_type':'u16','row_size':146,'domain':'monstie/player-side monster parameters'},
 'MonsterBaseData.bin': {'header':2,'count_type':'u16','row_size':60,'domain':'base monster parameters'},
 'PlayerData.bin': {'header':2,'count_type':'u16','row_size':22,'domain':'rider/player parameters'},
 'addParam.bin': {'header':2,'count_type':'u16','row_size':4,'domain':'additive battle parameters'},
 'adjustData.bin': {'header':2,'count_type':'u16','row_size':4,'domain':'adjustment parameters'},
}

def info(path: Path):
    data=path.read_bytes(); k=KNOWN.get(path.name)
    if k: return {'file':path.name,'size':len(data),**k,'rows':int.from_bytes(data[:2],'little')}
    n=int.from_bytes(data[:2],'little'); return {'file':path.name,'size':len(data),'rows_guess':n}

def patch_scalar(buf, off, typ, value):
    fmt={'u8':'<B','s8':'<b','u16':'<H','s16':'<h','u32':'<I','s32':'<i','f32':'<f'}[typ]
    struct.pack_into(fmt, buf, off, value)

def clone(data: bytes, filename: str, spec: dict) -> bytes:
    meta=KNOWN[filename]; header=meta['header']; stride=int(spec.get('row_size',meta['row_size']))
    count=int.from_bytes(data[:2],'little')
    out=bytearray(data)
    for add in spec.get('clone_rows', spec.get('add', [])):
        base_index=int(add.get('base_index', count-1))
        row=bytearray(out[header+base_index*stride:header+(base_index+1)*stride])
        for edit in add.get('set',[]): patch_scalar(row,int(edit['offset']),edit.get('type','u16'),edit['value'])
        out.extend(row); count+=1
    out[:2]=count.to_bytes(2,'little')
    return bytes(out)

def main(argv=None):
    p=argparse.ArgumentParser(description='MHST1 battleparm fixed-row patcher')
    sub=p.add_subparsers(required=True)
    s=sub.add_parser('info'); s.add_argument('files',nargs='+'); s.set_defaults(func=lambda a: print(json.dumps([info(Path(x)) for x in a.files],indent=2)))
    def run_clone(a): Path(a.output).write_bytes(clone(Path(a.input).read_bytes(), Path(a.input).name, json.loads(Path(a.patch).read_text())))
    s=sub.add_parser('clone'); s.add_argument('input'); s.add_argument('patch'); s.add_argument('output'); s.set_defaults(func=run_clone)
    a=p.parse_args(argv); a.func(a); return 0
if __name__=='__main__': raise SystemExit(main())
