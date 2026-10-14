# model-lz4-trace.py — walk the blocksInfo LZ4 stream byte by byte and report where it dies.
#
# UnityPy only says "LZ4BlockError ... (485)". A hand-written LZ4 block decoder can say
# *which input offset* produced an invalid back-reference, and how many output bytes were
# produced before that. That turns "corrupt" into a concrete address.
#
# usage: python .tools/model-lz4-trace.py
import struct
import sys

MODEL = r"D:\桌面\sts2mod\model\pet\3015004_prefab.data"
VOICE = r"D:\桌面\sts2mod\日配耶未解原文件\Voice_3015004_Skill_1_p01.dat"


def parse_fs_header(buf, xor=None):
    """UnityFS header. BIG-ENDIAN after the 8-byte signature (field-proven)."""
    if xor is not None:
        buf = bytes(b ^ xor for b in buf)
    assert buf[:7] == b"UnityFS", buf[:8]
    off = 8
    version = struct.unpack_from(">I", buf, off)[0]; off += 4
    vp_end = buf.index(b"\x00", off); ver_player = buf[off:vp_end].decode(); off = vp_end + 1
    ve_end = buf.index(b"\x00", off); ver_engine = buf[off:ve_end].decode(); off = ve_end + 1
    size = struct.unpack_from(">q", buf, off)[0]; off += 8
    cbis = struct.unpack_from(">I", buf, off)[0]; off += 4
    ubis = struct.unpack_from(">I", buf, off)[0]; off += 4
    flags = struct.unpack_from(">I", buf, off)[0]; off += 4
    # version >= 7 (or 2019.4.15+) -> align reader to 16 before blocksInfo
    aligned = (off + 15) & ~15
    return dict(buf=buf, version=version, ver_player=ver_player, ver_engine=ver_engine,
                size=size, cbis=cbis, ubis=ubis, flags=flags, hdr_end=off, data_off=aligned)


def lz4_block_decode(src, max_out=None, verbose=True):
    """Decode a raw LZ4 block. Returns (out, status, fail_off, i)."""
    out = bytearray()
    i = 0
    n = len(src)
    seq = 0
    while i < n:
        seq += 1
        tok_off = i
        token = src[i]; i += 1
        litlen = token >> 4
        if litlen == 15:
            while True:
                if i >= n:
                    return bytes(out), "truncated in litlen ext", tok_off, i
                b = src[i]; i += 1
                litlen += b
                if b != 255:
                    break
        if i + litlen > n:
            return bytes(out), f"literals run past end (need {litlen}, have {n - i})", tok_off, i
        out += src[i:i + litlen]
        i += litlen
        if i == n:                      # last sequence: literals only, no match
            return bytes(out), "ok (ended on literals)", tok_off, i
        if i + 2 > n:
            return bytes(out), "truncated in match offset", tok_off, i
        offset = src[i] | (src[i + 1] << 8); i += 2
        matchlen = token & 0x0F
        if matchlen == 15:
            while True:
                if i >= n:
                    return bytes(out), "truncated in matchlen ext", tok_off, i
                b = src[i]; i += 1
                matchlen += b
                if b != 255:
                    break
        matchlen += 4
        if offset == 0 or offset > len(out):
            return (bytes(out),
                    f"INVALID back-reference: offset={offset} but only {len(out)} bytes of history",
                    tok_off, i)
        for _ in range(matchlen):
            out.append(out[-offset])
    return bytes(out), "ok (ran out of input)", i, i


def report(label, path, xor):
    raw = open(path, "rb").read()
    h = parse_fs_header(raw, xor)
    print(f"===== {label} ({len(raw)} bytes, xor={xor}) =====")
    print(f"  version={h['version']} engine={h['ver_engine']!r} player={h['ver_player']!r}")
    print(f"  size={h['size']} (file {len(raw)})  cbis={h['cbis']} ubis={h['ubis']} flags=0x{h['flags']:x}")
    print(f"  header ends {h['hdr_end']}, blocksInfo at {h['data_off']} (16-aligned)")

    # alignment padding between header end and blocksInfo
    pad = h['buf'][h['hdr_end']:h['data_off']]
    print(f"  pad[{h['hdr_end']}:{h['data_off']}] = {pad.hex(' ')}")

    for off in (h['hdr_end'], h['data_off']):
        blob = h['buf'][off:off + h['cbis']]
        out, status, fail, endi = lz4_block_decode(blob)
        print(f"  -- lz4 from off {off}: {status}; produced {len(out)}/{h['ubis']} bytes; "
              f"died at seq input off {off + fail} (rel {fail})")
        if off == h['data_off']:
            print(f"     first 32 bytes of block: {blob[:32].hex(' ')}")
            try:
                import lz4.block
                d = lz4.block.decompress(blob, uncompressed_size=h['ubis'])
                print(f"     lz4.block.decompress: OK, {len(d)} bytes")
            except Exception as exc:
                print(f"     lz4.block.decompress: {type(exc).__name__}: {exc}")
            if out:
                print(f"     partial output head: {out[:48].hex(' ')}")
                # hunt for node paths in the partial output
                for name in (b"CAB-", b".prefab", b"Assets/"):
                    if name in out:
                        print(f"     partial output contains {name!r}")
    print()


report("MODEL 3015004_prefab.data (xor 0x7b)", MODEL, 0x7B)
report("VOICE Voice_3015004_Skill_1_p01.dat (plain)", VOICE, None)
