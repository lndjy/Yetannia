# model-export-hierarchy.py -- dump the GameObject/Transform tree (the skeleton) for a decrypted bundle.
#
# UnityPy's Mesh.export() writes static OBJ only: no bones, no skin weights, so the rig is lost.
# The bone hierarchy lives in the Transform components, so record it separately. This does not make
# a rigged FBX, but it preserves the skeleton + rest-pose transforms that a converter would need.
#
# usage: python .tools/model-export-hierarchy.py <decrypted.unity3d> [out.json]
import json
import os
import sys

import UnityPy


def pid(x):
    """PPtr-ish -> path id. GameObject.m_Component holds ComponentPair wrappers."""
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


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(src), "hierarchy.json")
    env = UnityPy.load(src)

    go, tr = {}, {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            d = obj.read()
            go[obj.path_id] = {"name": getattr(d, "m_Name", None),
                               "components": [pid(c) for c in (getattr(d, "m_Component", []) or [])],
                               "layer": getattr(d, "m_Layer", None),
                               "active": getattr(d, "m_IsActive", None)}
        elif obj.type.name in ("Transform", "RectTransform"):
            d = obj.read()
            tr[obj.path_id] = {
                "type": obj.type.name,
                "name": getattr(d, "m_Name", None),
                "game_object": pid(getattr(d, "m_GameObject", None)),
                "father": pid(getattr(d, "m_Father", None)),
                "children": [pid(c) for c in (getattr(d, "m_Children", []) or [])],
                "local_position": getattr(d, "m_LocalPosition", None) and
                {k: getattr(d.m_LocalPosition, k) for k in ("x", "y", "z")},
                "local_rotation": getattr(d, "m_LocalRotation", None) and
                {k: getattr(d.m_LocalRotation, k) for k in ("x", "y", "z", "w")},
                "local_scale": getattr(d, "m_LocalScale", None) and
                {k: getattr(d.m_LocalScale, k) for k in ("x", "y", "z")},
            }

    roots = [tid for tid, t in tr.items() if not t["father"] or t["father"] not in tr]

    def walk(tid, depth, out):
        t = tr.get(tid)
        if t is None:
            return
        g = go.get(t["game_object"], {})
        out.append({"depth": depth, "transform": tid, "game_object": t["game_object"],
                    "name": g.get("name") or t.get("name"),
                    "local_position": t["local_position"]})
        for c in t["children"]:
            walk(c, depth + 1, out)

    flat = {}
    for r in sorted(roots, key=lambda i: (tr[i]["name"] or "")):
        rows = []
        walk(r, 0, rows)
        flat[str(tr[r]["name"])] = rows

    skinned = []
    for obj in env.objects:
        if obj.type.name == "SkinnedMeshRenderer":
            d = obj.read()
            goid = pid(getattr(d, "m_GameObject", None))
            skinned.append({"game_object": goid,
                            "bones": len(getattr(d, "m_Bones", []) or []),
                            "bone_path_ids": [pid(b) for b in (getattr(d, "m_Bones", []) or [])]})

    data = {"source": os.path.basename(src), "transform_count": len(tr),
            "gameobject_count": len(go), "root_count": len(roots),
            "skinned_mesh_renderers": skinned, "hierarchies": flat}
    json.dump(data, open(dst, "w", encoding="utf-8"), indent=1, default=str)
    print(f"{os.path.basename(src)}: {len(tr)} transforms, {len(roots)} roots, "
          f"{len(skinned)} skinned renderers -> {dst}")
    for s in skinned:
        print(f"   skinned renderer on GO {s['game_object']}: {s['bones']} bones")


if __name__ == "__main__":
    main()
