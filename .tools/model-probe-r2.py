# model-probe-r2.py -- diagnose (a) per-axis diff vs OBJ, (b) Material texture wiring, (c) texture decode.
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

# ---------- (a) axis diff vs OBJ ----------
print("=== AXIS DIFF vs OBJ ===")
for obj in env.objects:
    if obj.type.name != "Mesh":
        continue
    d = obj.read()
    nm = g(d, "m_Name")
    p = os.path.join(BASE, "Mesh", nm + ".obj")
    if not os.path.exists(p):
        continue
    ov = []
    for line in open(p, "r", encoding="utf-8", errors="replace"):
        if line.startswith("v "):
            ov.append([float(x) for x in line.split()[1:4]])
    ov = np.array(ov, dtype=np.float64)
    h = MeshHandler(d); h.process()
    mv = np.array(h.m_Vertices, dtype=np.float64)
    diff = ov - mv
    print("  %-28s n=%5d  diff per-axis  x:[%8.4f..%8.4f] mean %7.4f | y:[%8.4f..%8.4f] mean %7.4f | z:[%8.4f..%8.4f] mean %7.4f"
          % (nm, len(mv), diff[:, 0].min(), diff[:, 0].max(), diff[:, 0].mean(),
             diff[:, 1].min(), diff[:, 1].max(), diff[:, 1].mean(),
             diff[:, 2].min(), diff[:, 2].max(), diff[:, 2].mean()))
    print("      decoded bbox min=%s max=%s" % (np.round(mv.min(0), 4), np.round(mv.max(0), 4)))
    print("      obj     bbox min=%s max=%s" % (np.round(ov.min(0), 4), np.round(ov.max(0), 4)))
    # is it exactly a z-flip?
    flipped = mv.copy(); flipped[:, 2] *= -1
    print("      z-flip maxdiff=%.6g ; y-flip maxdiff=%.6g ; x-flip maxdiff=%.6g" % (
        np.abs(ov - flipped).max(),
        np.abs(ov - (mv * np.array([1, -1, 1]))).max(),
        np.abs(ov - (mv * np.array([-1, 1, 1]))).max()))

# ---------- (b) Material internals ----------
print("\n=== MATERIAL RAW STRUCTURE ===")
mats = [o for o in env.objects if o.type.name == "Material"]
for mo in mats[:3]:
    d = mo.read()
    print("  --- %s ---" % g(d, "m_Name"))
    print("   attrs:", [a for a in dir(d) if not a.startswith("__")])
    sp = g(d, "m_SavedProperties")
    print("   savedprops type:", type(sp))
    if sp is not None:
        print("   savedprops attrs:", [a for a in dir(sp) if not a.startswith("__")])
        te = g(sp, "m_TexEnvs")
        print("   m_TexEnvs type=%s len=%s" % (type(te), None if te is None else len(te)))
        if te:
            e0 = te[0]
            print("   entry0 type:", type(e0), [a for a in dir(e0) if not a.startswith("__")])
            print("   entry0 repr:", repr(e0)[:400])
        fl = g(sp, "m_Floats")
        if fl:
            print("   m_Floats entry0:", repr(fl[0])[:300])

# ---------- (c) texture decode ----------
print("\n=== TEXTURE DECODE ===")
from PIL import Image
for to in env.objects:
    if to.type.name != "Texture2D":
        continue
    d = to.read()
    nm = g(d, "m_Name")
    if nm not in ("tt_3015004_01_cloth", "tt_3015004_01_hair", "tt_3015004_01_face",
                  "tt_3015004_01_weapon", "tt_3015004_01_body"):
        continue
    try:
        img = d.image
        print("  %-26s fmt=%s size=%s mode=%s" % (nm, g(d, "m_TextureFormat"), img.size, img.mode))
    except Exception as e:
        print("  %-26s FAILED %s" % (nm, e))

# ---------- (d) all mesh names + which material slots ----------
print("\n=== SMR -> mesh resolution ===")
for so in env.objects:
    if so.type.name != "SkinnedMeshRenderer":
        continue
    d = so.read()
    mm = g(d, "m_Mesh")
    print("  smr %s -> mesh ptr type=%s repr=%s" % (so.path_id, type(mm), repr(mm)[:200]))
    break
