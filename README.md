# Blackview Tab 7 WiFi (RK3326) — bootloader AVB unlock & root

Root for the **Blackview Tab 7 WiFi** (Rockchip **RK3326**, Android 12), a device
whose bootloader ships **no working unlock** (`fastboot oem unlock` =
*not implemented*, `fastboot flashing unlock` = stub). Root is achieved by
patching U-Boot so the Android Verified Boot (AVB) state reads **unlocked**, which
lets a Magisk-patched boot image run.

> ⚠️ GSMArena lists this tablet as Unisoc T310 — **wrong** for this revision. The
> firmware name and serial confirm **RK3326**. Verify your SoC by the firmware
> name, not spec sheets.

> **This flashes your bootloader. It can brick (though this method is
> MaskROM-recoverable on the tested unit). You do it at your own risk.** Have the
> stock firmware ready before you start. Tested on firmware
> `DK_Tab7_WiFi_NEU_2.4G_RK3326_12_ID3772_20231220_V1.0` only.

## TL;DR

1. **U-Boot**: `read_is_device_unlocked()` defaults its "unlocked" flag to `1`, then
   a Trusty callback overwrites it with the real (locked) value. We replace that
   one `blr x2` (@vaddr `0x22381c`) with `mov w0,#0` → the flag stays `1` =
   **unlocked**. That return value drives both the boot state and AVB's
   allow-verification-error.
2. The `uboot.img` is a Rockchip **LOADER** container (two copies) with a custom
   `crc32`+`sha256` header. We recompute those so the SPL accepts the patch
   (**Secure Boot is not fused** on this unit — it's a hash check, recoverable).
3. Flash the patched U-Boot via `rkdeveloptool` (MaskROM/Loader reachable with
   **no hardware test point**), confirm `verifiedbootstate=orange`, then flash a
   Magisk-patched boot → **root** (`su -c id` → `uid=0`).

Full write-up:
- [patches/read_is_device_unlocked.md](patches/read_is_device_unlocked.md) — the exact patch (offsets + bytes)
- [docs/hash-algorithm.md](docs/hash-algorithm.md) — the LOADER crc32/sha256 recipe
- [docs/01-unbrick.md](docs/01-unbrick.md) — restore stock from a bootloop
- [docs/02-root-avb-unlock.md](docs/02-root-avb-unlock.md) — the root procedure
- [docs/03-flash-recovery.md](docs/03-flash-recovery.md) — flashing & recovery reference
- [tools/build_uboot_rooted.py](tools/build_uboot_rooted.py) — patches + recomputes hashes + auto-verifies

## Build the unlocked U-Boot

```
python3 tools/build_uboot_rooted.py uboot-stock.img uboot-rooted.img
```
It first proves the hash recipe reproduces the stock values, then patches and
recomputes both copies, with an auto-verify pass.

## Stock firmware

This repo does **not** redistribute the full stock ROM (it's Blackview's
copyrighted firmware, and `super.img` alone is ~3.9 GB). Obtain
`DK_Tab7_WiFi_NEU_2.4G_RK3326_12_ID3772_20231220_V1.0` from **Blackview support**
(support@blackview.hk / the official Blackview firmware channel), then unpack the
RKFW `update.img` with [afptool-rs](https://github.com/vicalloy/afptool-rs).

## Release assets (small, convenience only)

The GitHub **Release** carries the small key images so you can un-brick or patch
without unpacking the whole ROM: `uboot-stock.img`, `uboot-rooted.img`,
`dtbo.img`, `vbmeta.img`, `MiniLoaderAll.bin`, `parameter.txt`. SHA-256 sums are
listed in the release notes. The large `super.img` and any Magisk-patched boot are
**not** provided — patch your own `boot.img` with the Magisk app (see docs/02).

## Status

Verified working on one unit (S/N `TABWIFINEU…`): `flash.locked 1→0`,
`verifiedbootstate green→orange`, Magisk 30.7 `su -c id → uid=0(root)`, busybox
module installed. Reports from other Tab 7 WiFi units welcome via Issues.

## Credits

- Method inspired by the "patch U-Boot to report unlocked" approach seen in the
  RK35xx scene (e.g. thewickedlabs / bootlicker).
- Rockchip `crc32_rk.c` / `loaderimage.c` for the LOADER hash format.
- [rkdeveloptool](https://github.com/rockchip-linux/rkdeveloptool),
  [afptool-rs](https://github.com/vicalloy/afptool-rs),
  [Magisk](https://github.com/topjohnwu/Magisk) by topjohnwu.

## License

Documentation under [CC BY 4.0](LICENSE); the scripts under `tools/` (except the
upstream Rockchip `.c` references) under the MIT terms noted in that file. The
stock Rockchip/Blackview binaries are **not** covered and remain their owners'.
