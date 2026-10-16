#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_uboot_rooted.py — patch a Rockchip RK3326 uboot.img to force the AVB
device-lock state to "unlocked", and recompute the LOADER header hashes so the
SPL accepts the modified image.

Target: Blackview Tab 7 WiFi (RK3326, Android 12), firmware
        DK_Tab7_WiFi_NEU_2.4G_RK3326_12_ID3772_20231220_V1.0.
        The patch offset is specific to THIS U-Boot build. On another build you
        must relocate read_is_device_unlocked() yourself (see docs/).

What it does
------------
U-Boot's read_is_device_unlocked() initialises a local "unlocked" flag to 1,
then a Trusty/TEE callback (an indirect `blr x2`) overwrites it with the real
(locked) value. We replace that single `blr x2` with `mov w0,#0`: the callback
is skipped, the flag keeps its initial value 1 => device reports UNLOCKED. That
return value drives both the boot state (orange vs green) AND whether AVB allows
a modified boot image (ALLOW_VERIFICATION_ERROR).

The uboot.img is a Rockchip LOADER container holding two identical copies
(stride 0x200000). Each copy has an 8-byte "LOADER  " magic, then at:
  0x10 load_addr (LE32)   0x14 load_size (LE32)
  0x18 crc32 (LE32)       0x1c hash_len (LE32)   0x20 sha256 (32 bytes)
Payload starts at file offset 0x800 inside each copy. Secure Boot is NOT fused
on this device, so a correct hash is enough for the SPL to accept the image.

Hash recipe (verified: reproduces the stock crc/sha bit-for-bit)
  crc32  = crc32_rk(0, payload[:size])          # custom table, see crc32_rk.c
  sha256 = sha256( payload[:size]
                   + load_addr(LE32) + load_size(LE32) + hash_len(LE32) )
           (the 8-byte version field is included ONLY if version>0; it is 0 here)

Usage
-----
  python3 build_uboot_rooted.py <uboot-stock.img> <uboot-rooted.img>

