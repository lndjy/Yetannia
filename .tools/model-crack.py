# model-crack.py — recover the real plaintext bundle.
#
# FINDING: the 0x7b XOR covers only a PREFIX of the file, not the whole file.
#   * all 77 data blocks decode as PLAIN except block 0, which needs 0x7b for its first ~1000 bytes
#   * block 0 is fully valid for any prefix length N in [974, 1013) because the changed bytes are
#     LZ4 *literals*, whose values do not affect decodability -- only the decoded content.
# So: scan N, decrypt as raw[:N]^0x7b + raw[N:], and let UnityPy be the oracle for the right N.
#
# usage: python .tools/model-crack.py <bundle.data> [nlo nhi]
import os
import sys

import lz4.block
import UnityPy

OUT = r"D:\桌面\sts2mod\.tools\out"


def xor_prefix(raw, n):
    return bytes(b ^ 0x7B for b in raw[:n]) + raw[n:]


def main():
    path = sys.argv[1]
    nlo = int(sys.argv[2]) if len(sys.argv) > 2 else 900
    nhi = int(sys.argv[3]) if len(sys.argv) > 3 else 1100
    raw = open(path, "rb").read()
    os.makedirs(OUT, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]

    print(f"scanning prefix length N in [{nlo}, {nhi}] for {os.path.basename(path)}")
    winners = []
    for n in range(nlo, nhi + 1):
        dec = xor_prefix(raw, n)
        if dec[:7] != b"UnityFS":
            continue
        tmp = os.path.join(OUT, f"_scan_{stem}.unity3d")
        open(tmp, "wb").write(dec)
        try:
            env = UnityPy.load(tmp)
            nobj = len(env.objects)
            if nobj:
                winners.append((n, nobj))
                kinds = {}
                for o in env.objects:
                    kinds[o.type.name] = kinds.get(o.type.name, 0) + 1
                print(f"  N={n}: OK {nobj} objects {kinds}")
        except Exception:
            pass
    print(f"winners: {winners}")
    if not winners:
        print("no prefix length produced a loadable bundle")
        return
    best = max(winners, key=lambda t: t[1])
    final = os.path.join(OUT, stem + ".decrypted.unity3d")
    open(final, "wb").write(xor_prefix(raw, best[0]))
    print(f"BEST N={best[0]} ({best[1]} objects) -> {final}")


if __name__ == "__main__":
    main()
