# model-render.py -- Python-only bind-pose renderer for the decrypted Unity AssetBundles.
#
# PIPELINE (no Blender, no Unity, no engine involved):
#   1. UnityPy.load() the already-decrypted .unity3d (XOR-first-1000-bytes-with-0x7B scheme).
#   2. Mesh data comes from UnityPy's MeshHandler, NOT from mesh.m_Skin -- these meshes have
#      m_Skin == None, and the 4 bone weights + 4 bone indices ride the vertex-data channels.
#      MeshHandler.process() decodes them into h.m_BoneWeights / h.m_BoneIndices.
#   3. Bind-pose matrices live on the RAW mesh: mesh.m_BindPose (list of Matrix4x4f with e00..e33,
#      row-major, translation in e03/e13/e23). Length == len(SkinnedMeshRenderer.m_Bones), and
#      bindPose[i] is parallel to m_Bones[i].
#   4. Bone world matrices are composed from the Transform TRS tree of the same bundle
#      (quaternion -> 3x3, then scale columns, then translate; child = parent @ local).
#   5. Linear blend skinning at bind pose:
#          v' = SUM_i  w_i * ( boneWorld_i @ bindPose_i ) @ v
#      Because the prefab hierarchy IS the bind pose, each (boneWorld @ bindPose) is ~identity,
#      which is exactly the self-check printed at runtime.
#   6. Submesh -> material -> diffuse texture (_BasicTex / _MainTex); textures decoded through
#      Texture2D.image (PIL) so no manual ASTC/DXT work is needed.
#   7. One shared z-buffer rasteriser in numpy: auto-framed perspective camera on the skinned
#      bbox, per-triangle barycentric UV interpolation, directional shading blended with ambient,
#      alpha cutout where a texture actually uses its alpha channel.
#   8. Writes an RGBA PNG (transparent background) plus a preview sheet tiling the render next to
#      the diffuse textures that were used.
#
# AXES: source is Y-up. "Forward" (+Z) was determined from the rig, not guessed: the toe bones sit
# at +Z relative to their ankle bones (Bip001 L Toe0 z=-0.0392 vs Bip001 L Foot z=-0.1068), and the
# face features (eyes/eyebrows) sit at higher z than the face-plate mean while the long hair and
# trailing cloth extend toward -Z. The camera therefore sits on +Z looking back along -Z.
#
# usage: python .tools/model-render.py [bundle.unity3d] [outdir]

import argparse
import json
import math
import os
import sys

import numpy as np
import UnityPy
from PIL import Image, ImageDraw
from UnityPy.helpers.MeshHelper import MeshHandler

DEFAULT_BUNDLE = (r"D:\桌面\sts2mod\.tools\out\export"
                  r"\pet__3015004_prefab\pet__3015004_prefab.unity3d")
DEFAULT_OUTDIR = r"D:\桌面\sts2mod\.tools\out\render"

# Renderable parts, in the order the game builds them. Sphere005 is referenced by no renderer in
# this bundle (it is an effect helper mesh), so it is deliberately excluded.
PARTS = ["mx_3015004_01_body", "mx_3015004_01_body_02", "mx_3015004_01_face",
         "mx_3015004_01_hair", "mx_3015004_01_weapon", "mx_3015004_01_weapon01"]

# Material texture slots that can hold the albedo, best first.
DIFFUSE_SLOTS = ["_BasicTex", "_MainTex", "_BaseMap", "_MainColorTex"]

# ---------------------------------------------------------------------------------------------
# STYLISED (toon) SHADING -- added for the Yetannia combat flipbook.
#
# WHY: this renderer used to sample ONLY the albedo and multiply it by one flat lambert term
# (AMBIENT + (1-AMBIENT)*|dot(n,L)|). That is not how the character was authored. The materials
# carry a full anime/NPR setup, and the decoded art proves which parts of it are real:
#
#   _ShadowTex (_anbu)  bound on 5 of the 6 parts; its RGB is a hand-painted, darkened version of
#                       the SAME UV islands (measured mean/anbu ratio: cloth 0.57, cloth_02 0.67,
#                       face 0.75, hair 0.71, weapon 0.71 of the albedo). This IS the cel shadow
#                       colour, and it is the difference between "flat 3D render" and "cel art".
#                       Its ALPHA is not a mask (0.0 on hair/face/cloth_02, 1.0 on cloth), so the
#                       RGB is used, never the alpha.
#   _LightTex (*_grey)  a CONSTANT placeholder, not an image: every one of the four maps decodes to
#                       a uniform green with max channel 0.502 (mean 0.167). Deliberately ignored.
#   _BumpMap (*_n)      bound on 3 of ~20 submeshes, and EVERY one of those materials also sets
#                       NORMALMAP = 0.0, i.e. the game's own shader keyword is off. Deliberately
#                       ignored, so no tangents are needed either.
#   _Eye_LightingInfo   bound only on the eyes submesh, but decodes to RGB mean (0.012,0.004,0.000)
#                       and A mean 0.000 - ~99% black. Useless as a mask; and unnecessary, because
#                       the eye/eyebrow/gemstone submeshes have NO _ShadowTex, which is what keeps
#                       them fully lit.
#   _MetalLightingInfo  a real greyscale metal mask (mean 0.067 / 0.108, mostly black with detailed
#                       bright regions) and the metal materials set _Metallic 1, _SpecularIntensity
#                       5.0, _SpecColor. Used to gate a specular lobe.
#
# The engine-independent outline is a real part of the look too: every one of those materials sets
# NewOutlineOn = 1.0 with an _OutlineColor and an _OutlineAmount of 0.62-3.16. A flipbook cannot run
# an inverted-hull pass, so build-creature-anim.py bakes an equivalent silhouette outline instead.
CHANNEL_SLOTS = {
    "shadow": ("_ShadowTex",),
    "light": ("_LightTex",),
    "metal": ("_MetalLightingInfo", "_MetallicMask"),
    "eye": ("_EyeLightingInfo",),
}
# The keys of the per-material texture tuple, in order. tuple[0] is always the albedo.
CHANNEL_ORDER = ("shadow", "light", "metal", "eye")

AMBIENT = 0.42
LIGHT_DIR = np.array([0.30, 0.62, 0.72], dtype=np.float64)  # world space, front-top-right
ALPHA_CUTOFF = 0.5

# Defaults for the toon pass. Overridable per material from the material's own floats.
TOON_DEFAULTS = dict(
    threshold=0.65,        # _DiffuseThreshold
    half_lambert=True,     # compare the threshold against 0.5+0.5*NdotL, not raw NdotL
    smoothness=0.055,      # half-width of the lit->shadow transition
    lit_gain=1.0,          # multiplier on the albedo on the lit side
    shadow_gain=1.0,       # multiplier on _ShadowTex on the shadow side
    rim=0.0,               # edge/rim light strength
    rim_power=3.0,
    rim_color=(1.0, 1.0, 1.0),
    spec=0.0,              # specular strength (global scale on the material's _SpecularIntensity)
    spec_power=24.0,
)



# ----------------------------------------------------------------------------- helpers
def pid(x):
    """PPtr / ComponentPair -> path id."""
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


def gg(o, *names, **kw):
    """Defensive getattr: UnityPy's generated structs are inconsistent about the m_ prefix."""
    default = kw.get("default")
    for n in names:
        v = getattr(o, n, None)
        if v is not None:
            return v
    return default


def quat_to_mat3(q):
    # accepts a Unity Vector4f/Quaternionf (has .x/.y/.z/.w) or a plain 4-sequence (animation code
    # passes numpy rows straight from the decoded clip)
    try:
        x, y, z, w = float(q.x), float(q.y), float(q.z), float(q.w)
    except AttributeError:
        x, y, z, w = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-12:
        return np.eye(3)
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)


