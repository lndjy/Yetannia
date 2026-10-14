# model-anim-diag.py -- hard numbers about WHAT is actually driven by a decoded clip.
#
# Motivated by a specific worry: the 6-frame zd_daiji contact sheet looks like the character simply
# yaws a full turn while the limbs stay put. A monotonic whole-body yaw is also the classic signature
# of a decode bug (wrong quaternion component order, or only the root rotation taking effect), so
# this script answers the discriminating questions with numbers instead of adjectives:
#
#   1. how many of the n bones have a NON-CONSTANT local rotation over the clip (>1 deg, >5 deg)?
#   2. the per-bone local rotation delta frame0 -> frame15, top 10, in DEGREES
#   3. is the root/pelvis WORLD yaw monotonic (a turntable) and how many degrees per frame?
#   4. for zd_jn_01 (a skill, which must move the arms): do the LIMBS move relative to the pelvis?
#   5. what is the evidence for the quaternion component order (x,y,z,w)?
#
# usage: python .tools/model-anim-diag.py [clip ...]
import importlib.util
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

clips, hash_to_tid, tid_to_chain = ma.load_clips(rr.BUNDLE)
rig = rr.Rig(rr.BUNDLE)
scene = rig.scene

# rest pose per transform
REST = {}
for o in scene.env.objects:
    if o.type.name in ("Transform", "RectTransform"):
        d = o.read()
        lp, lr, ls = (mr.gg(d, "m_LocalPosition"), mr.gg(d, "m_LocalRotation"),
                      mr.gg(d, "m_LocalScale"))
        REST[o.path_id] = (
            np.array([lp.x, lp.y, lp.z]) if lp else np.zeros(3),
            np.array([lr.x, lr.y, lr.z, lr.w]) if lr else np.array([0.0, 0, 0, 1]),
            np.array([ls.x, ls.y, ls.z]) if ls else np.ones(3))


def qang(a, b):
    """angle in degrees between two quaternions (xyzw), sign-agnostic."""
    a = a / max(np.linalg.norm(a), 1e-12)
    b = b / max(np.linalg.norm(b), 1e-12)
    d = abs(float(np.dot(a, b)))
    return float(np.degrees(2.0 * np.arccos(min(1.0, d))))


def yaw_of(R):
    f = R @ np.array([0.0, 0.0, 1.0])
    return float(np.degrees(np.arctan2(f[0], f[2])))


