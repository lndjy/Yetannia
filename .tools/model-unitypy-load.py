# model-unitypy-load.py — load the 0x7b-XORed bundle straight through UnityPy and list what is inside.
#
# usage: python .tools/model-unitypy-load.py <bundle.data> [more.data ...]
import os
import sys

import UnityPy

OUT = r"D:\桌面\sts2mod\.tools\out"


def xor(buf, key):
    return bytes(b ^ key for b in buf)


def main(paths):
    os.makedirs(OUT, exist_ok=True)
    for path in paths:
        raw = open(path, "rb").read()
        dec = xor(raw, 0x7B)
        assert dec[:7] == b"UnityFS"
        stem = os.path.splitext(os.path.basename(path))[0]
        tmp = os.path.join(OUT, stem + ".unity3d")
        open(tmp, "wb").write(dec)
        print(f"===== {os.path.basename(path)} -> {tmp}")
        try:
            env = UnityPy.load(tmp)
            kinds = {}
            for obj in env.objects:
                kinds[obj.type.name] = kinds.get(obj.type.name, 0) + 1
            print(f"  OK: {len(env.objects)} objects")
            for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
                print(f"    {k:28s} {v}")
            conts = list(getattr(env, "container", {}) or {})
            if conts:
                print("  container:")
                for c in conts:
                    print(f"    {c}")
        except Exception as exc:  # noqa: BLE001
            import traceback
            print(f"  FAILED {type(exc).__name__}: {exc}")
            traceback.print_exc(limit=6)


if __name__ == "__main__":
    main(sys.argv[1:])
