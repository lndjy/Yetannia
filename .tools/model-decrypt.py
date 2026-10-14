# model-decrypt.py — undo the single-byte XOR on 《千年之旅》 model bundles and parse their header.
#
# The model .data files are not plain UnityFS like the voice .dat files. Their first seven bytes XOR
# with "UnityFS" all give 0x7b, i.e. a single-byte XOR key. This parses the result field by field and
# compares it against a voice bundle that UnityPy reads without complaint, so a misalignment shows up
# as a named field rather than as a byte-offset mystery.
#
# usage: python .tools/model-decrypt.py <model.data> <known-good.dat>
import struct
import sys


def read_cstr(buf, off):
    end = buf.index(b"\x00", off)
    return buf[off:end].decode("utf-8", "replace"), end + 1


def parse_header(buf, label):
    print(f"--- {label}  ({len(buf)} bytes) ---")
    sig = buf[:8]
    print(f"  signature        = {sig!r}")
    if sig[:7] != b"UnityFS":
        print("  !! not a UnityFS bundle")
        return None
    off = 8
    version = struct.unpack_from("<I", buf, off)[0]
    off += 4
    unity_ver, off = read_cstr(buf, off)
    unity_rev, off = read_cstr(buf, off)
    size = struct.unpack_from("<q", buf, off)[0]
    off += 8
    cbis = struct.unpack_from("<I", buf, off)[0]
    off += 4
    ubis = struct.unpack_from("<I", buf, off)[0]
    off += 4
    flags = struct.unpack_from("<I", buf, off)[0]
    off += 4
    print(f"  version          = {version}")
    print(f"  unity_version    = {unity_ver!r}")
    print(f"  unity_revision   = {unity_rev!r}")
    print(f"  size             = {size}   (file has {len(buf)})")
    print(f"  blocksInfo csize = {cbis}")
    print(f"  blocksInfo usize = {ubis}")
    print(f"  flags            = 0x{flags:x}   (compression = {flags & 0x3f}, dirInfoAtEnd = {bool(flags & 0x80)}, "
          f"blocksInfoAtEnd = {bool(flags & 0x200)})")
    print(f"  header ends at   = {off}")
    print(f"  first 16 data bytes = {buf[off:off + 16].hex(' ')}")
    return dict(version=version, size=size, cbis=cbis, ubis=ubis, flags=flags, data_off=off)


def show_tail(buf, label):
    print(f"  last 32 bytes    = {buf[-32:].hex(' ')}")
    printable = "".join(chr(b) if 32 <= b < 127 else "." for b in buf[-64:])
    print(f"  last 64 ascii    = {printable!r}")


model_path, good_path = sys.argv[1], sys.argv[2]

raw_model = open(model_path, "rb").read()
dec = bytes(b ^ 0x7B for b in raw_model)

m = parse_header(dec, f"MODEL xor 0x7b: {model_path.split(chr(92))[-1]}")
if m:
    show_tail(dec, "model")

g = parse_header(open(good_path, "rb").read(), f"KNOWN-GOOD: {good_path.split(chr(92))[-1]}")
if g:
    show_tail(open(good_path, "rb").read(), "good")

# Try the loader on both, so a failure is attributable to one of them rather than to the file name.
import UnityPy  # noqa: E402

for label, buf in (("model(xor)", dec), ("good(plain)", open(good_path, "rb").read())):
    tmp = f"C:/temp/art/_probe_{label.split('(')[0]}.unity3d"
    import os
    os.makedirs("C:/temp/art", exist_ok=True)
    open(tmp, "wb").write(buf)
    try:
        env = UnityPy.load(tmp)
        kinds = {}
        for o in env.objects:
            kinds[o.type.name] = kinds.get(o.type.name, 0) + 1
        print(f"{label}: OK, {len(env.objects)} objects -> {kinds}")
    except Exception as exc:  # noqa: BLE001
        print(f"{label}: FAILED {type(exc).__name__}: {exc}")