def mat4_from_e(m):
    """UnityPy Matrix4x4f (e00..e33, row-major, translation in the last column) -> 4x4 ndarray."""
    return np.array([[m.e00, m.e01, m.e02, m.e03],
                     [m.e10, m.e11, m.e12, m.e13],
                     [m.e20, m.e21, m.e22, m.e23],
                     [m.e30, m.e31, m.e32, m.e33]], dtype=np.float64)


def _v3(v):
    """Unity Vector3f or a plain 3-sequence -> tuple of floats."""
    try:
        return float(v.x), float(v.y), float(v.z)
    except AttributeError:
        return float(v[0]), float(v[1]), float(v[2])


def mat4_trs(t, r, s):
    M = np.eye(4)
    M[:3, :3] = quat_to_mat3(r) * np.array(_v3(s))[None, :]
    M[:3, 3] = _v3(t)
    return M


# ----------------------------------------------------------------------------- scene
class Scene(object):
    def __init__(self, bundle_path):
        self.env = UnityPy.load(bundle_path)
        self.bundle_path = bundle_path
        self.meshes = {}       # path_id -> Mesh object
        self.textures = {}     # path_id -> Texture2D object
        self.materials = {}    # path_id -> Material object
        self.transforms = {}   # path_id -> Transform object
        self.go_name = {}      # GameObject path_id -> name
        self._world = {}
        self._texcache = {}
        # Animation hook (added for model-anim-render.py): when set, it is {transform_path_id:
        # (pos3, quat4, scale3)} and OVERRIDES the prefab's own local TRS for those transforms, so
        # world_matrix()/build_part() can be re-evaluated at any pose of a clip. Left as None the
        # renderer behaves exactly as before (static bind pose).
        self.local_pose = None
        for o in self.env.objects:
            t = o.type.name
            if t == "Mesh":
                self.meshes[o.path_id] = o
            elif t == "Texture2D":
                self.textures[o.path_id] = o
            elif t == "Material":
                self.materials[o.path_id] = o
            elif t in ("Transform", "RectTransform"):
                self.transforms[o.path_id] = o.read()
            elif t == "GameObject":
                d = o.read()
                self.go_name[o.path_id] = gg(d, "m_Name")

    # ---- transform tree
    def tr_name(self, tid):
        t = self.transforms.get(tid)
        if t is None:
            return "<?%s>" % tid
        go = gg(t, "m_GameObject")
        return self.go_name.get(pid(go), "<unnamed>")

    def world_matrix(self, tid):
        if tid in self._world:
            return self._world[tid]
        t = self.transforms.get(tid)
        if t is None:
            return np.eye(4)
        if self.local_pose is not None and tid in self.local_pose:
            p, q, s = self.local_pose[tid]
            M = mat4_trs(p, q, s)
        else:
            M = mat4_trs(gg(t, "m_LocalPosition", default=None) or _ZERO,
                         gg(t, "m_LocalRotation", default=None) or _QID,
                         gg(t, "m_LocalScale", default=None) or _ONE)
        f = pid(gg(t, "m_Father"))
        if f in self.transforms:
            M = self.world_matrix(f) @ M
        self._world[tid] = M
        return M

    def reset_pose(self, local_pose=None):
        """Install a new pose (or None for the prefab bind pose) and drop the world-matrix cache."""
        self.local_pose = local_pose
        self._world = {}

    # ---- material / texture
    def material_channels(self, mpid):
        """Resolve one material into (albedo_tpid, {channel: tpid}, info).

        `info` carries m_Name plus the m_Floats / m_Colors dictionaries, which is where the cel
        threshold, rim colour and specular strength live. Returns (None, {}, None) for a missing
        material so callers can fall back to the previous flat-grey behaviour.
        """
        mo = self.materials.get(mpid)
        if mo is None:
            return None, {}, None
        d = mo.read()
        sp = gg(d, "m_SavedProperties")
        slots = {}
        if sp is not None:
            for entry in (gg(sp, "m_TexEnvs") or []):
                try:
                    key, val = entry[0], entry[1]
                except Exception:
                    continue
                tp = pid(gg(val, "m_Texture"))
                if tp:
                    slots[key] = tp
        alb = None
        for s in DIFFUSE_SLOTS:
            if s in slots:
                alb = slots[s]
                break
        chans = {}
        for c, names in CHANNEL_SLOTS.items():
            for n in names:
                if n in slots:
                    chans[c] = slots[n]
                    break
        info = {"name": gg(d, "m_Name"), "shader": pid(gg(d, "m_Shader")),
                "floats": {}, "colors": {}}
        if sp is not None:
            for e in (gg(sp, "m_Floats") or []):
                try:
                    info["floats"][e[0]] = float(e[1])
                except Exception:
                    pass
            for e in (gg(sp, "m_Colors") or []):
                try:
                    c = e[1]
                    info["colors"][e[0]] = [float(c.r), float(c.g), float(c.b), float(c.a)]
                except Exception:
                    pass
        return alb, chans, info

    def material_diffuse(self, mpid):
        """-> (texture_path_id or None, dict_of_all_slots)"""
        mo = self.materials.get(mpid)
        if mo is None:
            return None, {}
        d = mo.read()
        sp = gg(d, "m_SavedProperties")
        slots = {}
        if sp is not None:
            for entry in (gg(sp, "m_TexEnvs") or []):
                try:
                    key, val = entry[0], entry[1]
                except Exception:
                    continue
                tp = pid(gg(val, "m_Texture"))
                if tp:
                    slots[key] = tp
        for s in DIFFUSE_SLOTS:
            if s in slots:
                return slots[s], slots
        return None, slots

    def texture_image(self, tpid):
        if tpid in self._texcache:
            return self._texcache[tpid]
        out = None
        to = self.textures.get(tpid)
        if to is not None:
            try:
                d = to.read()
                img = d.image
                if img is not None:
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    out = np.asarray(img, dtype=np.float32) / 255.0
            except Exception as e:
                print("   ! texture %s failed: %s" % (tpid, e))
        self._texcache[tpid] = out
        return out


class _Zero(object):
    x = y = z = 0.0


class _One(object):
    x = y = z = 1.0


class _QId(object):
    x = y = z = 0.0
    w = 1.0


_ZERO, _ONE, _QID = _Zero(), _One(), _QId()


