# model-decrypt-final.py — the real decryption: XOR the first 1000 bytes with 0x7b, leave the rest.
#
# Proven by the .manifest CRC: crc32(concatenated decompressed blocks) == manifest CRC exactly for
# N=1000 and for no other N. So this is a *prefix* obfuscation, not whole-file encryption.
#
# usage: python .tools/model-decrypt-final.py <in.data> <out.unity3d> [N]
import os
import sys

N_DEFAULT = 1000


def decrypt(raw, n=N_DEFAULT):
    return bytes(b ^ 0x7B for b in raw[:n]) + raw[n:]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else N_DEFAULT
    raw = open(src, "rb").read()
    dec = decrypt(raw, n)
    assert dec[:7] == b"UnityFS", dec[:8]
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(dec)
    print(f"{src} -> {dst}  ({len(dec)} bytes, prefix {n} xored with 0x7b)")


if __name__ == "__main__":
    main()
