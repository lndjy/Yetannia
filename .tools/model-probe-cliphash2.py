# model-probe-cliphash2.py -- why did hash resolution fail? Dump real structures + try alternatives.
import binascii
import os
import UnityPy

BUNDLE = r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab\pet__3015004_prefab.unity3d"


def gg(o, *names, **kw):
    for n in names:
        v = getattr(o, n, None)
        if v is not None:
            return v
    return kw.get("default")


def pid(x):
    if x is None:
        return None
    v = getattr(x, "m_PathID", None)
    if v is not None:
        return v
    i = getattr(x, "component", None)
    if i is not None:
        return getattr(i, "m_PathID", None)
    try:
        return int(x)
    except Exception:
        return None


env = UnityPy.load(BUNDLE)

clips = [o for o in env.objects if o.type.name == "AnimationClip"]
print("clip count", len(clips))
co = clips[0]
d = co.read()
print("clip name:", gg(d, "m_Name"))
print("clip attrs:", sorted(a for a in dir(d) if not a.startswith("_")))

mc = gg(d, "m_MuscleClip", "m_MuscleClipSize")
print("\nm_MuscleClip ->", type(mc))
if mc is not None:
    print("  attrs:", sorted(a for a in dir(mc) if not a.startswith("_")))

cb = gg(d, "m_ClipBindingConstant")
print("\nm_ClipBindingConstant ->", type(cb))
if cb is not None:
    print("  attrs:", sorted(a for a in dir(cb) if not a.startswith("_")))

# where do the generic bindings live?
for holder_name, holder in (("m_ClipBindingConstant", cb), ("m_MuscleClip", mc)):
    if holder is None:
        continue
    gb = gg(holder, "genericBindings", "m_GenericBindings")
    print("\n  %s.genericBindings len=%s" % (holder_name, None if gb is None else len(gb)))
    if gb:
        for b in gb[:3]:
            print("     type=%s attrs=%s" % (type(b), sorted(a for a in dir(b) if not a.startswith('_'))))
            print("     repr=", repr(b)[:300])

# dump MuscleClip sub-structs by scanning attributes for Dense/Streamed
print("\n=== scan clip object graph for Dense/Streamed/curve ===")
seen = set()


def scan(o, label, depth=0):
    if depth > 3 or id(o) in seen:
        return
    seen.add(id(o))
    for a in dir(o):
        if a.startswith("_"):
            continue
        try:
            v = getattr(o, a)
        except Exception:
            continue
        tl = type(v).__name__
        if "Dense" in tl or "Streamed" in tl or "Dense" in a or "Streamed" in a or "Clip" in tl:
            print("  %s%s.%s -> %s" % ("  " * depth, label, a, tl))
            if depth < 3:
                scan(v, "%s.%s" % (label, a), depth + 1)
        elif isinstance(v, (int, float)) and ("ount" in a or "ate" in a):
            print("  %s%s.%s = %s" % ("  " * depth, label, a, v))


for k in ("m_MuscleClip", "m_ClipBindingConstant", "m_SampleArray", "m_DenseClip"):
    v = gg(d, k)
    if v is not None:
        print("  clip.%s -> %s" % (k, type(v).__name__))
        scan(v, "clip." + k)

# ---- hash function candidates against 265 relative paths
trs, name, father = {}, {}, {}
for o in env.objects:
    if o.type.name in ("Transform", "RectTransform"):
        dd = o.read()
        trs[o.path_id] = dd
        go = gg(dd, "m_GameObject")
        name[o.path_id] = gg(go.read(), "m_Name") if go else "?"
        father[o.path_id] = pid(gg(dd, "m_Father"))


def path_of(t, stop_at_root=True):
    parts = []
    while t in trs:
        parts.append(name[t])
        t = father.get(t)
    return "/".join(reversed(parts))


def unity_hash(s):
    h = 0
    for ch in s:
        h = (ord(ch) + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


def djb2(s):
    h = 5381
    for ch in s:
        h = ((h * 33) + ord(ch)) & 0xFFFFFFFF
    return h


def fnv1a(s):
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


variants = {}
for t in trs:
    if father.get(t) not in trs:
        continue
    full = path_of(t)
    short = full.split("/", 1)[1] if "/" in full else full
    for tag, s in (("full", full), ("short", short)):
        variants.setdefault(("unity", tag), set()).add(unity_hash(s))
        variants.setdefault(("djb2", tag), set()).add(djb2(s))
        variants.setdefault(("fnv1a", tag), set()).add(fnv1a(s))
        variants.setdefault(("crc32", tag), set()).add(binascii.crc32(s.encode()) & 0xFFFFFFFF)

# gather every binding path value in every clip
allpaths = set()
for c in clips:
    dd = c.read()
    holder = gg(dd, "m_ClipBindingConstant")
    gb = (gg(holder, "genericBindings") if holder is not None else None) or []
    for b in gb:
        p = gg(b, "path", "m_Path")
        if p is not None:
            allpaths.add(int(p) & 0xFFFFFFFF)
print("\n=== HASH CANDIDATE MATCH RATE (bindings=%d, paths=%d) ===" % (len(allpaths), len(trs)))
for k, hs in sorted(variants.items()):
    print("  %-16s matched %d / %d bindings" % ("%s/%s" % k, len(allpaths & hs), len(allpaths)))