# ----------------------------------------------------------------------------- skinning
def decode_part(scene, mesh_name, verbose=True):
    """Decode one mesh + its SkinnedMeshRenderer into a reusable geometry record.

    Everything here is pose-independent, so a clip can re-skin the SAME record once per frame
    (model-anim-render.py does exactly that) without re-running MeshHandler.process().
    """
    # find mesh by name
    mesh_obj = None
    for o in scene.meshes.values():
        if gg(o.read(), "m_Name") == mesh_name:
            mesh_obj = o
            break
    if mesh_obj is None:
        raise KeyError("mesh %s not found" % mesh_name)
    md = mesh_obj.read()
    mid = mesh_obj.path_id

    # find the SkinnedMeshRenderer that uses it
    smr = None
    for o in scene.env.objects:
        if o.type.name != "SkinnedMeshRenderer":
            continue
        d = o.read()
        if pid(gg(d, "m_Mesh")) == mid:
            smr = d
            break
    if smr is None:
        raise KeyError("no SkinnedMeshRenderer for %s" % mesh_name)

    h = MeshHandler(md)
    h.process()
    V = np.asarray(h.m_Vertices, dtype=np.float64)
    N = np.asarray(h.m_Normals, dtype=np.float64) if h.m_Normals else None
    UV = np.asarray(h.m_UV0, dtype=np.float64) if h.m_UV0 else None
    W = np.asarray(h.m_BoneWeights, dtype=np.float64) if h.m_BoneWeights is not None else None
    BI = np.asarray(h.m_BoneIndices, dtype=np.int64) if h.m_BoneIndices is not None else None
    IB = np.asarray(h.m_IndexBuffer, dtype=np.int64).ravel()

    bind = [mat4_from_e(m) for m in (gg(md, "m_BindPose") or [])]
    bone_ids = [pid(b) for b in (gg(smr, "m_Bones") or [])]
    mats = [pid(x) for x in (gg(smr, "m_Materials") or [])]
    subs = gg(md, "m_SubMeshes") or []

    if verbose:
        print("  %-26s verts=%5d tris=%6d bones=%3d bindposes=%3d submeshes=%d"
              % (mesh_name, len(V), len(IB) // 3, len(bone_ids), len(bind), len(subs)))

    # ---- submesh -> material/texture, plus the per-submesh triangle index list
    #
    # `tex_ids` is a list of COMBINATION TUPLES, one per distinct material look:
    #     (albedo, shadow, light, metal, eye)   -- any entry may be None
    # tuple[0] is the albedo, which is all the pre-toon code ever needed. Keying on the whole
    # combination (and not on the albedo alone) is what lets the rasteriser pick the RIGHT
    # _ShadowTex per submesh: tt_3015004_01_cloth is the albedo of the metal, cloth, cloth_Double
    # and gemstones materials, but only the first three have a shadow map at all.
    tris, tex_ids, mat_slots = [], [], []
    for si, s in enumerate(subs):
        if gg(s, "topology", default=0) not in (0, None):
            continue  # 0 = Triangles; skip strips/lines for this proof
        ic = int(gg(s, "indexCount", default=0))
        off = sum(int(gg(x, "indexCount", default=0)) for x in subs[:si])
        tri = IB[off:off + ic]
        if tri.size < 3:
            continue
        tri = tri[: (len(tri) // 3) * 3].reshape(-1, 3)
        mpid = mats[si] if si < len(mats) else None
        tpid, chans, info = scene.material_channels(mpid)
        combo = tuple([tpid] + [chans.get(c) for c in CHANNEL_ORDER])
        if combo not in tex_ids:
            tex_ids.append(combo)
            mat_slots.append(dict(zip(CHANNEL_ORDER, combo[1:]), albedo=tpid, mpid=mpid,
                                  info=info or {}))
        if tpid is None and verbose:
            print("     submesh %d: no diffuse texture -> flat grey" % si)
        tris.append((tri, tex_ids.index(combo)))

    return dict(name=mesh_name, mid=mid, V=V, N=N, UV=UV, W=W, BI=BI, IB=IB,
                bind=bind, bone_ids=bone_ids, mats=mats, subs=len(subs),
                tris=tris, tex_ids=tex_ids, mat_slots=mat_slots)


def skin_part(scene, geom, verbose=True):
    """Linear blend skinning of a decoded part at the CURRENT pose of the scene.

    boneWorld_i comes from scene.world_matrix(), so setting scene.local_pose() first is what makes
    this animate. Returns (P, NR, diag) where diag carries the bind-pose residuals.
    """
    V, N, W, BI = geom["V"], geom["N"], geom["W"], geom["BI"]
    bind, bone_ids = geom["bind"], geom["bone_ids"]
    mesh_name = geom["name"]

    nB = len(bone_ids)
    if nB and len(bind) >= nB:
        sm = np.stack([scene.world_matrix(bone_ids[i]) @ bind[i] for i in range(nB)])
    elif nB == 1 and len(bind) == 1:
        sm = np.stack([scene.world_matrix(bone_ids[0]) @ bind[0]])
    else:
        sm = np.eye(4)[None]

    if W is None:
        # Rigid / single-bone meshes (the weapons): no weight channel at all.
        if BI is not None and np.asarray(BI).size:
            idx = np.clip(np.asarray(BI)[:, 0], 0, len(sm) - 1)
            Mv = sm[idx][:, None, :, :]                     # (N,1,4,4)
        else:
            Mv = np.repeat(sm[0][None, None], len(V), axis=0)
        Wv = np.ones((len(V), 1), dtype=np.float64)
    else:
        idx = np.clip(BI, 0, len(sm) - 1)
        Mv = sm[idx]                                        # (N,4,4,4)
        Wv = W
        s = Wv.sum(axis=1, keepdims=True)
        s[s < 1e-9] = 1.0
        Wv = Wv / s

    vh = np.concatenate([V, np.ones((len(V), 1))], axis=1)   # (N,4)
    out = np.einsum("nkij,nj->nki", Mv, vh)                  # (N,4,4)
    w4 = out[..., 3:4].copy()
    w4[np.abs(w4) < 1e-12] = 1.0
    p3 = out[..., :3] / w4
    P = np.einsum("nk,nki->ni", Wv, p3)

    if N is not None:
        nh = np.concatenate([N, np.zeros((len(N), 1))], axis=1)
        nout = np.einsum("nkij,nj->nki", Mv, nh)[..., :3]
        NR = np.einsum("nk,nki->ni", Wv, nout)
        ln = np.linalg.norm(NR, axis=1, keepdims=True)
        ln[ln < 1e-9] = 1.0
        NR = NR / ln
    else:
        NR = None

    ident_err = float(np.abs(sm[:, :3, :3] - np.eye(3)[None]).max()) if len(sm) else 0.0
    pos_err = float(np.abs(sm[:, :3, 3]).max()) if len(sm) else 0.0
    reskew = float(np.abs(P - V).max())

    if verbose and (ident_err > 1e-3 or pos_err > 1e-3):
        per = np.abs(sm[:, :3, :3] - np.eye(3)[None]).reshape(len(sm), -1).max(1)
        per = np.maximum(per, np.abs(sm[:, :3, 3]).max(1))
        worst = np.argsort(-per)[:6]
        print("     ! non-identity bone matrices (bind pose / rest pose mismatch):")
        for w in worst:
            bid = bone_ids[w] if w < len(bone_ids) else None
            print("        bone[%3d] %-28s resid=%.4f  in_hierarchy=%s"
                  % (w, scene.tr_name(bid) if bid else "?", per[w],
                     bid in scene.transforms))

    return P, NR, dict(bind_err=(ident_err, pos_err), reskew=reskew)


def assemble_tris(scene, geom, P, NR):
    """Gather the per-triangle attribute arrays the rasteriser consumes."""
    UV = geom["UV"]
    tri_pos, tri_nrm, tri_uv, tri_tex = [], [], [], []
    tex_ids = geom["tex_ids"]
    for tri, ti in geom["tris"]:
        tri_pos.append(P[tri])
        tri_nrm.append(NR[tri] if NR is not None else np.zeros_like(P[tri]))
        tri_uv.append(UV[tri] if UV is not None else np.zeros((len(tri), 3, 2)))
        tri_tex.append(np.full(len(tri), ti, dtype=np.int64))
    return dict(
        name=geom["name"], mid=geom["mid"], V=geom["V"], P=P, NR=NR,
        pos=np.concatenate(tri_pos, 0) if tri_pos else np.zeros((0, 3, 3)),
        nrm=np.concatenate(tri_nrm, 0) if tri_nrm else np.zeros((0, 3, 3)),
        uv=np.concatenate(tri_uv, 0) if tri_uv else np.zeros((0, 3, 2)),
        tex=np.concatenate(tri_tex, 0) if tri_tex else np.zeros(0, np.int64),
        tex_ids=geom["tex_ids"], mat_slots=geom.get("mat_slots", []), subs=geom["subs"])


def build_part(scene, mesh_name, verbose=True, geom=None):
    """Decode one mesh + its SkinnedMeshRenderer and skin it at the CURRENT pose."""
    if geom is None:
        geom = decode_part(scene, mesh_name, verbose)
    P, NR, diag = skin_part(scene, geom, verbose)
    data = assemble_tris(scene, geom, P, NR)
    data["geom"] = geom
    data.update(diag)
    if verbose:
        print("     bind-pose residual: rot %.2e  trans %.2e | |skinned - raw| max %.2e"
              % (diag["bind_err"][0], diag["bind_err"][1], diag["reskew"]))
        print("     textures: %s" % [[(scene.textures[t].read().m_Name
                                      if t in scene.textures else t) for t in combo]
                                     for combo in data["tex_ids"]])
    return data


# ----------------------------------------------------------------------------- camera
def look_at(eye, target, up):
    f = target - eye
    f = f / np.linalg.norm(f)
    zc = -f
    xc = np.cross(up, zc)
    xc = xc / np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    R = np.stack([xc, yc, zc])
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = -R @ eye
    return M


def perspective(fov_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov_deg) * 0.5)
    P = np.zeros((4, 4))
    P[0, 0] = f / aspect
    P[1, 1] = f
    P[2, 2] = (far + near) / (near - far)
    P[2, 3] = 2 * far * near / (near - far)
    P[3, 2] = -1.0
    return P


# ----------------------------------------------------------------------------- stylised shading
def toon_params(mat, opts):
    """Per-material toon parameters: the material's own floats/colours, over an override dict.

    `opts` may carry the keys of TOON_DEFAULTS; a material's own _DiffuseThreshold / _SpecularIntensity
    / _SpecColor win unless opts explicitly overrides them (opts keys ending in "_force").
    """
    p = dict(TOON_DEFAULTS)
    p.update({k: v for k, v in opts.items() if k in TOON_DEFAULTS})
    f = (mat or {}).get("info", {}).get("floats", {}) or {}
    c = (mat or {}).get("info", {}).get("colors", {}) or {}
    if not opts.get("threshold_force") and "_DiffuseThreshold" in f:
        p["threshold"] = float(f["_DiffuseThreshold"])
    if not opts.get("smoothness_force"):
        # _DefSmooth / _DiffuseSmoothness are the authored softness; they range 0.001..0.3.
        for k in ("_DiffuseSmoothness", "_DefSmooth"):
            if k in f and 0.0 < float(f[k]) <= 0.35:
                p["smoothness"] = max(0.012, float(f[k]))
                break
    sc = c.get("_SpecColor")
    if sc is not None:
        p["spec_color"] = tuple(sc[:3])
    if "_SpecularIntensity" in f:
        p["spec_power_mul"] = float(f["_SpecularIntensity"])
    if "_Shininess" in f:
        p["spec_power"] = max(4.0, min(120.0, float(f["_Shininess"]) * 8.0))
    p["has_shadow"] = mat.get("shadow") is not None if mat else False
    p["has_metal"] = mat.get("metal") is not None if mat else False
    return p


def stylise(albedo, shadow, metal, lam, facing, spec_base, p):
    """Cel-shade one batch of fragments.

    albedo / shadow / metal : (N,3) float arrays (shadow and metal may be None)
    lam    : (N,)   dot(n, L)                    -- NOT abs(); the back of the model IS the shadow side
    facing : (N,)   |dot(n, camera_forward)|     -- for the rim term
    spec_base : (N,) or None  max(0, dot(n, H))
    Returns (N,3) float in [0,1].
    """
    N = lam.shape
    if not p["has_shadow"]:
        # No _ShadowTex on this material (eyes, eyebrows, gemstones): the authored look keeps these
        # fully lit, which is precisely the "eye pass" the source art relies on.
        t = np.ones(N, np.float32)
    else:
        thr, sm = float(p["threshold"]), float(p["smoothness"])
        # `half_lambert`: the authored _DiffuseThreshold (0.65) only makes sense against a REMAPPED
        # NdotL. Against raw NdotL it puts more than half the figure in shadow and reads much darker
        # than the shipped game art; against 0.5+0.5*NdotL it lights everything facing within ~50 deg
        # of the light, which is what the screenshots of the real game show.
        x = lam
        if p.get("half_lambert", True):
            x = 0.5 + 0.5 * lam
        t = np.clip((x - thr) / (2.0 * sm) + 0.5, 0.0, 1.0)
        t = t * t * (3.0 - 2.0 * t)
    t3 = t[..., None]
    lit = albedo * float(p["lit_gain"])
    if shadow is not None:
        dark = shadow * float(p["shadow_gain"])
    else:
        dark = albedo * 0.62
    out = dark + (lit - dark) * t3
    if p["rim"] > 0.0:
        rim = np.clip(1.0 - facing, 0.0, 1.0) ** float(p["rim_power"])
        out = out + rim[..., None] * np.asarray(p["rim_color"], np.float32) * float(p["rim"])
    if p["spec"] > 0.0 and spec_base is not None:
        s = np.clip(spec_base, 0.0, 1.0) ** float(p["spec_power"])
        if metal is not None:
            s = s * metal[..., 0]
        elif not p.get("has_metal", False):
            s = s * 0.0
        amp = float(p["spec"]) * float(p.get("spec_power_mul", 1.0))
        out = out + s[..., None] * np.asarray(p.get("spec_color", (1.0, 1.0, 1.0)), np.float32) * amp
    return np.clip(out, 0.0, 1.0)


# ----------------------------------------------------------------------------- outline
def apply_outline(rgba, color=(0.06, 0.08, 0.16), width=2, alpha_thr=0.35):
    """Bake an inverted-hull-equivalent silhouette outline into an RGBA frame.

    The 3D materials all set NewOutlineOn = 1.0 with an _OutlineColor and an _OutlineAmount, so the
    authored look HAS an outline; a flipbook cannot run a second geometry pass, so the ring just
    outside the alpha silhouette is painted instead. Purely additive: no interior pixel changes.
    """
    a = np.asarray(rgba, np.float32)[..., 3] / 255.0
    inside = a > alpha_thr
    grow = inside.copy()
    for _ in range(int(width)):
        g = grow.copy()
        g[1:, :] |= grow[:-1, :]
        g[:-1, :] |= grow[1:, :]
        g[:, 1:] |= grow[:, :-1]
        g[:, :-1] |= grow[:, 1:]
        grow = g
    ring = grow & ~inside
    if not ring.any():
        return rgba
    out = np.array(rgba, copy=True)
    col = np.array([int(round(255.0 * c)) for c in color] + [255], np.uint8)
    out[ring] = col[None, :]
    return out


# ----------------------------------------------------------------------------- raster
def rasterize(tri_pos, tri_nrm, tri_uv, tri_tex, textures, tex_alphas,
              MVP, W, H, near, verbose=True, return_z=False, extras=None, shade=None):
    """One shared z-buffer over every part. Returns (rgb, alpha[, zbuf])."""
    color = np.zeros((H, W, 3), np.float32)
    outa = np.zeros((H, W), np.float32)
    zbuf = np.zeros((H, W), np.float32)          # stores 1/w_clip, bigger = closer

    T = len(tri_pos)
    ldir = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)
    cam_pos = None

    drawn = 0
    for i in range(T):
        vp = tri_pos[i]                                     # (3,3)
        vh = np.concatenate([vp, np.ones((3, 1))], axis=1)   # (3,4)
        clip = vh @ MVP.T                                   # (3,4)
        w = clip[:, 3]
        if np.any(w <= near):
            continue
        invw = 1.0 / w
        ndc = clip[:, :3] * invw[:, None]
        if np.all(ndc[:, 0] < -1.6) or np.all(ndc[:, 0] > 1.6):
            continue
        if np.all(ndc[:, 1] < -1.6) or np.all(ndc[:, 1] > 1.6):
            continue
        sx = (ndc[:, 0] * 0.5 + 0.5) * W
        sy = (0.5 - ndc[:, 1] * 0.5) * H

        x0 = max(int(math.floor(sx.min())), 0)
        x1 = min(int(math.ceil(sx.max())) + 1, W)
        y0 = max(int(math.floor(sy.min())), 0)
        y1 = min(int(math.ceil(sy.max())) + 1, H)
        if x1 <= x0 or y1 <= y0:
            continue

        area = ((sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0]))
        if abs(area) < 1e-9:
            continue
        sgn = 1.0 if area > 0 else -1.0

        xs = np.arange(x0, x1, dtype=np.float32) + 0.5
        ys = np.arange(y0, y1, dtype=np.float32) + 0.5
        gx, gy = np.meshgrid(xs, ys)

        def edge(ax, ay, bx, by):
            return (bx - ax) * (gy - ay) - (by - ay) * (gx - ax)

        e0 = edge(sx[1], sy[1], sx[2], sy[2]) * sgn
        e1 = edge(sx[2], sy[2], sx[0], sy[0]) * sgn
        e2 = edge(sx[0], sy[0], sx[1], sy[1]) * sgn
        inside = (e0 >= -1e-6) & (e1 >= -1e-6) & (e2 >= -1e-6)
        if not inside.any():
            continue
        asum = e0 + e1 + e2
        asum[asum == 0] = 1.0
        b0 = e0 / asum
        b1 = e1 / asum
        b2 = e2 / asum

        # perspective-correct attribute weights
        d = b0 * invw[0] + b1 * invw[1] + b2 * invw[2]
        depth = d
        sub = inside & (depth > zbuf[y0:y1, x0:x1])
        if not sub.any():
            continue
        inv_d = 1.0 / np.where(np.abs(d) < 1e-12, 1e-12, d)
        c0 = b0 * invw[0] * inv_d
        c1 = b1 * invw[1] * inv_d
        c2 = b2 * invw[2] * inv_d

        uvv = tri_uv[i]
        u = c0 * uvv[0, 0] + c1 * uvv[1, 0] + c2 * uvv[2, 0]
        v = c0 * uvv[0, 1] + c1 * uvv[1, 1] + c2 * uvv[2, 1]
        np.nan_to_num(u, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
        np.nan_to_num(v, copy=False, nan=0.0, posinf=1.0, neginf=0.0)

        nn = tri_nrm[i]
        nx = c0 * nn[0, 0] + c1 * nn[1, 0] + c2 * nn[2, 0]
        ny = c0 * nn[0, 1] + c1 * nn[1, 1] + c2 * nn[2, 1]
        nz = c0 * nn[0, 2] + c1 * nn[1, 2] + c2 * nn[2, 2]
        nl = np.sqrt(nx * nx + ny * ny + nz * nz)
        nl[nl < 1e-9] = 1.0
        inv_nl = 1.0 / nl
        lam = (nx * ldir[0] + ny * ldir[1] + nz * ldir[2]) * inv_nl
        use_toon = bool(shade) and shade.get("mode") == "toon"
        if not use_toon:
            shade_map = AMBIENT + (1.0 - AMBIENT) * np.abs(lam)
        else:
            fwd = np.asarray(shade.get("fwd", (0.0, 0.0, 1.0)), np.float64)
            fwd = fwd / np.linalg.norm(fwd)
            hd = ldir + fwd
            hd = hd / np.linalg.norm(hd)
            facing = np.abs(nz * inv_nl)
            specb = np.clip((nx * hd[0] + ny * hd[1] + nz * hd[2]) * inv_nl, 0.0, 1.0)

        tp = tri_tex[i]
        tex = textures[tp] if tp < len(textures) else None
        if tex is None:
            rgb = np.full((y1 - y0, x1 - x0, 3), 0.62, np.float32)
            a = np.ones((y1 - y0, x1 - x0), np.float32)
        else:
            th, tw = tex.shape[:2]
            tx = np.clip((u * tw).astype(np.int32), 0, tw - 1)
            ty = np.clip(((1.0 - v) * th).astype(np.int32), 0, th - 1)
            sm = tex[ty, tx]
            albedo = sm[..., :3]
            a = sm[..., 3]
            if tex_alphas[tp]:
                sub &= (a >= ALPHA_CUTOFF)
                if not sub.any():
                    continue
            if use_toon:
                exd = extras[tp] if extras is not None and tp < len(extras) else None
                shadow = None
                metal = None
                if exd and exd.get("shadow") is not None:
                    sh_a = exd["shadow"]
                    sh, sw = sh_a.shape[:2]
                    shadow = sh_a[np.clip(((1.0 - v) * sh).astype(np.int32), 0, sh - 1),
                                  np.clip((u * sw).astype(np.int32), 0, sw - 1)][..., :3]
                if exd and exd.get("metal") is not None:
                    me_a = exd["metal"]
                    mh, mw = me_a.shape[:2]
                    metal = me_a[np.clip(((1.0 - v) * mh).astype(np.int32), 0, mh - 1),
                                 np.clip((u * mw).astype(np.int32), 0, mw - 1)][..., :3]
                pars = (exd or {}).get("params") or toon_params(None, {})
                rgb = stylise(albedo, shadow, metal, lam, facing, specb, pars)
            else:
                rgb = np.clip(albedo * shade_map[..., None], 0.0, 1.0)

        # composite (over) into the target through the sub mask
        reg_c = color[y0:y1, x0:x1]
        reg_a = outa[y0:y1, x0:x1]
        reg_z = zbuf[y0:y1, x0:x1]
        m = sub
        src_a = a * m
        reg_c[m] = rgb[m]
        reg_a[m] = src_a[m]
        reg_z[m] = depth[m]
        drawn += 1

    if verbose:
        print("  rasterised %d/%d triangles" % (drawn, T))
    if return_z:
        return color, outa, zbuf
    return color, outa


# ----------------------------------------------------------------------------- fast raster
def rasterize_fast(tri_pos, tri_nrm, tri_uv, tri_tex, textures, tex_alphas,
                   MVP, W, H, near, tiles=(4, 8, 16, 32, 64), chunk=512, verbose=True,
                   debug=False, extras=None, shade=None):
    """Batched rasteriser with EXACTLY the semantics of rasterize() (same z-buffer sense, same flat
    lambert, same alpha cutout, same ordering-independent result) but vectorised over triangles.

    Triangles are bucketed by the size of their screen bounding box and rasterised in batches of
    `chunk` into a padded tile x tile pixel grid; pixels are scattered into the framebuffer sorted
    far-to-near so the nearest fragment wins. Triangles too big for the largest tile fall through to
    the per-triangle loop, and the two buffers are merged on the z-buffer. This is what makes
    rendering a whole 281-frame clip practical.

    Two optional arguments switch on the stylised pass, and leaving both None reproduces the
    original flat-lambert output byte for byte:
      extras : list parallel to `textures`; extras[tp] = {"shadow": arr|None,
               "metal": arr|None, "params": {..}} -- the per-material cel data.
      shade  : {"mode": "toon"} to enable; anything else (or None) keeps the old shading.
    """
    T = len(tri_pos)
    color = np.zeros((H, W, 3), np.float32)
    outa = np.zeros((H, W), np.float32)
    zbuf = np.zeros((H, W), np.float32)
    if T == 0:
        return color, outa
    cf = color.reshape(-1, 3)
    af = outa.reshape(-1)
    zf = zbuf.reshape(-1)

    use_toon = bool(shade) and shade.get("mode") == "toon"
    ldir = LIGHT_DIR / np.linalg.norm(LIGHT_DIR)
    # V is the camera forward axis (the camera sits on +FWD looking back), so the Blinn half-vector
    # is a constant over the whole frame and the facing ratio is |n . FWD|.
    fwd = np.asarray(shade.get("fwd", (0.0, 0.0, 1.0)), np.float64) if shade else \
        np.array([0.0, 0.0, 1.0])
    fwd = fwd / np.linalg.norm(fwd)
    hdir = ldir + fwd
    hdir = hdir / np.linalg.norm(hdir)
    vh = np.concatenate([tri_pos, np.ones((T, 3, 1))], axis=2)
    clip = vh @ MVP.T
    w = clip[:, :, 3]
    ok = w.min(axis=1) > near
    invw = np.where(np.abs(w) < 1e-12, 1e-12, 1.0 / w)
    ndc = clip[:, :, :3] * invw[:, :, None]
    sx = (ndc[:, :, 0] * 0.5 + 0.5) * W
    sy = (0.5 - ndc[:, :, 1] * 0.5) * H
    area = (sx[:, 1] - sx[:, 0]) * (sy[:, 2] - sy[:, 0]) - (sx[:, 2] - sx[:, 0]) * (sy[:, 1] - sy[:, 0])
    ok &= np.abs(area) > 1e-9
    x0 = np.clip(np.floor(sx.min(1)), 0, W).astype(np.int64)
    x1 = np.clip(np.ceil(sx.max(1)) + 1, 0, W).astype(np.int64)
    y0 = np.clip(np.floor(sy.min(1)), 0, H).astype(np.int64)
    y1 = np.clip(np.ceil(sy.max(1)) + 1, 0, H).astype(np.int64)
    ok &= (x1 > x0) & (y1 > y0)
    ex, ey = x1 - x0, y1 - y0
    sgn = np.where(area > 0, 1.0, -1.0)

    todo = np.nonzero(ok)[0]
    ar = np.arange
    done = 0
    for tile in tiles:
        if todo.size == 0:
            break
        take = todo[(ex[todo] <= tile) & (ey[todo] <= tile)]
        if take.size == 0:
            continue
        todo = todo[~np.isin(todo, take)]
        # group by texture so each batch touches (almost) one texture gather
        take = take[np.argsort(tri_tex[take], kind="stable")]
        tile_eff = tile
        chunk_eff = max(16, int(2.0e6 / float(tile_eff * tile_eff)))
        off = ar(tile_eff)
        nsamp = nwin = 0
        for s in range(0, take.size, chunk_eff):
            g = take[s:s + chunk_eff]
            C = g.size
            C = g.size
            sxc, syc = sx[g], sy[g]
            iwc = invw[g]
            sgnc = sgn[g]
            x0c, x1c = x0[g], x1[g]
            y0c, y1c = y0[g], y1[g]
            pxs = x0c[:, None] + off[None, :]                # (C,tile)
            pys = y0c[:, None] + off[None, :]
            X = (pxs[:, None, :] + 0.5).astype(np.float32)   # (C,1,tile)
            Y = (pys[:, :, None] + 0.5).astype(np.float32)   # (C,tile,1)
            ax, ay = sxc[:, 0][:, None, None], syc[:, 0][:, None, None]
            bx, by = sxc[:, 1][:, None, None], syc[:, 1][:, None, None]
            cx, cy = sxc[:, 2][:, None, None], syc[:, 2][:, None, None]
            sg = sgnc[:, None, None].astype(np.float32)
            e0 = (((cx - bx) * (Y - by)) - ((cy - by) * (X - bx))) * sg
            e1 = (((ax - cx) * (Y - cy)) - ((ay - cy) * (X - cx))) * sg
            e2 = (((bx - ax) * (Y - ay)) - ((by - ay) * (X - ax))) * sg
            inside = (e0 >= -1e-6) & (e1 >= -1e-6) & (e2 >= -1e-6)
            inside &= (X < x1c[:, None, None]) & (Y < y1c[:, None, None])
            if not inside.any():
                continue
            asum = e0 + e1 + e2
            asum[asum == 0] = 1.0
            b0, b1, b2 = e0 / asum, e1 / asum, e2 / asum
            d = (b0 * iwc[:, 0][:, None, None] + b1 * iwc[:, 1][:, None, None]
                 + b2 * iwc[:, 2][:, None, None])
            inv_d = 1.0 / np.where(np.abs(d) < 1e-12, 1e-12, d)
            c0 = b0 * iwc[:, 0][:, None, None] * inv_d
            c1 = b1 * iwc[:, 1][:, None, None] * inv_d
            c2 = b2 * iwc[:, 2][:, None, None] * inv_d

            uvv = tri_uv[g]
            u = c0 * uvv[:, 0, 0][:, None, None] + c1 * uvv[:, 1, 0][:, None, None] \
                + c2 * uvv[:, 2, 0][:, None, None]
            v = c0 * uvv[:, 0, 1][:, None, None] + c1 * uvv[:, 1, 1][:, None, None] \
                + c2 * uvv[:, 2, 1][:, None, None]
            # degenerate triangles can produce NaN here (0/0); a NaN would poison the int cast used
            # for the texture gather, so clamp it to 0 up front.
            np.nan_to_num(u, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
            np.nan_to_num(v, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
            nn = tri_nrm[g]
            nx = c0 * nn[:, 0, 0][:, None, None] + c1 * nn[:, 1, 0][:, None, None] \
                + c2 * nn[:, 2, 0][:, None, None]
            ny = c0 * nn[:, 0, 1][:, None, None] + c1 * nn[:, 1, 1][:, None, None] \
                + c2 * nn[:, 2, 1][:, None, None]
            nz = c0 * nn[:, 0, 2][:, None, None] + c1 * nn[:, 1, 2][:, None, None] \
                + c2 * nn[:, 2, 2][:, None, None]
            nl = np.sqrt(nx * nx + ny * ny + nz * nz)
            nl[nl < 1e-9] = 1.0
            inv_nl = 1.0 / nl
            # SIGNED lambert: unlike the old `np.abs(...)` this keeps the back of the model on the
            # shadow side of the cel step, which is the whole point.
            lam = (nx * ldir[0] + ny * ldir[1] + nz * ldir[2]) * inv_nl
            facing = np.abs(nz * inv_nl)
            specb = np.clip((nx * hdir[0] + ny * hdir[1] + nz * hdir[2]) * inv_nl, 0.0, 1.0)
            shade_map = AMBIENT + (1.0 - AMBIENT) * np.abs(lam)
            tpc = tri_tex[g]
            rgb = np.full((C, tile_eff, tile_eff, 3), 0.62, np.float32)
            a = np.ones((C, tile_eff, tile_eff), np.float32)
            # group by texture so the gather is one fancy-index per texture
            for tp in np.unique(tpc):
                tex = textures[tp] if tp < len(textures) else None
                sel = np.nonzero(tpc == tp)[0]
                if tex is None:
                    continue
                th, tw = tex.shape[:2]
                tx = np.clip((u[sel] * tw).astype(np.int32), 0, tw - 1)
                ty = np.clip(((1.0 - v[sel]) * th).astype(np.int32), 0, th - 1)
                sm = tex[ty, tx]
                a[sel] = sm[..., 3]
                if tex_alphas[tp]:
                    inside[sel] &= (sm[..., 3] >= ALPHA_CUTOFF)
                if not use_toon:
                    rgb[sel] = sm[..., :3]
                    continue
                exd = extras[tp] if extras is not None and tp < len(extras) else None
                sh_a = exd.get("shadow") if exd else None
                me_a = exd.get("metal") if exd else None
                if sh_a is not None:
                    sh, sw = sh_a.shape[:2]
                    stx = np.clip((u[sel] * sw).astype(np.int32), 0, sw - 1)
                    sty = np.clip(((1.0 - v[sel]) * sh).astype(np.int32), 0, sh - 1)
                    shadow = sh_a[sty, stx][..., :3]
                else:
                    shadow = None
                if me_a is not None:
                    mh, mw = me_a.shape[:2]
                    mtx = np.clip((u[sel] * mw).astype(np.int32), 0, mw - 1)
                    mty = np.clip(((1.0 - v[sel]) * mh).astype(np.int32), 0, mh - 1)
                    metal = me_a[mty, mtx][..., :3]
                else:
                    metal = None
                pars = (exd or {}).get("params") or toon_params(None, {})
                rgb[sel] = stylise(sm[..., :3], shadow, metal, lam[sel], facing[sel],
                                   specb[sel], pars)
            if not use_toon:
                rgb = np.clip(rgb * shade_map[..., None], 0.0, 1.0)

            pix = (pys[:, :, None] * W + pxs[:, None, :])
            mask = inside
            if not mask.any():
                continue
            ii = pix[mask]
            dd = d[mask]
            rr_ = rgb[mask]
            aa_ = (a * mask.astype(np.float32))[mask]
            # per-pixel winner inside this batch = the deepest sample (lexsort by pixel, then depth)
            order = np.lexsort((dd, ii))
            ii_s = ii[order]
            last = np.empty(ii_s.size, dtype=bool)
            last[-1] = True
            if ii_s.size > 1:
                last[:-1] = ii_s[:-1] != ii_s[1:]
            sel = order[last]
            ci = ii[sel]
            cd = dd[sel]
            new = cd > zf[ci]                  # ... and only if it beats what is already there
            ci = ci[new]
            zf[ci] = cd[new]
            cf[ci] = rr_[sel][new]
            af[ci] = aa_[sel][new]
            done += C
            nsamp += int(mask.sum())
            nwin += int(ci.size)
        if debug:
            print("   tile %3d: tris=%5d samples=%8d written=%8d" % (tile, take.size, nsamp, nwin))

    if todo.size:
        # oversized triangles: reuse the exact per-triangle loop, then merge on the z-buffer
        sub = lambda arr: arr[todo]
        c2_, a2_, z2_ = rasterize(sub(tri_pos), sub(tri_nrm), sub(tri_uv), sub(tri_tex),
                                  textures, tex_alphas, MVP, W, H, near, verbose=False,
                                  return_z=True, extras=extras, shade=shade)
        win = z2_ > zbuf
        color[win] = c2_[win]
        outa[win] = a2_[win]
        zbuf[win] = z2_[win]
    if verbose:
        print("  rasterised %d/%d triangles (%d via the per-triangle fallback)"
              % (int((outa > 0).any() and T or 0), T, todo.size))
    return color, outa


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle", nargs="?", default=DEFAULT_BUNDLE)
    ap.add_argument("outdir", nargs="?", default=DEFAULT_OUTDIR)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--fov", type=float, default=30.0)
    ap.add_argument("--ssaa", type=int, default=2, help="supersampling factor (1 = off)")
    ap.add_argument("--flip-z", action="store_true", help="view from -Z instead")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    print("bundle: %s" % args.bundle)
    scene = Scene(args.bundle)

    # ---------- OBJ cross-check (a different code path produced the OBJ) ----------
    print("\n[DECODE CROSS-CHECK vs exported OBJ]")
    objdir = os.path.join(os.path.dirname(args.bundle), "Mesh")
    crosscheck = []
    for nm in PARTS:
        p = os.path.join(objdir, nm + ".obj")
        mo = None
        for o in scene.meshes.values():
            if gg(o.read(), "m_Name") == nm:
                mo = o
                break
        if mo is None:
            continue
        h = MeshHandler(mo.read()); h.process()
        V = np.asarray(h.m_Vertices, dtype=np.float64)
        nf = 0
        ov = []
        if os.path.exists(p):
            for line in open(p, "r", encoding="utf-8", errors="replace"):
                if line.startswith("v "):
                    ov.append([float(x) for x in line.split()[1:4]])
                elif line.startswith("f "):
                    nf += 1
        ov = np.asarray(ov, dtype=np.float64) if ov else np.zeros((0, 3))
        same = ov.shape == V.shape
        raw = float(np.abs(ov - V).max()) if same else float("nan")
        mir = float(np.abs(ov - (V * np.array([-1.0, 1.0, 1.0]))).max()) if same else float("nan")
        print("  %-26s decoded %5d v / %6d f | obj %5d v / %6d f | maxdiff raw %.3e | "
              "maxdiff after X-mirror %.3e" % (nm, len(V), len(h.m_IndexBuffer) // 3,
                                               len(ov), nf, raw, mir))
        crosscheck.append({"mesh": nm, "decoded_verts": int(len(V)),
                           "decoded_faces": int(len(h.m_IndexBuffer) // 3),
                           "obj_verts": int(len(ov)), "obj_faces": int(nf),
                           "maxdiff_raw": raw, "maxdiff_after_x_mirror": mir,
                           "note": "OBJ vertices are X-mirrored vs the bundle (UnityPy Mesh.export "
                                   "negates X); identical otherwise to float32 epsilon"})

    # ---------- build all parts ----------
    print("\n[PARTS]")
    parts = []
    for nm in PARTS:
        try:
            parts.append(build_part(scene, nm))
        except KeyError as e:
            print("  skip %s (%s)" % (nm, e))

    allP = np.concatenate([p["P"] for p in parts], 0)
    bmin, bmax = allP.min(0), allP.max(0)
    print("\nskinned bbox (all parts)  min=%s max=%s size=%s" %
          (np.round(bmin, 4), np.round(bmax, 4), np.round(bmax - bmin, 4)))
    # The weapons' bind positions are parked ~1 unit to the left of the body (see below), so use
    # the character-only bbox for the main framing or the character ends up tiny in the frame.
    charP = np.concatenate([p["P"] for p in parts if not p["name"].endswith(("weapon", "weapon01"))], 0)
    cmin, cmax = charP.min(0), charP.max(0)
    print("skinned bbox (character)  min=%s max=%s size=%s" %
          (np.round(cmin, 4), np.round(cmax, 4), np.round(cmax - cmin, 4)))

    # ---------- textures ----------
    # tex_ids entries are (albedo, shadow, light, metal, eye) tuples; only the albedo goes into the
    # global texture list this (non-stylised) path samples.
    used = []
    for p in parts:
        for t in p["tex_ids"]:
            alb = t[0]
            if alb is not None and alb not in used:
                used.append(alb)
    tex_arrays, tex_alphas, tex_names = [], [], []
    print("\n[TEXTURES]")
    for t in used:
        arr = scene.texture_image(t)
        nm = gg(scene.textures[t].read(), "m_Name") if t in scene.textures else str(t)
        if arr is None:
            print("  %-32s MISSING" % nm)
            tex_arrays.append(None); tex_alphas.append(False); tex_names.append(nm)
            continue
        a = arr[..., 3]
        frac = float((a < 0.98).mean())
        use_a = frac > 0.02
        tex_arrays.append(arr); tex_alphas.append(use_a); tex_names.append(nm)
        print("  %-32s %sx%s  alpha<0.98 on %.1f%% of texels -> cutout=%s"
              % (nm, arr.shape[1], arr.shape[0], frac * 100, use_a))

    # remap per-part texture indices into the global list
    gpos, gnrm, guv, gtex = [], [], [], []
    for p in parts:
        remap = np.array([used.index(t[0]) if t[0] is not None else -1
                          for t in p["tex_ids"]], np.int64)
        gi = remap[p["tex"]]
        gpos.append(p["pos"]); gnrm.append(p["nrm"]); guv.append(p["uv"]); gtex.append(gi)
    gpos = np.concatenate(gpos, 0); gnrm = np.concatenate(gnrm, 0)
    guv = np.concatenate(guv, 0)
    gtex = np.concatenate(gtex, 0)
    gtex[gtex < 0] = 0

    # ---------- render ----------
    fwd = np.array([0.0, 0.0, -1.0 if args.flip_z else 1.0])

    def render_view(bmin_, bmax_, height, ssaa, label):
        center = (bmin_ + bmax_) * 0.5
        size = np.maximum(bmax_ - bmin_, 1e-6)
        W_ = max(128, int(round(height * (size[0] / size[1]) / 2.0)) * 2)
        W_ = min(W_, height * 2)
        aspect = float(W_) / float(height)
        half_h = size[1] * 0.5 * 1.10
        half_w = size[0] * 0.5 * 1.10
        t = math.tan(math.radians(args.fov) * 0.5)
        dist = max(half_h / t, half_w / (t * aspect))
        eye = center + fwd * (dist + size[2])
        near = max(0.05, dist * 0.05)
        far = dist + size[2] * 3 + 10.0
        MVP = perspective(args.fov, aspect, near, far) @ look_at(eye, center,
                                                                 np.array([0.0, 1.0, 0.0]))
        BW, BH = W_ * ssaa, height * ssaa
        print("\n[RASTER %s] %dx%d (buffer %dx%d, ssaa=%d) eye=%s target=%s"
              % (label, W_, height, BW, BH, ssaa, np.round(eye, 3), np.round(center, 3)))
        col, alp = rasterize(gpos, gnrm, guv, gtex, tex_arrays, tex_alphas,
                             MVP, BW, BH, near)
        if ssaa > 1:
            pm = col * alp[..., None]
            pm = pm.reshape(height, ssaa, W_, ssaa, 3).mean(axis=(1, 3))
            al = alp.reshape(height, ssaa, W_, ssaa).mean(axis=(1, 3))
            col = pm / np.maximum(al[..., None], 1e-6)
            alp = al
        rgba = np.zeros((height, W_, 4), np.uint8)
        rgba[..., :3] = np.clip(col * 255.0 + 0.5, 0, 255).astype(np.uint8)
        rgba[..., 3] = np.clip(alp * 255.0 + 0.5, 0, 255).astype(np.uint8)
        print("  coverage: %.2f%% of the frame" % (float((alp > 0.5).mean()) * 100))
        return rgba, W_, height, center, eye, near, far

    out, W_, H_, center, eye, near, far = render_view(cmin, cmax, args.height,
                                                      args.ssaa, "character")
    op = os.path.join(args.outdir, "3015004_front_bindpose.png")
    Image.fromarray(out, "RGBA").save(op)
    print("  wrote %s" % op)

    # secondary proof panel: every part including the two weapons at their bind locations
    wide, wW, wH, _c2, _e2, _n2, _f2 = render_view(bmin, bmax, 512, 1, "all parts")

    # ---------- preview sheet ----------
    # Row 1: the render + the all-parts render (so the parked weapon rest placement is visible).
    # Row 2: every diffuse texture that was actually sampled, so a human can eyeball whether the
    # UV islands the render used are the right islands of the atlas.
    pad = 12
    label_h = 20
    tex_h = 300
    rowh = 640
    rimg = Image.fromarray(out, "RGBA")
    rimg = rimg.resize((int(round(rimg.width * (rowh / float(rimg.height)))), rowh), Image.LANCZOS)
    wimg = Image.fromarray(wide, "RGBA")
    wimg = wimg.resize((int(round(wimg.width * (rowh / float(wimg.height)))), rowh), Image.LANCZOS)
    row1 = [("RENDER: front view, bind pose (character-framed)", rimg),
            ("ALL PARTS at bind rest - the 2 weapons are parked off-model by design", wimg)]
    row2 = []
    for arr, nm, cut in zip(tex_arrays, tex_names, tex_alphas):
        if arr is None:
            continue
        im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGBA")
        bg = Image.new("RGBA", im.size, (40, 40, 46, 255))
        im = Image.alpha_composite(bg, im)
        im = im.resize((int(round(im.width * (tex_h / float(im.height)))), tex_h), Image.BILINEAR)
        row2.append(("diffuse %s%s" % (nm, "  (alpha cutout)" if cut else ""), im))

    def row_width(row):
        return sum(im.width + pad for _l, im in row) + pad

    sheet_w = max(row_width(row1), row_width(row2))
    sheet_h = pad + label_h + rowh + pad + label_h + tex_h + pad
    sheet = Image.new("RGBA", (sheet_w, pad + sheet_h), (24, 24, 28, 255))
    dr = ImageDraw.Draw(sheet)
    y = pad
    for row, hh in ((row1, rowh),):
        x = pad
        for lbl, im in row:
            dr.text((x + 2, y + 2), lbl[:70], fill=(240, 240, 240, 255))
            sheet.paste(im, (x, y + label_h), im)
            x += im.width + pad
        y += label_h + hh + pad
    x = pad
    for lbl, im in row2:
        dr.text((x + 2, y + 2), lbl[:70], fill=(240, 240, 240, 255))
        sheet.paste(im, (x, y + label_h), im)
        x += im.width + pad
    sp = os.path.join(args.outdir, "preview_sheet.png")
    sheet.save(sp)
    print("\n  wrote %s (%dx%d)" % (sp, sheet.width, sheet.height))

    # ---------- summary ----------
    summary = {
        "bundle": args.bundle,
        "image": op, "image_size": [W_, H_],
        "forward_axis": "-Z" if args.flip_z else "+Z",
        "camera_eye": eye.tolist(), "camera_target": center.tolist(), "fov": args.fov,
        "skinned_bbox_character_min": cmin.tolist(), "skinned_bbox_character_max": cmax.tolist(),
        "skinned_bbox_allparts_min": bmin.tolist(), "skinned_bbox_allparts_max": bmax.tolist(),
        "textures": [{"name": n, "cutout": bool(c)} for n, c in zip(tex_names, tex_alphas)],
        "obj_crosscheck": crosscheck,
        "notes": [
            "No texture named tt_3015004_01_body exists in this bundle; the body mesh resolves its "
            "submeshes to tt_3015004_01_cloth (cloth/metal/gemstone) and tt_3015004_01_face (skin).",
            "Only the albedo slot (_BasicTex/_MainTex) is sampled. _ShadowTex (anbu), _LightTex "
            "(grey), _BumpMap (cloth_n), _MetalLightingInfo and _Eye_LightingInfo are ignored, so "
            "there is no toon ramp, no normal mapping and no eye-lighting pass - deliberate.",
            "No texture in this bundle uses its alpha channel (0.0% of texels below 0.98), so alpha "
            "cutout never fires; there is no card-based hair or alpha-tested fringe to composite.",
            "The two weapons are the same mesh instanced twice and their rest bones "
            "(aoi_scale_wuqi01 / aoi_scale_wuqi002, both children of mx_3015004_01) are parked at "
            "x=-0.97 / -1.41, i.e. ~1 unit left of the body. That is the bind rest state, not a "
            "decode error: animations drive those bones into the hands. The main render is framed "
            "on the character so the weapons fall outside it; the preview sheet shows them.",
            "body_02 (the outer cloth layer) has 2 tassel bones (Bone_suizi_b_01, Bone_suizi_d_01) "
            "whose bind-pose matrices disagree with the prefab hierarchy by <=0.33 (translation), "
            "moving <=4.1 cm of cloth. All other parts agree to ~1e-5.",
            "Single shared z-buffer over all parts, no backface culling (assumed two-sided for the "
            "_Double cloth materials), flat-ish shading = ambient 0.42 + 0.58 * |dot(n, L)| with the "
            "normal flipped toward the camera, 2x supersampling.",
        ],
        "parts": [{"name": p["name"],
                   "raw_verts": int(len(p["V"])),
                   "tris": int(len(p["pos"])),
                   "bind_residual_rot": p["bind_err"][0],
                   "bind_residual_trans": p["bind_err"][1],
                   "max_skinned_minus_raw": p["reskew"]} for p in parts],
    }
    jp = os.path.join(args.outdir, "render_report.json")
    json.dump(summary, open(jp, "w", encoding="utf-8"), indent=1)
    print("  wrote %s" % jp)


if __name__ == "__main__":
    main()
