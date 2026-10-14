# model-probe-r5.py -- decisive forward-axis test: toe bones point forward in every humanoid rig.
import os
import numpy as np
import UnityPy

BUNDLE = r"D:\桌面\sts2mod\.tools\out\export\pet__3015004_prefab\pet__3015004_prefab.unity3d"


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
trs = {}
name = {}
for o in env.objects:
    if o.type.name in ("Transform", "RectTransform"):
        d = o.read()
        trs[o.path_id] = d
        go = g(d, "m_GameObject")
        name[o.path_id] = g(go.read(), "m_Name") if go else "?"


def qmat(q):
    x, y, z, w = q.x, q.y, q.z, q.w
    n = (x * x + y * y + z * z + w * w) ** 0.5
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def world(tid, cache={}):
    if tid in cache:
        return cache[tid]
    d = trs[tid]
    lp = g(d, "m_LocalPosition")
    lq = g(d, "m_LocalRotation")
    ls = g(d, "m_LocalScale")
    M = np.eye(4)
    R = qmat(lq)
    M[:3, :3] = R * np.array([ls.x, ls.y, ls.z])[None, :]
    M[:3, 3] = [lp.x, lp.y, lp.z]
    f = pid(g(d, "m_Father"))
    if f in trs:
        M = world(f) @ M
    cache[tid] = M
    return M


print("=== bone names containing Toe/Foot/Ankle/Head/Nose/Hand ===")
for tid, d in trs.items():
    n = name[tid]
    if any(k in n for k in ("Toe", "Foot", "Ankle")):
        M = world(tid)
        print("  %-28s local=%s world=%s" % (n, np.round([g(d, 'm_LocalPosition').x, g(d, 'm_LocalPosition').y, g(d, 'm_LocalPosition').z], 4), np.round(M[:3, 3], 4)))

print("\n=== all bone-like names (Bip001 / Bone) ===")
for tid, d in sorted(trs.items(), key=lambda kv: name[kv[0]]):
    n = name[tid]
    if n.startswith("Bip001") or n.startswith("Bone"):
        M = world(tid)
        print("  %-30s local=%s world=%s" % (n, np.round([g(d, 'm_LocalPosition').x, g(d, 'm_LocalPosition').y, g(d, 'm_LocalPosition').z], 4), np.round(M[:3, 3], 4)))

print("\n=== top-level GO children of root ===")
roots = [k for k in trs if pid(g(trs[k], "m_Father")) not in trs]
for r in roots:
    print("  root:", name[r])
    for c in (g(trs[r], "m_Children") or []):
        cp = pid(c)
        print("     child:", name.get(cp), np.round(world(cp)[:3, 3], 4) if cp in trs else "?")
