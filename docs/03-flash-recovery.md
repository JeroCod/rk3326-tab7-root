# 3 — Flashing & recovery reference

## USB modes seen on this device

| Mode | USB ID | Reached by | Tool |
|---|---|---|---|
| Android / adb | — | normal boot | `adb` |
| Rockchip Loader | `0x2207:0x330d` | `adb reboot loader` | `rkdeveloptool` |
| MaskROM | `0x2207:0x330d` | `rkdeveloptool rd 3` (or Loader fallback) | `rkdeveloptool` |
| Fastboot (Rockchip) | `0x18d1` | recovery → *Reboot to bootloader* | `fastboot` (flash only) |

`adb reboot loader` reaches the low-level channel **without any hardware test
point**. Always wait ≥10 s after it before issuing `rkdeveloptool` commands.

## rkdeveloptool cheatsheet

```
rkdeveloptool ld                       # list devices / confirm mode
rkdeveloptool wl <LBA> <image>         # write image at sector LBA
rkdeveloptool rl <LBA> <sectors> out   # read back (verify)
rkdeveloptool rd                        # reboot (normal)
rkdeveloptool rd 3                       # reboot to MaskROM
rkdeveloptool db MiniLoaderAll.bin       # download bootloader (pure MaskROM)
```

Key LBAs: `uboot_a 0x4000`, `uboot_b 0x6000`, `boot_a 0x13000`, `boot_b 0x4f000`.

## Restore to 100% stock

In Loader mode, rewrite the stock images at their LBAs:
```
rkdeveloptool wl 0x4000  uboot-stock.img
rkdeveloptool wl 0x6000  uboot-stock.img
rkdeveloptool wl 0x13000 boot-stock.img      # from your stock firmware
rkdeveloptool wl 0x4f000 boot-stock.img
rkdeveloptool rd
```
If it drops back into fastboot after bootloops: `fastboot set_active a`.

Full stock firmware reflash is in [01-unbrick.md](01-unbrick.md).

## Safety notes

- Secure Boot is **not** fused on the tested unit → modified U-Boot with correct
  hashes is accepted, and a bad one simply drops to MaskROM (recoverable). This is
  a *hash* check, not a *signature* check.
- These procedures are destructive to the targeted partitions. Have the stock
  firmware on hand before you start. Back up your own `boot.img`/`uboot.img` first.