Requires: pip install capstone   (only used for an optional sanity disassembly;
the patch itself is a plain byte replacement and needs nothing extra).
"""
import sys, struct, hashlib

# --- crc32_rk table (from Rockchip crc32_rk.c; tole() = value stored as-is LE) ---
CRC_TABLE_HEX = """
00000000 04c10db7 09821b6e 0d4316d9 130436dc 17c53b6b 1a862db2 1e472005
26086db8 22c9600f 2f8a76d6 2b4b7b61 350c5b64 31cd56d3 3c8e400a 384f4dbd
4c10db70 48d1d6c7 4592c01e 4153cda9 5f14edac 5bd5e01b 5696f6c2 5257fb75
6a18b6c8 6ed9bb7f 639aada6 675ba011 791c8014 7ddd8da3 709e9b7a 745f96cd
9821b6e0 9ce0bb57 91a3ad8e 9562a039 8b25803c 8fe48d8b 82a79b52 866696e5
be29db58 bae8d6ef b7abc036 b36acd81 ad2ded84 a9ece033 a4aff6ea a06efb5d
d4316d90 d0f06027 ddb376fe d9727b49 c7355b4c c3f456fb ceb74022 ca764d95
f2390028 f6f80d9f fbbb1b46 ff7a16f1 e13d36f4 e5fc3b43 e8bf2d9a ec7e202d
34826077 30436dc0 3d007b19 39c176ae 278656ab 23475b1c 2e044dc5 2ac54072
128a0dcf 164b0078 1b0816a1 1fc91b16 018e3b13 054f36a4 080c207d 0ccd2dca
7892bb07 7c53b6b0 7110a069 75d1adde 6b968ddb 6f57806c 621496b5 66d59b02
5e9ad6bf 5a5bdb08 5718cdd1 53d9c066 4d9ee063 495fedd4 441cfb0d 40ddf6ba
aca3d697 a862db20 a521cdf9 a1e0c04e bfa7e04b bb66edfc b625fb25 b2e4f692
8aabbb2f 8e6ab698 8329a041 87e8adf6 99af8df3 9d6e8044 902d969d 94ec9b2a
e0b30de7 e4720050 e9311689 edf01b3e f3b73b3b f776368c fa352055 fef42de2
c6bb605f c27a6de8 cf397b31 cbf87686 d5bf5683 d17e5b34 dc3d4ded d8fc405a
6904c0ee 6dc5cd59 6086db80 6447d637 7a00f632 7ec1fb85 7382ed5c 7743e0eb
4f0cad56 4bcda0e1 468eb638 424fbb8f 5c089b8a 58c9963d 558a80e4 514b8d53
25141b9e 21d51629 2c9600f0 28570d47 36102d42 32d120f5 3f92362c 3b533b9b
031c7626 07dd7b91 0a9e6d48 0e5f60ff 101840fa 14d94d4d 199a5b94 1d5b5623
f125760e f5e47bb9 f8a76d60 fc6660d7 e22140d2 e6e04d65 eba35bbc ef62560b
d72d1bb6 d3ec1601 deaf00d8 da6e0d6f c4292d6a c0e820dd cdab3604 c96a3bb3
bd35ad7e b9f4a0c9 b4b7b610 b076bba7 ae319ba2 aaf09615 a7b380cc a3728d7b
9b3dc0c6 9ffccd71 92bfdba8 967ed61f 8839f61a 8cf8fbad 81bbed74 857ae0c3
5d86a099 5947ad2e 5404bbf7 50c5b640 4e829645 4a439bf2 47008d2b 43c1809c
7b8ecd21 7f4fc096 720cd64f 76cddbf8 688afbfd 6c4bf64a 6108e093 65c9ed24
11967be9 1557765e 18146087 1cd56d30 02924d35 06534082 0b10565b 0fd15bec
379e1651 335f1be6 3e1c0d3f 3add0088 249a208d 205b2d3a 2d183be3 29d93654
c5a71679 c1661bce cc250d17 c8e400a0 d6a320a5 d2622d12 df213bcb dbe0367c
e3af7bc1 e76e7676 ea2d60af eeec6d18 f0ab4d1d f46a40aa f9295673 fde85bc4
89b7cd09 8d76c0be 8035d667 84f4dbd0 9ab3fbd5 9e72f662 9331e0bb 97f0ed0c
afbfa0b1 ab7ead06 a63dbbdf a2fcb668 bcbb966d b87a9bda b5398d03 b1f880b4
"""
TAB = [int(x, 16) for x in CRC_TABLE_HEX.split()]
assert len(TAB) == 256

# --- patch site (RK3326, this firmware): read_is_device_unlocked() Trusty callback
PATCH_VA   = 0x22381c            # vaddr of the `blr x2`
LOAD_BASE  = 0x200000            # U-Boot load address (payload maps here)
PAYLOAD    = 0x800               # payload offset inside each LOADER copy
STRIDE     = 0x200000            # distance between the two LOADER copies
STOCK_INS  = bytes.fromhex("40003fd6")   # blr x2
NEW_INS    = bytes.fromhex("00008052")   # mov w0,#0


def crc32_rk(data: bytes) -> int:
    crc = 0
    for b in data:
        crc = (TAB[((crc >> 24) ^ b) & 255] ^ ((crc << 8) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return crc


def calc_hashes(copy: bytes):
    load = struct.unpack_from("<I", copy, 0x10)[0]
    size = struct.unpack_from("<I", copy, 0x14)[0]
    hlen = struct.unpack_from("<I", copy, 0x1c)[0]
    payload = copy[PAYLOAD:PAYLOAD + size]
    crc = crc32_rk(payload)
    h = hashlib.sha256()
    h.update(payload)
    h.update(struct.pack("<I", load))
    h.update(struct.pack("<I", size))
    h.update(struct.pack("<I", hlen))
    return crc, h.digest(), load, size, hlen


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src = open(sys.argv[1], "rb").read()
    if len(src) % STRIDE != 0:
        sys.exit(f"unexpected size {len(src)} (not a multiple of 0x{STRIDE:x})")
    copies = [i * STRIDE for i in range(len(src) // STRIDE)]

    # 1) sanity: our algo must reproduce the STOCK crc/sha on every copy
    for base in copies:
        copy = src[base:base + STRIDE]
        crc, sha, load, size, hlen = calc_hashes(copy)
        scrc = struct.unpack_from("<I", copy, 0x18)[0]
        ssha = copy[0x20:0x40]
        ok = crc == scrc and sha[:hlen] == ssha[:hlen]
        print(f"[stock @0x{base:x}] load=0x{load:x} size=0x{size:x} "
              f"crc=0x{crc:08x}(stock 0x{scrc:08x}) sha_ok={sha[:hlen]==ssha[:hlen]} "
              f"-> {'OK' if ok else 'MISMATCH'}")
        if not ok:
            sys.exit("algo does not reproduce stock hashes — wrong firmware/offsets, aborting")

    # 2) patch + recompute on every copy
    out = bytearray(src)
    for base in copies:
        foff = base + PAYLOAD + (PATCH_VA - LOAD_BASE)
        cur = bytes(out[foff:foff + 4])
        if cur != STOCK_INS:
            sys.exit(f"@0x{foff:x}: expected {STOCK_INS.hex()} (blr x2), found {cur.hex()} — aborting")
        out[foff:foff + 4] = NEW_INS
        copy = bytes(out[base:base + STRIDE])
        crc, sha, load, size, hlen = calc_hashes(copy)
        struct.pack_into("<I", out, base + 0x18, crc)
        out[base + 0x20:base + 0x20 + hlen] = sha[:hlen]
        print(f"[patch @0x{base:x}] blr x2 -> mov w0,#0, new crc=0x{crc:08x} sha={sha[:8].hex()}...")

    # 3) auto-verify
    final = bytes(out)
    for base in copies:
        copy = final[base:base + STRIDE]
        crc, sha, load, size, hlen = calc_hashes(copy)
        scrc = struct.unpack_from("<I", copy, 0x18)[0]
        ssha = copy[0x20:0x40]
        foff = base + PAYLOAD + (PATCH_VA - LOAD_BASE)
        patched = bytes(copy[foff - base:foff - base + 4]) == NEW_INS
        ok = patched and crc == scrc and sha[:hlen] == ssha[:hlen]
        print(f"[verify @0x{base:x}] patched={patched} crc_ok={crc==scrc} "
              f"sha_ok={sha[:hlen]==ssha[:hlen]} -> {'OK' if ok else 'FAIL'}")
        if not ok:
            sys.exit("verification failed")

    open(sys.argv[2], "wb").write(final)
    print(f"written {sys.argv[2]} ({len(final)} bytes)")


if __name__ == "__main__":
    main()
