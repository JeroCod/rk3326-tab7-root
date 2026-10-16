#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_synthetic_uboot.py — build a tiny, fake RK3326 LOADER image that mimics the
real uboot.img layout closely enough to exercise tools/build_uboot_rooted.py in
CI, WITHOUT redistributing any copyrighted Rockchip/Blackview firmware.

The synthetic image:
  * has the real two-copy layout (stride 0x200000),
  * carries a "blr x2" (40003fd6) at the real patch vaddr 0x22381c,
  * has self-consistent crc32_rk/sha256 headers, computed with the SAME recipe
    the build script uses — so the build script's "reproduces stock hashes"
    sanity gate passes and the full patch + recompute + verify path runs.

It validates the plumbing (offsets, copy iteration, header math, round-trip),
not the crc table against genuine Rockchip output (that was verified once against
the real stock image, 0x45acb94e, on the author's unit).

Usage: python3 tests/make_synthetic_uboot.py <out.img>
"""
import sys, os, struct, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import build_uboot_rooted as b  # reuse crc32_rk / constants

STRIDE   = b.STRIDE              # 0x200000
PAYLOAD  = b.PAYLOAD             # 0x800
LOAD     = b.LOAD_BASE           # 0x200000
HLEN     = 0x20
SIZE     = 0x30000               # must be > (patch_va - load) so the patch is hashed
PATCH_OFF = PAYLOAD + (b.PATCH_VA - LOAD)   # = 0x2401c within a copy


def make_copy() -> bytes:
    copy = bytearray(STRIDE)
    copy[0:8] = b"LOADER  "
    # deterministic, non-trivial payload
    payload = bytearray((i * 37 + 11) & 0xFF for i in range(SIZE))
    # plant the real instruction we expect to patch
    payload[PATCH_OFF - PAYLOAD: PATCH_OFF - PAYLOAD + 4] = b.STOCK_INS
    copy[PAYLOAD:PAYLOAD + SIZE] = payload
    struct.pack_into("<I", copy, 0x10, LOAD)
    struct.pack_into("<I", copy, 0x14, SIZE)
    struct.pack_into("<I", copy, 0x1c, HLEN)
    # self-consistent hashes via the build script's own recipe
    crc, sha, *_ = b.calc_hashes(bytes(copy))
    struct.pack_into("<I", copy, 0x18, crc)
    copy[0x20:0x20 + HLEN] = sha[:HLEN]
    return bytes(copy)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    img = make_copy() * 2  # two identical copies, like the real container
    open(sys.argv[1], "wb").write(img)
    print(f"wrote synthetic {sys.argv[1]} ({len(img)} bytes, 2 copies, "
          f"blr x2 @copy+0x{PATCH_OFF:x})")


if __name__ == "__main__":
    main()
