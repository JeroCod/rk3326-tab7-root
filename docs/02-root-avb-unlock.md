# 2 — Root via U-Boot AVB unlock + Magisk

## Why the usual routes don't work on this device

- `fastboot oem unlock` → *not implemented*.
- `fastboot flashing unlock` → a **stub**: it returns OKAY but never flips the
  lock state. `ro.boot.flash.locked` stays `1` (green). So the bootloader has no
  real unlock, and a locked AVB **rejects any modified boot** → bootloop.
- Re-signing a patched boot (avbroot-style) is impossible: the vbmeta is signed
  with Blackview's **private** AVB key (public-key SHA1
  `38212ebae4021ba401b251176ffb4eee7994dd90`, not the AOSP test keys).
- `apply update from ADB` (recovery sideload) hits the same wall — AVB verifies
  at **boot**, not at write time.

The way through is to make **U-Boot itself report the device as unlocked**, which
flips AVB into "allow verification error" mode so a modified boot can boot.
Secure Boot is **not** fused on this unit, so a U-Boot with correctly recomputed
LOADER hashes is accepted by the SPL. Everything here is recoverable via MaskROM.

## Tools

- [`rkdeveloptool`](https://github.com/rockchip-linux/rkdeveloptool) (build from source).
- `adb`, `fastboot`.
- Python 3 (+ `capstone` only if you want to re-derive offsets).

## The low-level channel — no hardware test point needed

```
adb reboot loader          # -> Rockchip Loader/MaskROM mode, USB 0x2207:0x330d
# WAIT >= 10 seconds before the next command (6 s is too short: writes silently
# fail with "Did not find any rockusb device" and nothing is written — harmless)
rkdeveloptool ld           # should list a "Loader" device
```

## Step A — build and flash the unlocked U-Boot

```
# build (from YOUR legally-obtained stock uboot.img)
python3 tools/build_uboot_rooted.py uboot-stock.img uboot-rooted.img

# flash both copies in Loader mode, at the uboot_a / uboot_b LBAs
rkdeveloptool wl 0x4000 uboot-rooted.img
rkdeveloptool wl 0x6000 uboot-rooted.img
rkdeveloptool rd                      # reboot
```

Wait ~35 s. If `adb` comes back and Android boots, the SPL accepted the image.
Verify:
```
adb shell getprop ro.boot.flash.locked        # expect 0
adb shell getprop ro.boot.verifiedbootstate   # expect orange
```
If instead it drops back into MaskROM, the SPL rejected the hash — recheck the
build (wrong firmware/offsets); restore stock (see docs/01) and stop.

> Keep the **stock boot image** at this stage. Because the stock boot is validly
> signed, it boots regardless of lock state — so this step is zero-risk for
> bricking: you are only changing U-Boot, which is fully MaskROM-recoverable.

## Step B — patch your own boot with Magisk, then flash it

1. Install the Magisk app (`com.topjohnwu.magisk`). In the app, **Install → Select
   and Patch a File**, pick your stock `boot.img`. It writes a patched
   `magisk_patched-*.img` (same 120 MB size on this device).
2. Flash it to both boot slots in Loader mode:
   ```
   rkdeveloptool wl 0x13000 magisk_patched.img
   rkdeveloptool wl 0x4f000 magisk_patched.img
   rkdeveloptool rd
   ```
3. On first boot, open the Magisk app and **grant** the superuser request when it
   appears on screen. Verify:
   ```
   adb shell su -c id          # uid=0(root) ... context=u:r:magisk:s0
   ```

Done — rooted, with `verifiedbootstate=orange`.

> Because AVB now only reports "orange" (verification-error allowed) rather than
> being truly unlocked, `ro.boot.vbmeta.device_state` may still read `locked`;
> that's expected and harmless — the `flash.locked=0` / orange state is what lets
> the modified boot run.
