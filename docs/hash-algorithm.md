# Rockchip LOADER header hash algorithm (RK3326)

The `uboot.img` / `trust.img` produced by Rockchip's `loaderimage` tool is a
**LOADER container**. On this device the file holds **two identical copies** of
the container, `0x200000` bytes apart.

## Container layout (per copy)

| offset | size | field |
|---|---|---|
| `0x00` | 8 | magic `"LOADER  "` (two trailing spaces) |
| `0x08` | 8 | version (0 here) |
| `0x10` | 4 | `loader_load_addr` (LE32) = `0x00200000` |
| `0x14` | 4 | `loader_load_size` (LE32) = `0x000fe1c8` |
| `0x18` | 4 | `crc32` (LE32) |
| `0x1c` | 4 | `hash_len` (LE32) = `0x20` (SHA-256) |
| `0x20` | 32 | `sha256` |
| … | | (js_hash, rsaHash — unused for verification here) |
| `0x800` | `load_size` | **payload** (the actual U-Boot image) |

## CRC32 (`+0x18`)

`crc32_rk(0, payload, load_size)` using Rockchip's **custom** 256-entry table
(see [`../tools/crc32_rk.c`](../tools/crc32_rk.c)). Core step:

```
DO_CRC(x):  crc = table[((crc >> 24) ^ x) & 0xff] ^ ((crc << 8) & 0xffffffff)
```
Initial `crc = 0`. This is **not** standard zlib CRC-32 — different polynomial/table.

## SHA-256 (`+0x20`)

From Rockchip's `loaderimage.c` (`CONFIG_SECUREBOOT_SHA256` path):

```
sha256_starts()
sha256_update(payload, load_size)
if version > 0:                       # version == 0 here, so SKIPPED
    sha256_update(&version, 8)
sha256_update(&loader_load_addr, 4)   # LE32
sha256_update(&loader_load_size, 4)   # LE32
sha256_update(&hash_len, 4)           # LE32
sha256_finish()
```

i.e. the digest covers the payload **plus three little-endian header words**
(`load_addr`, `load_size`, `hash_len`), not just the payload.

## Verification

Running the recompute on the **stock** image reproduces the stock values
bit-for-bit (sanity check built into `build_uboot_rooted.py`):

```
crc = 0x45acb94e        # stock uboot.img, both copies
```

Both the custom CRC table and the SHA field order were confirmed against
Rockchip's published `crc32_rk.c` and `loaderimage.c` (mirrored in `tools/` for
reference), and empirically: the SPL accepts the rebuilt image and boots.
