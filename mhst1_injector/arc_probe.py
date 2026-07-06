from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


def probe_file(path: Path) -> dict:
    data = path.read_bytes()[:256]
    magic = data[:4]
    out = {
        "path": str(path),
        "size": path.stat().st_size,
        "magic_ascii": magic.decode("ascii", errors="replace"),
        "magic_hex": magic.hex(),
        "notes": [],
    }

    if magic == b"ARC\x00":
        out["container_guess"] = "MT Framework ARC (unencrypted or plain variant)"
    elif magic == b"ARCC":
        out["container_guess"] = "MT Framework ARCC (encrypted/compressed ARC variant)"
        out["notes"].append("Known from MT Mobile/Ace Attorney/Kuriimu discussions as encrypted Capcom ARC variant.")
    elif magic.startswith(b"ARC"):
        out["container_guess"] = "ARC-like container"
    else:
        out["container_guess"] = "unknown"

    # Try common little/big-endian header words after magic. This is diagnostic only.
    if len(data) >= 16:
        out["u32_le_04"] = struct.unpack_from("<I", data, 4)[0]
        out["u32_le_08"] = struct.unpack_from("<I", data, 8)[0]
        out["u32_le_0c"] = struct.unpack_from("<I", data, 12)[0]
        out["u32_be_04"] = struct.unpack_from(">I", data, 4)[0]
        out["u32_be_08"] = struct.unpack_from(">I", data, 8)[0]
        out["u32_be_0c"] = struct.unpack_from(">I", data, 12)[0]

    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Probe suspected MHST1/MT Mobile container files")
    p.add_argument("paths", nargs="+", help="Files to inspect")
    args = p.parse_args(argv)
    print(json.dumps([probe_file(Path(x)) for x in args.paths], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
