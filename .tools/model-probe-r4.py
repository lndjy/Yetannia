# model-probe-r4.py -- Matrix4x4 + Transform structure, bone parent chains, world matrix sanity.
import os
import numpy as np
import UnityPy

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

mesh = [o for o in env.objects if o.type.name == "Mesh" and g(o.read(), "m_Name") == "mx_3015004_01_body"][0]
md = mesh.read()
bp = g(md, "m_BindPose")
print("m_BindPose len", len(bp), "elem type", type(bp[0]))
e = bp[0]
print("elem attrs:", [a for a in dir(e) if not a.startswith("_")])
print("repr:", repr(e)[:500])
for a in ("m_00", "m_03", "m_33", "e00", "m_Data", "data"):
    print("   %s ->" % a, getattr(e, a, "<none>"))

print("\n--- Transform ---")
t = [o for o in env.objects if o.type.name == "Transform"][0]
td = t.read()
print("attrs:", [a for a in dir(td) if not a.startswith("_")])
print("repr local:", repr(g(td, "m_LocalPosition")), repr(g(td, "m_LocalRotation")), repr(g(td, "m_LocalScale")))
print("m_LocalEulerAnglesHint:", repr(g(td, "m_LocalEulerAnglesHint")) if hasattr(td, "m_LocalEulerAnglesHint") else "n/a")
print("m_RootOrder:", g(td, "m_RootOrder"))

print("\n--- root transforms (no father) ---")
trs = {}
for o in env.objects:
    if o.type.name in ("Transform", "RectTransform"):
        trs[o.path_id] = o.read()
roots = [k for k, v in trs.items() if pid(g(v, "m_Father")) not in trs]
for r in roots:
    v = trs[r]
    go = g(v, "m_GameObject")
    print("  root %s name=%s localpos=%s" % (r, g(go.read(), "m_Name") if go else "?", repr(g(v, "m_LocalPosition"))))

print("\n--- count transforms:", len(trs))

# weapon SMR bones
print("\n--- weapon SMR ---")
meshes = {o.path_id: o for o in env.objects if o.type.name == "Mesh"}
for so in env.objects:
    if so.type.name != "SkinnedMeshRenderer":
        continue
    d = so.read()
    mp = pid(g(d, "m_Mesh"))
    nm = g(meshes[mp].read(), "m_Name") if mp in meshes else "?"
    if nm not in ("mx_3015004_01_weapon", "mx_3015004_01_weapon01"):
        continue
    bones = [pid(b) for b in (g(d, "m_Bones") or [])]
    rb = pid(g(d, "m_RootBone"))
    t0 = trs.get(bones[0]) if bones else None
    go0 = g(t0, "m_GameObject") if t0 else None
    print("  %s: bones=%s rootbone=%s  bone0name=%s bone0pos=%s  rootbone_is_bone0=%s"
          % (nm, bones, rb, g(go0.read(), "m_Name") if go0 else "?", repr(g(t0, "m_LocalPosition")) if t0 else "?", rb == (bones[0] if bones else None)))
    # also the SMR's own gameobject transform
    sgo = g(d, "m_GameObject")
    print("     smr GO name=%s" % (g(sgo.read(), "m_Name") if sgo else "?"))
    # find the transform whose gameObject == that
    for k, v in trs.items():
        if pid(g(v, "m_GameObject")) == pid(sgo):
            print("     smr GO transform=%s localpos=%s father=%s" % (k, repr(g(v, "m_LocalPosition")), pid(g(v, "m_Father"))))
            break

# Is Sphere005 rendered by a MeshRenderer?
print("\n--- Sphere005 references ---")
for k, v in meshes.items():
    if g(v.read(), "m_Name") != "Sphere005":
        continue
    for o in env.objects:
        if o.type.name in ("MeshRenderer", "MeshFilter"):
            dd = o.read()
            if pid(g(dd, "m_Mesh")) == k:
                print("   %s %s references Sphere005" % (o.type.name, o.path_id))
                sgo = g(dd, "m_GameObject")
                print("      GO:", g(sgo.read(), "m_Name") if sgo else "?")
