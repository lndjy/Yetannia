# model-unitypy-spy.py — wrap UnityPy's LZ4 entry point so we can see the exact bytes it passes.
#
# python .tools/model-lz4-trace.py proves lz4.block.decompress(buf[64:64+465], 913) works.
# UnityPy still fails, so it must be handing over a different slice/position. Print it.
#
# usage: python .tools/model-unitypy-spy.py <bundle.data>
import sys

import UnityPy
from UnityPy.helpers import CompressionHelper

print("[spy] DECOMPRESSION_MAP =", {k: v.__name__ for k, v in CompressionHelper.DECOMPRESSION_MAP.items()})

orig = CompressionHelper.decompress_lz4


def spy(data, uncompressed_size, *a, **kw):
    print(f"[spy] decompress_lz4: len(data)={len(data)} uncompressed_size={uncompressed_size}")
    print(f"[spy]   head = {data[:40].hex(' ')}")
    print(f"[spy]   tail = {data[-16:].hex(' ')}")
    try:
        out = orig(data, uncompressed_size, *a, **kw)
        print(f"[spy]   -> OK {len(out)} bytes; head={out[:32].hex(' ')}")
        return out
    except Exception as exc:
        print(f"[spy]   -> {type(exc).__name__}: {exc}")
        # Try to find a working window: maybe the slice is offset.
        import lz4.block
        for delta in range(-8, 9):
            if delta == 0:
                continue
            try:
                out = lz4.block.decompress(data[delta:], uncompressed_size=uncompressed_size)
                print(f"[spy]   !! data[{delta}:] DOES decompress ({len(out)} bytes)")
            except Exception:
                pass
        raise


CompressionHelper.decompress_lz4 = spy
for _k, _v in list(CompressionHelper.DECOMPRESSION_MAP.items()):
    if getattr(_v, "__name__", "") in ("decompress_lz4", "decompress_lz4hc", "decompress_lz4_hc"):
        CompressionHelper.DECOMPRESSION_MAP[_k] = spy
print("[spy] patched map ->", {k: v.__name__ for k, v in CompressionHelper.DECOMPRESSION_MAP.items()})

path = sys.argv[1]
raw = open(path, "rb").read()
dec = bytes(b ^ 0x7B for b in raw)
tmp = r"D:\桌面\sts2mod\.tools\out\spy.unity3d"
import os
os.makedirs(os.path.dirname(tmp), exist_ok=True)
open(tmp, "wb").write(dec)
try:
    env = UnityPy.load(tmp)
    print("loaded", len(env.objects), "objects")
except Exception as exc:
    print("load failed:", type(exc).__name__, exc)
