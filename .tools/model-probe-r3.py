# model-probe-r3.py -- material->texture map, per-submesh material names, forward-axis detection.
import os
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler

BASE = r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab"
BUNDLE = os.path.join(BASE, "pet__3015004_prefab.unity3d")


def g(o, *names, default=None):
    for n in names:
        v = getattr(o, n, None)
        if v is not None:
            return v
    return default


def pid(x):
    if x is None:
        return None
    v = getattr(x, "m_PathID", None)
    if v is not None:
        return v
    inner = getattr(x, "component", None)
    if inner is not None:
        return getattr(inner, "m_PathID", None)
    try:
        return int(x)
    except Exception:
        return None


env = UnityPy.load(BUNDLE)
texname = {}
for o in env.objects:
    if o.type.name == "Texture2D":
        texname[o.path_id] = g(o.read(), "m_Name")

mat2tex = {}
matname = {}
for o in env.objects:
    if o.type.name != "Material":
        continue
    d = o.read()
    matname[o.path_id] = g(d, "m_Name")
    sp = g(d, "m_SavedProperties")
    found = {}
    if sp is not None:
        for entry in (g(sp, "m_TexEnvs") or []):
            try:
                k, v = entry[0], entry[1]
            except Exception:
                continue
            tp = pid(g(v, "m_Texture"))
            if tp:
                found[k] = (tp, texname.get(tp))
    mat2tex[o.path_id] = found

print("=== MATERIAL -> TEXTURES ===")
for mpid, n in sorted(matname.items(), key=lambda kv: str(kv[1])):
    f = mat2tex.get(mpid) or {}
    print("  %-34s %s" % (n, {k: v[1] for k, v in f.items()}))

print("\n=== MESH SUBMESH -> MATERIAL ===")
meshes = {o.path_id: o for o in env.objects if o.type.name == "Mesh"}
for so in env.objects:
    if so.type.name != "SkinnedMeshRenderer":
        continue
    d = so.read()
    mp = pid(g(d, "m_Mesh"))
    mo = meshes.get(mp)
    if mo is None:
        continue
    md = mo.read()
    nm = g(md, "m_Name")
    mats = [pid(x) for x in (g(d, "m_Materials") or [])]
    h = MeshHandler(md); h.process()
    V = np.array(h.m_Vertices, dtype=np.float64)
    ib = np.array(h.m_IndexBuffer, dtype=np.int64).ravel()
    subs = g(md, "m_SubMeshes") or []
    print("\n  %s  (%d submeshes, %d mats)" % (nm, len(subs), len(mats)))
    for si, s in enumerate(subs):
        ic = int(g(s, "indexCount"))
        fv = int(g(s, "firstVertex"))
        # index buffer offset: use running sum of indexCount (firstByte is per-stride)
        off = sum(int(g(x, "indexCount")) for x in subs[:si])
        tri = ib[off:off + ic]
        # last index used
        print("     [%d] mat=%-34s idxCount=%5d firstVertex=%5d  idx[%d:%d] maxIdxUsed=%d  bboxY=[%.3f..%.3f] bboxZ=[%.3f..%.3f] bboxX=[%.3f..%.3f]"
              % (si, (matname.get(mats[si]) if si < len(mats) else "?"), ic, fv,
                 off, off + ic, tri.max(), V[tri, 1].min(), V[tri, 1].max(),
                 V[tri, 2].min(), V[tri, 2].max(), V[tri, 0].min(), V[tri, 0].max()))

# ---------- forward axis detection ----------
print("\n=== FORWARD AXIS HEURISTIC ===")
# The head is roughly y>1.40. Compare z-extent of the whole model vs x-extent near the head.
faceobj = meshes[[k for k, v in meshes.items() if g(v.read(), "m_Name") == "mx_3015004_01_face"][0]]
h = MeshHandler(faceobj.read()); h.process()
V = np.array(h.m_Vertices, dtype=np.float64)
head = V[V[:, 1] > 1.45]
print("  face verts y>1.45: n=%d  x[%.3f..%.3f] z[%.3f..%.3f] meanZ=%.4f" % (
    len(head), head[:, 0].min(), head[:, 0].max(), head[:, 2].min(), head[:, 2].max(), head[:, 2].mean()))

# Sphere005 = likely an eye/iris helper: where is it?
for k, v in meshes.items():
    d = v.read()
    if g(d, "m_Name") != "Sphere005":
        continue
    hh = MeshHandler(d); hh.process()
    VV = np.array(hh.m_Vertices, dtype=np.float64)
    print("  Sphere005 bbox min=%s max=%s centroid=%s" % (np.round(VV.min(0), 3), np.round(VV.max(0), 3), np.round(VV.mean(0), 3)))
