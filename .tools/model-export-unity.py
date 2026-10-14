# model-export.py -- decrypt, load and export the qiannian-zhilv model bundles.
#
# Cipher (proven by the .manifest CRC on 10/11 bundles):
#     plaintext = raw[:1000] ^ 0x7b  +  raw[1000:]
# Everything after byte 1000 is stored unencrypted; only the header / first block are obfuscated.
#
# Exports per bundle: Mesh -> .obj, Texture2D -> .png, AnimationClip -> typetree .json,
# plus inventory.json describing every object (names, vertex counts, texture sizes, script classes).
#
# usage: python .tools/model-export.py [root] [--meshes-only]
import glob
import json
import os
import sys

import UnityPy

KEY = 0x7B
PREFIX = 1000
ROOT = r"D:\桌面\sts2mod\model"
OUT = r"D:\桌面\sts2mod\.tools\out\export"


def decrypt(raw, n=PREFIX):
    return bytes(b ^ KEY for b in raw[:n]) + raw[n:]


def safe(name, fallback):
    s = "".join(c if c.isalnum() or c in "._-" else "_" for c in (name or ""))
    return s or fallback


def describe(obj):
    t = obj.type.name
    try:
        d = obj.read()
    except Exception as exc:
        return {"type": t, "path_id": obj.path_id, "error": f"{type(exc).__name__}: {exc}"}
    rec = {"type": t, "path_id": obj.path_id}
    try:
        if t == "Mesh":
            rec.update(name=getattr(d, "m_Name", None),
                       vertices=len(getattr(d, "m_Vertices", []) or []),
                       submeshes=len(getattr(d, "m_SubMeshes", []) or []),
                       bind_pose=len(getattr(d, "m_BindPose", []) or []),
                       has_skin=bool(getattr(d, "m_Skin", None)))
        elif t == "Texture2D":
            rec.update(name=getattr(d, "m_Name", None),
                       width=getattr(d, "m_Width", None),
                       height=getattr(d, "m_Height", None),
                       format=getattr(getattr(d, "m_TextureFormat", None), "name", None))
        elif t == "AnimationClip":
            rec.update(name=getattr(d, "m_Name", None),
                       legacy=getattr(d, "m_Legacy", None),
                       sample_rate=getattr(d, "m_SampleRate", None))
        elif t == "MonoScript":
            rec.update(name=getattr(d, "m_Name", None),
                       class_name=getattr(d, "m_ClassName", None),
                       namespace=getattr(d, "m_Namespace", None),
                       assembly=getattr(d, "m_AssemblyName", None))
        elif t in ("GameObject", "Transform", "Material", "AnimatorController",
                   "SkinnedMeshRenderer", "Animator", "ParticleSystem", "AssetBundle",
                   "MeshRenderer", "MeshFilter", "BoxCollider"):
            rec.update(name=getattr(d, "m_Name", None))
            if t == "SkinnedMeshRenderer":
                rec["bones"] = len(getattr(d, "m_Bones", []) or [])
                rec["mesh"] = getattr(getattr(d, "m_Mesh", None), "m_PathID", None)
            if t == "Material":
                rec["shader"] = getattr(getattr(d, "m_Shader", None), "m_PathID", None)
        else:
            rec["name"] = getattr(d, "m_Name", None)
    except Exception as exc:
        rec["describe_error"] = f"{type(exc).__name__}: {exc}"
    return rec


def export_bundle(path, root, meshes_only=False):
    # keep the bundle's relative directory in the output path: pet/hx/301500402_prefab and
    # pet/301500402_prefab are different bundles that share a basename.
    rel = os.path.relpath(path, root)
    stem = os.path.splitext(rel)[0].replace(os.sep, "__")
    dest = os.path.join(OUT, stem)
    raw = open(path, "rb").read()
    dec = decrypt(raw)
    assert dec[:7] == b"UnityFS"
    os.makedirs(dest, exist_ok=True)
    tmp = os.path.join(dest, stem + ".unity3d")
    open(tmp, "wb").write(dec)
    env = UnityPy.load(tmp)

    inv, counts = [], {}
    n_mesh = n_tex = n_clip = n_fail = 0
    for obj in env.objects:
        t = obj.type.name
        counts[t] = counts.get(t, 0) + 1
        rec = describe(obj)
        inv.append(rec)
        try:
            if t == "Mesh":
                d = obj.read()
                text = d.export()
                fp = os.path.join(dest, "Mesh",
                                  safe(getattr(d, "m_Name", None), f"mesh_{obj.path_id}") + ".obj")
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                open(fp, "w", encoding="utf-8").write(text)
                n_mesh += 1
            elif t == "Texture2D" and not meshes_only:
                d = obj.read()
                img = d.image
                fp = os.path.join(dest, "Texture2D",
                                  safe(getattr(d, "m_Name", None), f"tex_{obj.path_id}") + ".png")
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                img.save(fp)
                n_tex += 1
            elif t == "AnimationClip" and not meshes_only:
                tree = obj.read_typetree()
                fp = os.path.join(dest, "AnimationClip",
                                  safe(getattr(obj.read(), "m_Name", None),
                                       f"clip_{obj.path_id}") + ".json")
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                json.dump(tree, open(fp, "w", encoding="utf-8"), default=str)
                n_clip += 1
        except Exception as exc:
            n_fail += 1
            inv[-1]["export_error"] = f"{type(exc).__name__}: {exc}"

    json.dump({"file": os.path.basename(path), "relative": rel, "bytes": len(raw),
               "counts": counts, "objects": inv},
              open(os.path.join(dest, "inventory.json"), "w", encoding="utf-8"),
              indent=1, default=str)
    print(f"{stem:36s} {len(raw):>9}B  objects={len(inv):>4}  "
          f"mesh={n_mesh} tex={n_tex} clip={n_clip} fail={n_fail}")
    return counts, inv


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    meshes_only = "--meshes-only" in sys.argv
    root = args[0] if args else ROOT
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(root, "**", "*.data"), recursive=True))
    allc = {}
    for p in files:
        try:
            counts, _ = export_bundle(p, root, meshes_only)
            for k, v in counts.items():
                allc[k] = allc.get(k, 0) + v
        except Exception as exc:
            print(f"{os.path.basename(p):36s} FAILED {type(exc).__name__}: {exc}")
    print("\n=== object type totals across all bundles ===")
    for k, v in sorted(allc.items(), key=lambda kv: -kv[1]):
        print(f"  {k:26s} {v}")


if __name__ == "__main__":
    main()
