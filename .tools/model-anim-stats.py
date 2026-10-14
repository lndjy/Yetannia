# model-anim-stats.py -- produce the numeric evidence file for MOTION_REPORT.md.
#
# Writes (pure Python file IO, never a PowerShell text round-trip):
#   .tools/out/render/anim/motion_stats.json   machine readable, all 11 clips
#   .tools/out/render/anim/motion_stats.txt    the same, human readable
#
# usage: python .tools/model-anim-stats.py
import importlib.util
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def _imp(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rr = _imp("model_anim_render", os.path.join(HERE, "model-anim-render.py"))
mr, ma = rr.mr, rr.ma
OUT = os.path.join(HERE, "out", "render", "anim")

clips, hash_to_tid, tid_to_chain = ma.load_clips(rr.BUNDLE)
rig = rr.Rig(rr.BUNDLE)
scene = rig.scene

REST = {}
for o in scene.env.objects:
    if o.type.name in ("Transform", "RectTransform"):
        d = o.read()
        lp, lr, ls = (mr.gg(d, "m_LocalPosition"), mr.gg(d, "m_LocalRotation"),
                      mr.gg(d, "m_LocalScale"))
        REST[o.path_id] = (np.array([lp.x, lp.y, lp.z]) if lp else np.zeros(3),
                           np.array([lr.x, lr.y, lr.z, lr.w]) if lr else np.array([0.0, 0, 0, 1]),
                           np.array([ls.x, ls.y, ls.z]) if ls else np.ones(3))


def qang(a, b):
    a = a / max(float(np.linalg.norm(a)), 1e-12)
    b = b / max(float(np.linalg.norm(b)), 1e-12)
    return float(np.degrees(2.0 * np.arccos(min(1.0, abs(float(np.dot(a, b)))))))


def short(tid):
    return (tid_to_chain.get(tid, "?") or "?").split("/")[-1]


ATTRS = ((1, "localPosition", "pos"), (2, "localRotation", "rot"), (3, "localScale", "scl"))


def clip_stats(name):
    cl = clips[name]
    n = cl.n
    out = {
        "frames": cl.frame_count, "fps": cl.rate, "duration_s": round(cl.stop_time, 4),
        "paths": n, "max_quat_norm_err": cl.rot_norm_err,
        "layout": {"n": n,
                   "streamed": [cl.Ps, cl.Rs, cl.Ss],
                   "dense": [cl.Pd, cl.Rd, cl.Sd],
                   "constant": [cl.Pc, cl.Rc, cl.Sc],
                   "checks": {
                       "dense_floats": [3 * cl.Pd + 4 * cl.Rd + 3 * cl.Sd, cl.curve_count],
                       "streamed_curves": [3 * cl.Ps + 4 * cl.Rs + 3 * cl.Ss,
                                           cl.streamed_curve_count],
                       "constant_floats": [3 * cl.Pc + 4 * cl.Rc + 3 * cl.Sc, len(cl.constant)],
                       "width_sum_per_attr": [cl.Ps + cl.Pd + cl.Pc, cl.Rs + cl.Rd + cl.Rc,
                                              cl.Ss + cl.Sd + cl.Sc]}},
        "channels": {}, "frame0_vs_rest": {}, "driven": {},
    }
    # ---- frame 0 (and any frame) vs the prefab rest pose, per bone
    for a, label, key in ATTRS:
        arr = getattr(cl, key)
        tids = cl.attr_tid[a]
        tbl = np.stack([REST[t][{1: 0, 2: 1, 3: 2}[a]] for t in tids])
        if key == "rot":
            e0 = np.array([qang(arr[0, i], tbl[i]) for i in range(n)])
            eany = np.array([max(qang(arr[f, i], tbl[i]) for f in range(cl.frame_count))
                             for i in range(n)])
            unit = "deg"
        else:
            e0 = np.abs(arr[0] - tbl).max(1)
            eany = np.abs(arr - tbl[None]).max(2).max(0)
            unit = "m" if key == "pos" else "x"
        worst = np.argsort(-e0)[:5]
        out["frame0_vs_rest"][label] = {
            "unit": unit, "median": float(np.median(e0)), "p95": float(np.percentile(e0, 95)),
            "max": float(e0.max()), "max_over_all_frames": float(eany.max()),
            "worst_bones": [{"bone": short(tids[i]), "err": float(e0[i])} for i in worst],
        }
    # ---- which channels actually move
    dp = np.abs(cl.pos - cl.pos[0][None]).max(2)                  # (F, n)
    ds = np.abs(cl.scl - cl.scl[0][None]).max(2)
    drot = np.array([[qang(cl.rot[f, i], cl.rot[0, i]) for i in range(n)]
                     for f in range(cl.frame_count)])
    out["driven"] = {
        "rotation_bones_over_1deg": int((drot.max(0) > 1).sum()),
        "rotation_bones_over_5deg": int((drot.max(0) > 5).sum()),
        "rotation_bones_over_15deg": int((drot.max(0) > 15).sum()),
        "position_bones_over_1mm": int((dp.max(0) > 1e-3).sum()),
        "position_bones_over_1cm": int((dp.max(0) > 1e-2).sum()),
        "scale_bones_over_1e-3": int((ds.max(0) > 1e-3).sum()),
        "max_bone_rotation_deg": float(drot.max()),
        "max_bone_position_m": float(dp.max()),
        "max_bone_scale_abs": float(ds.max()),
        "rot_storage_split": {"streamed": cl.Rs, "dense": cl.Rd, "constant": cl.Rc},
        "pos_storage_split": {"streamed": cl.Ps, "dense": cl.Pd, "constant": cl.Pc},
        "scl_storage_split": {"streamed": cl.Ss, "dense": cl.Sd, "constant": cl.Sc},
    }
    top = np.argsort(-drot.max(0))[:12]
    out["top_moving_bones"] = [{"bone": short(cl.attr_tid[2][i]),
                               "max_rot_deg": float(drot[:, i].max())} for i in top]
    # ---- world yaw of the pelvis: turntable or not?
    pel = None
    for t in cl.attr_tid[2]:
        if (tid_to_chain.get(t) or "").endswith("Bip001 Pelvis"):
            pel = t
            break
    if pel:
        yaw = []
        for f in range(cl.frame_count):
            scene.reset_pose(cl.pose(f))
            R = scene.world_matrix(pel)[:3, :3]
            fv = R @ np.array([0.0, 0.0, 1.0])
            yaw.append(float(np.degrees(np.arctan2(fv[0], fv[2]))))
        yaw = np.array(yaw)
        unw = np.rad2deg(np.unwrap(np.deg2rad(yaw)))
        out["pelvis_world_yaw_deg"] = {
            "frame0": float(yaw[0]), "min": float(yaw.min()), "max": float(yaw.max()),
            "peak_to_peak": float(yaw.max() - yaw.min()),
            "unwrapped_total_travel": float(abs(unw[-1] - unw[0])),
            "monotonic": bool(np.all(np.diff(unw) > -1e-9)),
            "sample": [round(float(yaw[f]), 2) for f in range(0, cl.frame_count,
                                                             max(1, cl.frame_count // 10))],
        }
        # ---- limb travel measured in the PELVIS frame (removes any whole-body motion)
        watch = {}
        for key in ("Bip001 L Hand", "Bip001 R Hand", "Bip001 L Foot", "Bip001 R Foot",
                    "Bip001 L UpperArm", "Bip001 R UpperArm", "aoi_scale_wuqi01"):
            for t, ch in tid_to_chain.items():
                if (ch or "").endswith(key):
                    watch[key] = t
                    break
        trav = {}
        traj = {k: [] for k in watch}
        for f in range(cl.frame_count):
            scene.reset_pose(cl.pose(f))
            Pinv = np.linalg.inv(scene.world_matrix(pel))
            for k, t in watch.items():
                traj[k].append((Pinv @ np.append(scene.world_matrix(t)[:3, 3], 1.0))[:3])
        for k, v in traj.items():
            a = np.array(v)
            trav[k] = {"peak_to_peak_m": (a.max(0) - a.min(0)).round(4).tolist(),
                       "path_length_m": round(float(np.linalg.norm(np.diff(a, axis=0), axis=1).sum()), 4)}
        out["limb_travel_in_pelvis_frame"] = trav
    return out


allst = {}
lines = []
for nm in sorted(clips):
    st = clip_stats(nm)
    allst[nm] = st
    lay = st["layout"]
    print("stats: %s" % nm)
    lines.append("=" * 96)
    lines.append("%s   %d frames @ %.0f fps  = %.3f s   (%d paths)" %
                 (nm, st["frames"], st["fps"], st["duration_s"], st["paths"]))
    lines.append("  layout  streamed pos/rot/scl = %s   dense = %s   constant = %s" %
                 (lay["streamed"], lay["dense"], lay["constant"]))
    lines.append("  identity checks (computed vs header): %s" % json.dumps(lay["checks"]))
    lines.append("  max |q|-1 over every frame/bone = %.2e" % st["max_quat_norm_err"])
    for a, label, _k in ATTRS:
        d = st["frame0_vs_rest"][label]
        lines.append("  frame0 vs REST %-14s median %.3e p95 %.3e max %.3e (all frames %.3e) "
                     "worst: %s" % (label, d["median"], d["p95"], d["max"],
                                    d["max_over_all_frames"],
                                    ", ".join("%s %.3g" % (w["bone"], w["err"])
                                              for w in d["worst_bones"][:3])))
    dr = st["driven"]
    lines.append("  driven: rot >1deg %d, >5deg %d, >15deg %d (max %.1f deg) | pos >1cm %d "
                 "(max %.3f m) | scale >1e-3 %d (max %.4f)" %
                 (dr["rotation_bones_over_1deg"], dr["rotation_bones_over_5deg"],
                  dr["rotation_bones_over_15deg"], dr["max_bone_rotation_deg"],
                  dr["position_bones_over_1cm"], dr["max_bone_position_m"],
                  dr["scale_bones_over_1e-3"], dr["max_bone_scale_abs"]))
    lines.append("  top movers: %s" % ", ".join("%s %.1f" % (t["bone"], t["max_rot_deg"])
                                               for t in st["top_moving_bones"][:8]))
    y = st.get("pelvis_world_yaw_deg")
    if y:
        lines.append("  pelvis world yaw: f0 %.2f, range [%.2f,%.2f] p2p %.2f deg, unwrapped "
                     "travel %.2f deg, monotonic(turntable)=%s" %
                     (y["frame0"], y["min"], y["max"], y["peak_to_peak"],
                      y["unwrapped_total_travel"], y["monotonic"]))
        lines.append("  yaw samples: %s" % y["sample"])
    lt = st.get("limb_travel_in_pelvis_frame")
    if lt:
        lines.append("  limb travel in the pelvis frame (peak-to-peak xyz m / path m):")
        for k, v in lt.items():
            lines.append("      %-22s %s   path %.4f" % (k, v["peak_to_peak_m"], v["path_length_m"]))

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "motion_stats.json"), "w", encoding="utf-8") as fh:
    json.dump(allst, fh, indent=1)
with open(os.path.join(OUT, "motion_stats.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("wrote %s" % os.path.join(OUT, "motion_stats.json"))
print("wrote %s" % os.path.join(OUT, "motion_stats.txt"))
