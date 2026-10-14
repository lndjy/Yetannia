# model-probe-r1.py -- reconnaissance for the Python-only bind-pose renderer.
# Dumps: mesh/submesh/material/texture wiring, bone lists, bind pose stats, skin weight stats.
import json
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler

BUNDLE = r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab\pet__3015004_prefab.unity3d"


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


def g(o, *names, default=None):
    for n in names:
        v = getattr(o, n, None)
        if v is not None:
            return v
    return default


env = UnityPy.load(BUNDLE)

# ---- index objects by type
meshes = {}
textures = {}
materials = {}
smrs = {}
for obj in env.objects:
    t = obj.type.name
    if t == "Mesh":
        meshes[obj.path_id] = obj
    elif t == "Texture2D":
        textures[obj.path_id] = obj
    elif t == "Material":
        materials[obj.path_id] = obj
    elif t == "SkinnedMeshRenderer":
        smrs[obj.path_id] = obj

print("counts: Mesh=%d Tex=%d Mat=%d SMR=%d" % (len(meshes), len(textures), len(materials), len(smrs)))

# ---- materials
print("\n=== MATERIALS ===")
for mpid, mo in materials.items():
    d = mo.read()
    name = g(d, "m_Name")
    saved = g(d, "m_SavedProperties")
    texs = []
    if saved is not None:
        for key in ("m_TexEnvs", "m_Floats", "m_Colors"):
            v = g(saved, key)
            if v is None:
                continue
            for entry in v:
                # entry may be (key, value) pair object
                k = g(entry, "first", "key")
                val = g(entry, "second", "value")
                if key == "m_TexEnvs":
                    tt = g(val, "m_Texture")
                    texs.append((k, pid(tt)))
    print("  mat %s (%s): %s" % (name, mpid, [x for x in texs if x[1]]))

# ---- textures
print("\n=== TEXTURES ===")
tname = {}
for tpid, to in textures.items():
    d = to.read()
    tname[tpid] = g(d, "m_Name")
for tpid, n in sorted(tname.items(), key=lambda kv: str(kv[1])):
    print("  %s -> %s" % (tpid, n))

# ---- skinned mesh renderers
print("\n=== SKINNED MESH RENDERERS ===")
hierarchy = json.load(open(r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab\hierarchy.json", encoding="utf-8"))
for spid, so in smrs.items():
    d = so.read()
    mn = g(d, "m_Mesh")
    mpid = pid(mn)
    bones = g(d, "m_Bones") or []
    bpid = [pid(b) for b in bones]
    print("  smr %s: mesh=%s (%s) bones=%d rootbone=%s" %
          (spid, mpid, tname.get(mpid), len(bpid), pid(g(d, "m_RootBone"))))
    print("     materials: %s" % [pid(x) for x in (g(d, "m_Materials") or [])])

# ---- meshes
print("\n=== MESHES ===")
for mpid, mo in meshes.items():
    d = mo.read()
    nm = g(d, "m_Name")
    verts = g(d, "m_VertexData")
    h = MeshHandler(d)
    h.process()
    bp = g(d, "m_BindPose") or []
    print("\n  mesh %s (%s)" % (nm, mpid))
    print("    verts=%d uv0=%d normals=%s boneW=%s boneI=%s bindposes=%d" % (
        len(h.m_Vertices), len(h.m_UV0) if h.m_UV0 is not None else -1,
        None if h.m_Normals is None else len(h.m_Normals),
        None if h.m_BoneWeights is None else len(h.m_BoneWeights),
        None if h.m_BoneIndices is None else len(h.m_BoneIndices), len(bp)))
    # submeshes
    subs = g(d, "m_SubMeshes") or []
    print("    submeshes=%d" % len(subs))
    for si, s in enumerate(subs):
        print("      [%d] firstByte=%s firstVertex=%s indexCount=%s topo=%s" % (
            si, g(s, "firstByte"), g(s, "firstVertex"), g(s, "indexCount"), g(s, "topology")))
    idx = h.m_IndexBuffer
    print("    indexbuffer=%s dtype=%s" % (None if idx is None else len(idx), None if idx is None else getattr(idx, 'dtype', None)))
    # compare against OBJ
    import os
    objp = r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab\Mesh\%s.obj" % nm
    if os.path.exists(objp):
        nv = 0
        nf = 0
        objverts = []
        with open(objp, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("v "):
                    nv += 1
                    objverts.append([float(x) for x in line.split()[1:4]])
                elif line.startswith("f "):
                    nf += 1
        objverts = np.array(objverts, dtype=np.float64)
        mine = np.array(h.m_Vertices, dtype=np.float64)
        print("    OBJ: %d verts / %d faces" % (nv, nf))
        if len(objverts) == len(mine):
            dmax = np.abs(objverts - mine).max()
            print("    DECODE CHECK: max |obj - decoded| = %.9g  (mean %.3g)" % (
                dmax, np.abs(objverts - mine).mean()))
        else:
            print("    DECODE CHECK: vertex count mismatch!")
    else:
        print("    (no OBJ)")

# ---- hierarchy root names
print("\n=== HIERARCHY ROOTS ===")
for rn in list(hierarchy["hierarchies"].keys()):
    print("  root:", rn)

print("\n=== BONE PATH IDS of first big SMR ===")
for spid, so in smrs.items():
    d = so.read()
    bones = g(d, "m_Bones") or []
    bpid = [pid(b) for b in bones]
    if len(bpid) == 98:
        tr = {}
        for rn, rows in hierarchy["hierarchies"].items():
            pass
        # build transform map from bundle
        for o in env.objects:
            if o.type.name in ("Transform", "RectTransform"):
                dd = o.read()
                tr[o.path_id] = dd
        def nm(tid):
            t = tr.get(tid)
            if t is None:
                return "<?%s>" % tid
            go = g(t, "m_GameObject")
            if go is None:
                return "<noname>"
            return g(go.read(), "m_Name")
        print("  rootbone path:", nm(pid(g(d, "m_RootBone"))))
        for i, b in enumerate(bpid[:20]):
            print("   [%2d] %s -> %s" % (i, b, nm(b)))
        break
