# AVB unlock patch — `read_is_device_unlocked()`

Firmware: `DK_Tab7_WiFi_NEU_2.4G_RK3326_12_ID3772_20231220_V1.0` (Blackview Tab 7 WiFi, RK3326).
Component: `uboot.img` (Rockchip LOADER container, two copies, stride `0x200000`, payload at `+0x800`, load address `0x00200000`).

## The function

`read_is_device_unlocked()` lives at virtual address **`0x22378c`**. Simplified:

```
read_is_device_unlocked(ops, out1, out2):
    unlocked = 1                      ; strb w0(=1),[x29,#0x67]   <-- default: UNLOCKED
    ops2 = get_ops()
    if ops2 == 0: return 1
    cb = ops2->fn[0x48]               ; Trusty/TEE "read lock state" callback
    cb(&unlocked)                     ; blr x2  @0x22381c  <-- OVERWRITES unlocked with the REAL (locked) value
    if unlocked bit0 set: ...orange/allow... else ...green/enforce...
```

The return value of this function drives **both** the reported boot state
(`androidboot.verifiedbootstate` orange vs green, `ro.boot.flash.locked`) **and**
whether `avb_slot_verify` runs with `ALLOW_VERIFICATION_ERROR` (i.e. whether a
modified boot image is allowed to boot).

> A naive patch of the lower-level `rk_avb_read_lock_state()` (vaddr `0x229c78`)
> has **no effect**: it reads Trusty and its value is overwritten/ignored on the
> boot-state path. `read_is_device_unlocked()` is the correct lever.

## The patch

Neutralise the Trusty callback so the flag keeps its initial value `1` (unlocked):

| | vaddr | file offset (copy A) | file offset (copy B) | bytes |
|---|---|---|---|---|
| stock | `0x22381c` | `0x2401c` | `0x22401c` | `40 00 3f d6` — `blr x2` |
| patched | `0x22381c` | `0x2401c` | `0x22401c` | `00 00 80 52` — `mov w0,#0` |

File offset = `copy_base + 0x800 + (vaddr − 0x200000)`, with `copy_base` ∈ {`0x0`, `0x200000`}.

After patching, the LOADER header hashes (`crc32` @`+0x18`, `sha256` @`+0x20`) must be
recomputed for **each** copy — see [`../tools/build_uboot_rooted.py`](../tools/build_uboot_rooted.py)
and [`../docs/hash-algorithm.md`](../docs/hash-algorithm.md). The provided script does all of this
and auto-verifies. Secure Boot is **not** fused on this device, so a correct hash is sufficient
for the SPL to accept the modified U-Boot (hash-not-signature; fully recoverable via MaskROM).

## Result (verified on device)

```
ro.boot.flash.locked      : 1 -> 0
ro.boot.verifiedbootstate : green -> orange
```
Android boots; a Magisk-patched boot image then boots too → root.

## Porting to another RK3326 build

The offset `0x22381c` is specific to this exact U-Boot build. On another build:
1. Extract the U-Boot payload: `uboot.img[0x800 : 0x800+load_size]` (load_size is LE32 at `+0x14`).
2. Find the string `androidboot.verifiedbootstate=orange` and
   `read_is_device_unlocked() ops returned that device is %s`; follow the xrefs to the function.
3. Locate the single indirect call (`blr x2`) that fills the local "unlocked" byte from a
   Trusty/TEE op, and replace it with `mov w0,#0` (keeps the initialised value `1`).
4. Recompute the LOADER hashes.