def report(name, f_ref=15):
    cl = clips[name]
    print("=" * 100)
    print("%s   frames=%d  %.3fs" % (name, cl.frame_count, cl.stop_time))
    n = cl.n
    tids = cl.attr_tid

    # ---- 1/2/5: local rotation deltas
    rot = cl.rot                                   # (F, n, 4)
    ref = rot[0]
    fr = min(f_ref, cl.frame_count - 1)
    deg = np.array([[qang(rot[f, i], ref[i]) for i in range(n)] for f in range(cl.frame_count)])
    peak = deg.max(0)                              # max angle away from the frame-0 value
    print("(1) bones whose local ROTATION is non-constant over the clip:")
    for thr in (0.5, 1.0, 5.0, 15.0, 45.0):
        print("      > %5.1f deg : %3d / %d bones" % (thr, int((peak > thr).sum()), n))
    print("(2) largest local rotation change frame 0 -> frame %d (degrees):" % fr)
    d15 = np.array([qang(rot[fr, i], ref[i]) for i in range(n)])
    for i in np.argsort(-d15)[:10]:
        print("      %6.2f deg  %-26s (%s)" % (d15[i], tid_to_chain.get(tids[2][i], "?").split("/")[-1],
                                               "settled" if peak[i] < 1 else "moves"))

    # ---- positions and scales
    pos, scl = cl.pos, cl.scl
    pmax = np.abs(pos - pos[0][None]).max(0).max(1)          # (n,)
    smax = np.abs(scl - scl[0][None]).max(0).max(1)
    print("(1b) local POSITION change over clip: > 1 mm %d, > 1 cm %d, > 10 cm %d bones (max %.3f m)"
          % (int((pmax > 1e-3).sum()), int((pmax > 1e-2).sum()), int((pmax > 1e-1).sum()),
             float(pmax.max())))
    for i in np.argsort(-pmax)[:5]:
        print("      %7.4f m  %s" % (pmax[i], tid_to_chain.get(tids[1][i], "?").split("/")[-1]))
    print("(1c) local SCALE change over clip: > 1e-3 %d bones (max %.4f)"
          % (int((smax > 1e-3).sum()), float(smax.max())))
    dmag = np.abs(np.diff(pos, axis=0)).reshape(cl.frame_count - 1, -1).max(1)
    print("      per-frame max |dpos| mean %.4f m  max %.4f m" % (dmag.mean(), dmag.max()))

    # ---- 3: root / pelvis world yaw
    root_tid = tids[2][0]
    pelvis_tid = None
    for i, t in enumerate(tids[2]):
        if tid_to_chain.get(t, "").endswith("Bip001 Pelvis"):
            pelvis_tid = t
            break
    print("(3) world yaw of the first rotation binding (%s) and of the pelvis, per 6th frame:"
          % tid_to_chain.get(root_tid, "?").split("/")[-1])
    ys, yp = [], []
    for f in range(0, cl.frame_count, max(1, cl.frame_count // 10)):
        scene.reset_pose(cl.pose(f))
        ys.append((f, yaw_of(scene.world_matrix(root_tid)[:3, :3]),
                   yaw_of(scene.world_matrix(pelvis_tid)[:3, :3]) if pelvis_tid else 0.0))
    for f, a, b in ys:
        print("      frame %3d  root yaw %+8.2f deg   pelvis yaw %+8.2f deg" % (f, a, b))
    yaws = np.array([y for _f, y, _b in ys])
    print("      root yaw unwrapped total travel = %.1f deg over the clip; monotonic steps: %s"
          % (abs(np.rad2deg(np.unwrap(np.deg2rad(yaws)))[-1] - np.rad2deg(
              np.unwrap(np.deg2rad(yaws)))[0]),
             bool(np.all(np.diff(np.rad2deg(np.unwrap(np.deg2rad(yaws)))) > -1e-6))))
    r0 = cl.rot[0, 0]
    print("      root LOCAL rotation at frame 0: %s  |q|=%.6f  angle to rest %s = %.3f deg"
          % (np.round(r0, 6), np.linalg.norm(r0),
             np.round(REST[root_tid][1], 4), qang(r0, REST[root_tid][1])))

    # ---- 4: do the LIMBS move relative to the pelvis (world)?
    if pelvis_tid:
        watch = {}
        for path_key in ("Bip001 L Hand", "Bip001 R Hand", "Bip001 L Foot", "Bip001 R Foot",
                         "Bip001 Head", "Bip001 L UpperArm", "Bip001 R UpperArm"):
            for t, ch in tid_to_chain.items():
                if ch.endswith(path_key):
                    watch[path_key] = t
                    break
        traj = {k: [] for k in watch}
        for f in range(cl.frame_count):
            scene.reset_pose(cl.pose(f))
            Pw = scene.world_matrix(pelvis_tid)
            Pinv = np.linalg.inv(Pw)
            for k, t in watch.items():
                p = Pinv @ np.append(scene.world_matrix(t)[:3, 3], 1.0)
                traj[k].append(p[:3])
        print("(4) limb travel in the PELVIS frame (peak-to-peak, metres):")
        for k in watch:
            a = np.array(traj[k])
            rng = a.max(0) - a.min(0)
            print("      %-20s p2p = %6.4f %6.4f %6.4f  (total path %.4f m)"
                  % (k, rng[0], rng[1], rng[2], float(np.linalg.norm(np.diff(a, axis=0), axis=1).sum())))
    return peak


print("quaternion component order evidence:")
print("  the CONSTANT clip's rotation section reproduces Transform.m_LocalRotation EXACTLY when the")
print("  4 floats are read as (x,y,z,w): median |diff| ~1e-6 over ~60-80 bones per clip. Unity stores")
print("  Quaternion as x,y,z,w, and any other assignment (w,x,y,z etc.) cannot match a stored")
print("  quaternion component-wise. |q|==1 holds either way, so the match - not the norm - is the")
print("  evidence. See model-anim-clip.py header / probe8 for the numbers.")
for nm in (sys.argv[1:] or ["zd_daiji", "zd_jn_01", "zd_chuchang"]):
    report(nm)
