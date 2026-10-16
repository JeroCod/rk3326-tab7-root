#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest.py — end-to-end check of tools/build_uboot_rooted.py on a synthetic
LOADER image (no copyrighted firmware needed). Exits non-zero on any failure.
"""
import os, sys, subprocess, tempfile

HERE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.join(HERE, "..")
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import build_uboot_rooted as b

PATCH_OFF = b.PAYLOAD + (b.PATCH_VA - b.LOAD_BASE)


def run(cmd):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r


def main():
    with tempfile.TemporaryDirectory() as d:
        stock  = os.path.join(d, "stock.img")
        rooted = os.path.join(d, "rooted.img")

        assert run([sys.executable, os.path.join(HERE, "make_synthetic_uboot.py"), stock]).returncode == 0

        r = run([sys.executable, os.path.join(TOOLS, "build_uboot_rooted.py"), stock, rooted])
        assert r.returncode == 0, "build script failed"

        data = open(rooted, "rb").read()
        assert len(data) == len(open(stock, "rb").read()), "size changed"

        # every copy must now carry mov w0,#0 and valid self-consistent hashes
        import struct, hashlib
        copies = [i * b.STRIDE for i in range(len(data) // b.STRIDE)]
        assert copies, "no copies found"
        for base in copies:
            copy = data[base:base + b.STRIDE]
            ins = copy[PATCH_OFF:PATCH_OFF + 4]
            assert ins == b.NEW_INS, f"@0x{base:x}: patch missing, got {ins.hex()}"
            crc, sha, _, _, hlen = b.calc_hashes(copy)
            assert crc == struct.unpack_from("<I", copy, 0x18)[0], f"@0x{base:x}: crc mismatch"
            assert sha[:hlen] == copy[0x20:0x20 + hlen], f"@0x{base:x}: sha mismatch"

        print(f"OK — {len(copies)} copies patched (blr x2 -> mov w0,#0), hashes consistent")


if __name__ == "__main__":
    main()
