# 1 — Un-brick (restore stock from a bootloop)

If the tablet is stuck on the Blackview logo / bootloops (e.g. after a bad flash
or a failed update), reflash the stock firmware. This is also the full recovery
path if anything in the root procedure goes wrong.

## You need

- The **official stock firmware** `DK_Tab7_WiFi_NEU_2.4G_RK3326_12_ID3772_20231220_V1.0`
  (an `update.img` in RKFW format). Get it from Blackview support — see the main README.
- A tool to unpack RKFW into individual partition images, e.g.
  [`afptool-rs`](https://github.com/vicalloy/afptool-rs) (`afptool-rs unpack update.img out/`).
  This yields `uboot.img`, `boot.img`, `super.img`, `dtbo.img`, `vbmeta.img`,
  `trust.img`, `misc.img`, `MiniLoaderAll.bin`, `parameter.txt`, …
- `fastboot` (Android platform-tools).

## Partition map (`parameter.txt`)

```
uboot_a  @LBA 0x04000   boot_a  @0x13000   dtbo_a   @0x0e000   vbmeta_a @0x12000
uboot_b  @0x06000       boot_b  @0x4f000   super    @0x20dc00  userdata @grow
```
(LBA = 512-byte sectors.)

## Fastboot reflash

1. Boot to recovery (power + Vol-Up), choose **Reboot to bootloader** → Rockchip
   fastboot (`0x18d1`). *Note: this fastboot is minimal — `flash` works, but
   `getvar`/`oem` largely don't.*
2. Flash each partition:
   ```
   fastboot flash uboot   uboot.img
   fastboot flash boot    boot.img
   fastboot flash dtbo    dtbo.img
   fastboot flash vbmeta  vbmeta.img
   fastboot flash super   super.img      # ~3.9 GB, auto-sparsed by fastboot, OK
   fastboot flash trust   trust.img
   fastboot flash misc    misc.img
   ```
3. **Critical:** force the active slot or the device reboots back into fastboot:
   ```
   fastboot set_active a
   fastboot reboot
   ```

> **Pitfall (A/B slots):** after repeated bootloops a slot can be marked
> unbootable. Whenever a reboot drops back into fastboot, run
> `fastboot set_active a` before concluding anything failed.
