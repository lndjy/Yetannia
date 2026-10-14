# hand-render.py -- render Yetannia's four multiplayer rock/paper/scissors hands from the decoded rig.
#
# WHY THIS EXISTS
#   PlaceholderCharacterModel (BaseLib) derives CustomArmPointingTexturePath etc. from `PlaceholderID`,
#   which YetanniaCharacter never overrode, so all four multiplayer gestures resolved to the Ironclad's
#   art (images/ui/hands/multiplayer_hand_ironclad_{point,rock,paper,scissors}.png). BaseLib's own
#   `CustomCharacterModel.CustomArm*TexturePath` + the four Arm*TexturePath.cs Harmony patches are the
#   supported hook, so the fix is to render our own four textures and override those four properties.
#
# THE VANILLA CONVENTION (measured from the retail pck, see .tools/out/charselect/hand_stats.json):
#   every character, every gesture: canvas 422 x 1200, RGBA, alpha present, hand at the TOP and the
#   forearm/sleeve running down to (or past) the bottom edge. The four gestures differ ONLY near the
#   top ~150 px; the forearm below is the same shape in all four.
#
# HOW THE POSE IS BUILT (no hand-authored keyframes exist for this rig)
#   1. the prefab BIND pose is the base (straight fingers -- a clean start for point/paper);
#   2. the FOREARM bone is rotated about the elbow so the forearm is vertical, i.e. the hand ends up
#      above the elbow exactly as in the vanilla art (otherwise the A-pose arm leaves the 0.09 m-wide
#      crop sideways within 0.12 m);
#   3. each finger's three bones get an extra local rotation about a curl axis DERIVED from the rig
#      (the knuckle line), applied in the bone's parent frame so the joint itself does not move;
#   4. the camera's up axis is the ARM axis (elbow->wrist) and its back axis the measured palm/back
#      normal, so the FOREARM is vertical in the image exactly like the vanilla art, and the hand
#      sits on top of it with its natural wrist angle.
#   Every number below is either read from the bundle or measured by `probe`, never eyeballed.
#
# WHY THE CAMERA FRAME CHANGED (was: up = measured fingertip direction, --cam-up finger)
#   The hand bone is not collinear with the forearm: measured, angle(finger_dir, wrist-elbow) =
#   7.52 deg in every gesture. Aiming the camera up at the fingers therefore ROLLED the whole image
#   -- forearm included -- by those 7.5 deg, and the arm came out diagonal. Measured on the shipped
#   PNGs with .tools/out/hands/axis_tilt.py: arm axis 7.3-8.0 deg off image-vertical, and the four
#   gestures all rotated the same way. All 20 vanilla multiplayer_hand_*.png measure 0.4 deg or less
#   off vertical (ironclad +/-0.4, silent -0.2, defect +0.4). Vanilla keeps the ARM vertical, so the
#   image up axis has to be the arm; the 7.5 deg then shows up where it belongs, as a natural wrist
#   angle between hand and forearm instead of as a global rotation. Confirmed by looking at the
#   renders (see .tools/qa/RPS-HAND-FIX.md), not assumed.
#
# usage:
#   python .tools/hand-render.py probe            # identify the hand's sides/thumb -> a sheet
#   python .tools/hand-render.py build            # write the four 422x1200 PNGs + a contact sheet
import argparse
import importlib.util
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "out", "hands")


def _imp(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mr = _imp("model_render", os.path.join(HERE, "model-render.py"))
mrv = _imp("model_anim_render", os.path.join(HERE, "model-anim-render.py"))
BUNDLE = mr.DEFAULT_BUNDLE

# Vanilla canvas, measured from the CTEX headers of all 20 multiplayer_hand_*.png (4 per character
# x 5 characters): 422 x 1200 every time.
VAN_W, VAN_H = 422, 1200

# --------------------------------------------------------------------------------- quaternion maths
# Unity/UnityPy quaternions are (x, y, z, w); mr.quat_to_mat3 normalises before use.


def q_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ], np.float64)


def q_axis_angle(axis, angle):
    a = np.asarray(axis, np.float64)
    n = np.linalg.norm(a)
    if n < 1e-12:
        return np.array([0.0, 0.0, 0.0, 1.0])
    a = a / n
    s = math.sin(angle * 0.5)
    return np.array([a[0] * s, a[1] * s, a[2] * s, math.cos(angle * 0.5)], np.float64)


def q_from_basis(B):
    """Rotation matrix -> quaternion (Shepperd's method), so a measured basis can become a rotation."""
    m = np.asarray(B, np.float64)
    t = m[0, 0] + m[1, 1] + m[2, 2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2.0
        q = np.array([(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s,
                      (m[1, 0] - m[0, 1]) / s, 0.25 * s])
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        q = np.array([0.25 * s, (m[0, 1] + m[1, 0]) / s,
                      (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s])
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        q = np.array([(m[0, 1] + m[1, 0]) / s, 0.25 * s,
                      (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s])
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        q = np.array([(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s,
                      0.25 * s, (m[1, 0] - m[0, 1]) / s])
    return q / np.linalg.norm(q)


def rot_between(a, b):
    """Shortest rotation taking unit vector a to unit vector b, as a 3x3 matrix."""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.eye(3)
        # 180 degrees: rotate about any axis perpendicular to a
        p = np.array([1.0, 0.0, 0.0])
        if abs(a[0]) > 0.9:
            p = np.array([0.0, 1.0, 0.0])
        ax = np.cross(a, p)
        ax = ax / np.linalg.norm(ax)
        return 2.0 * np.outer(ax, ax) - np.eye(3)
    K = np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])
    return np.eye(3) + K + K @ K * (1.0 / (1.0 + c))


def orthonormal(M):
    """Strip scale/shear from a 3x3 by Gram-Schmidt (the Biped chains here are all scale 1)."""
    x = M[:, 0] / np.linalg.norm(M[:, 0])
    y = M[:, 1] - x * float(np.dot(x, M[:, 1]))
    y = y / np.linalg.norm(y)
    z = np.cross(x, y)
    return np.stack([x, y, z], axis=1)


# --------------------------------------------------------------------------------- rig access
NAMES = {}


def build_names(scene):
    if not NAMES:
        for tid in scene.transforms:
            NAMES.setdefault(scene.tr_name(tid), []).append(tid)
    return NAMES


def tid_of(scene, name):
    build_names(scene)
    got = NAMES.get(name)
    if not got:
        raise KeyError(name)
    return got[0]


def bind_local(scene, tid):
    """The prefab's own local TRS for one transform, as numpy.

    NOTE: m_LocalRotation is a quaternion (x,y,z,w) -- it must NOT go through mr._v3, which returns
    only x/y/z and would silently drop w.
    """
    t = scene.transforms[tid]
    q = mr.gg(t, "m_LocalRotation", default=(0.0, 0.0, 0.0, 1.0))
    try:
        qq = np.array([float(q.x), float(q.y), float(q.z), float(q.w)], np.float64)
    except AttributeError:
        qq = np.array([float(q[0]), float(q[1]), float(q[2]), float(q[3])], np.float64)
    return (np.array(mr._v3(mr.gg(t, "m_LocalPosition", default=(0, 0, 0))), np.float64),
            qq,
            np.array(mr._v3(mr.gg(t, "m_LocalScale", default=(1, 1, 1))), np.float64))


def world_pos(scene, tid):
    return np.array(scene.world_matrix(tid)[:3, 3], np.float64)


def world_rot(scene, tid):
    return orthonormal(np.array(scene.world_matrix(tid)[:3, :3], np.float64))


class Hand(object):
    """The bones of one side, resolved once, plus the bind-pose axes measured from them.

    THE FINGER NUMBERING IS MEASURED, NOT ASSUMED. In the hand frame (k = knuckle line, n = palm
    normal, d = finger direction), the five base joints sit at these (k, d) coordinates in metres
    from the wrist (probe output, side L):

        Finger0  k=-0.0037  d=+0.0329  |base-wrist|=0.0383   <- 3.8 cm from the wrist, WAY off the row
        Finger1  k=-0.0440  d=+0.0904  |base-wrist|=0.0913
        Finger2  k=-0.0584  d=+0.0884  |base-wrist|=0.0890
        Finger3  k=-0.0690  d=+0.0852  |base-wrist|=0.0885
        Finger4  k=-0.0723  d=+0.0730  |base-wrist|=0.0817

    Finger0 is the only one not on the metacarpal row and its base is nearest the wrist -> it is the
    THUMB (its 3 "segments" include the metacarpal). Finger1 is the one closest to the thumb
    (0.0591 m vs Finger4's 0.0683 m) and its tip length is 4.2 cm with Finger2/3 at 4.8 cm and
    Finger4 at 3.6 cm -> Finger1..4 are INDEX, MIDDLE, RING, LITTLE.
    Therefore: thumb=0, index=1, middle=2, ring=3, little=4.
    """

    THUMB, INDEX, MIDDLE, RING, LITTLE = 0, 1, 2, 3, 4
    FOUR = (1, 2, 3, 4)

    def __init__(self, scene, side):
        self.scene = scene
        self.side = side
        P = "Bip001 %s " % side
        self.forearm = tid_of(scene, P + "Forearm")
        self.hand = tid_of(scene, P + "Hand")
        self.fingers = []
        for i in range(5):
            # the bundle spells the three segments Finger0 / Finger01 / Finger02
            chain = [tid_of(scene, P + "Finger%d%s" % (i, s)) for s in ("", "1", "2")]
            self.fingers.append(chain)
        self._measure()

    def _measure(self):
        s = self.scene
        s.reset_pose({})
        self.elbow = world_pos(s, self.forearm)
        self.wrist = world_pos(s, self.hand)
        self.tips = [world_pos(s, c[2]) for c in self.fingers]
        self.bases = [world_pos(s, c[0]) for c in self.fingers]
        # finger direction and knuckle line are measured over the FOUR fingers only: including the
        # thumb would tilt both axes (the thumb points out of the knuckle row).
        dd = [self.tips[i] - self.bases[i] for i in self.FOUR]
        self.finger_dir = np.mean(dd, axis=0)
        self.finger_dir /= np.linalg.norm(self.finger_dir)
        self.knuckle = self.bases[self.INDEX] - self.bases[self.LITTLE]
        self.knuckle /= np.linalg.norm(self.knuckle)
        self.palm_n = np.cross(self.knuckle, self.finger_dir)
        self.palm_n /= np.linalg.norm(self.palm_n)
        # The four fingers all hinge about the knuckle line; the thumb hinges about an axis
        # perpendicular to its own direction and lying in the palm plane, which swings it across the
        # palm (the direction a thumb actually closes in).
        self.thumb_dir = self.tips[self.THUMB] - self.bases[self.THUMB]
        self.thumb_dir /= np.linalg.norm(self.thumb_dir)
        self.thumb_axis = np.cross(self.thumb_dir, self.palm_n)
        self.thumb_axis /= np.linalg.norm(self.thumb_axis)
        self.curl_axis = self.knuckle


def pose_fingers(hand, pose, curls, spread):
    """Add a rotation about the rig-derived hinge axis to every finger bone of `hand`.

    `curls` is a list of 5 angles in degrees indexed by the rig's Finger0..Finger4 (so
    curls[Hand.THUMB] is the thumb); 0 leaves the bind pose alone. `spread` fans the four fingers
    apart within the palm plane (about the palm normal) by that many degrees per finger step.
    """
    scene = hand.scene
    for fi, chain in enumerate(hand.fingers):
        ang = math.radians(curls[fi])
        axis_world = hand.thumb_axis if fi == hand.THUMB else hand.curl_axis
        for depth, b in enumerate(chain):
            t = scene.transforms[b]
            f = mr.pid(mr.gg(t, "m_Father"))
            Rp = world_rot(scene, f)
            # hinge axis expressed in the bone's PARENT frame: rotating about a parent-frame axis
            # leaves the joint POSITION untouched and only changes the bone's orientation.
            axis_local = Rp.T @ axis_world
            qd = q_axis_angle(axis_local, ang * CURL_SIGN[hand.side])
            if spread and depth == 0 and fi != hand.THUMB:
                # fan within the palm plane -> rotate about the palm normal, in the parent frame
                ax2 = Rp.T @ hand.palm_n
                qd = q_mul(q_axis_angle(ax2, math.radians(spread) * (fi - 2.5)), qd)
            p, q, sc = pose.get(b, bind_local(scene, b))
            pose[b] = (p, q_mul(qd, np.asarray(q, np.float64)), sc)
            scene.reset_pose(pose)      # so the next joint in the chain sees the updated parent


# Which way is "curl"? Measured, not assumed: `probe` renders both signs and the palm side is
# identified from the pictures. Recorded per side because the two hands are mirrored.
# (see .tools/out/hands/probe_signs.png)
CURL_SIGN = {"L": 1.0, "R": 1.0}


def rotate_bone_world(hand, pose, tid, R_world):
    """Apply an extra world-space rotation R_world about the bone's own origin.

    The rotation is expressed in the bone's PARENT frame (R_parent^T . R . R_parent) and
    pre-multiplied onto the local quaternion, which leaves the joint POSITION fixed and rotates the
    bone plus everything below it.
    """
    scene = hand.scene
    scene.reset_pose(pose)
    father = mr.pid(mr.gg(scene.transforms[tid], "m_Father"))
    Rp = world_rot(scene, father)
    A_parent = Rp.T @ R_world @ Rp
    p, q, sc = pose.get(tid, bind_local(scene, tid))
    pose[tid] = (p, q_mul(q_from_basis(A_parent), np.asarray(q, np.float64)), sc)
    scene.reset_pose(pose)


def aim_bone(hand, pose, tid, a, b):
    """Rotate `tid` so the direction `a` becomes `b` (both world vectors)."""
    rotate_bone_world(hand, pose, tid, rot_between(a, b))
    return world_pos(hand.scene, tid)


def upper_arm_tid(hand):
    return mr.pid(mr.gg(hand.scene.transforms[hand.forearm], "m_Father"))


def raise_arm(hand, pose, upper_dir, fore_dir):
    """Aim the upper arm, then the forearm, so the hand ends up where the caller wants it.

    WHY: in the bind A-pose the hand hangs at hip height, surrounded by the skirt, the hip ribbons
    and the tips of her long hair (measured: mx_3015004_01_hair reaches x=-0.432 while the hand is at
    x=-0.365), so a hand close-up fills with garments. Raising the arm moves the hand OUT into clear
    space, and a raised arm with the sleeve below it is also how the vanilla art is posed.
    """
    scene = hand.scene
    scene.reset_pose(pose)
    ua = upper_arm_tid(hand)
    shoulder = world_pos(scene, ua)
    elbow = world_pos(scene, hand.forearm)
    L1 = np.linalg.norm(elbow - shoulder)
    aim_bone(hand, pose, ua, elbow - shoulder,
             np.asarray(upper_dir, np.float64) / np.linalg.norm(upper_dir) * L1)
    elbow = world_pos(scene, hand.forearm)
    wrist = world_pos(scene, hand.hand)
    L2 = np.linalg.norm(wrist - elbow)
    aim_bone(hand, pose, hand.forearm, wrist - elbow,
             np.asarray(fore_dir, np.float64) / np.linalg.norm(fore_dir) * L2)
    scene.reset_pose(pose)
    return shoulder, elbow, world_pos(scene, hand.hand)


def straighten_forearm(hand, pose, arm_dir):
    """Rotate the FOREARM about the elbow so (wrist - elbow) points along `arm_dir`.

    Applied in the forearm's parent frame (the upper arm), so the elbow stays put; the hand and
    fingers ride along, which is why the camera is then measured from the RESULTING pose rather than
    from the bind pose.
    """
    scene = hand.scene
    scene.reset_pose(pose)
    elbow = world_pos(scene, hand.forearm)
    wrist = world_pos(scene, hand.hand)
    cur = wrist - elbow
    R = rot_between(cur, np.asarray(arm_dir, np.float64) * np.linalg.norm(cur))
    father = mr.pid(mr.gg(scene.transforms[hand.forearm], "m_Father"))
    Rp = world_rot(scene, father)
    A_parent = Rp.T @ R @ Rp
    p, q, sc = pose.get(hand.forearm, bind_local(scene, hand.forearm))
    pose[hand.forearm] = (p, q_mul(q_from_basis(A_parent), np.asarray(q, np.float64)), sc)
    scene.reset_pose(pose)
    return elbow, world_pos(scene, hand.hand)


def measured_frame(hand):
    """(finger_dir, knuckle, palm_normal) of the CURRENT pose -- used to aim the camera."""
    s = hand.scene
    tips = [world_pos(s, c[2]) for c in hand.fingers]
    bases = [world_pos(s, c[0]) for c in hand.fingers]
    d = np.mean([t - b for t, b in zip(tips, bases)], axis=0)
    d /= np.linalg.norm(d)
    k = bases[0] - bases[4]
    k /= np.linalg.norm(k)
    n = np.cross(k, d)
    n /= np.linalg.norm(n)
    return d, k, n


def measured_arm_up(hand):
    """Image-up axis = elbow->wrist, i.e. the FOREARM's own direction. See the header note."""
    s = hand.scene
    up = world_pos(s, hand.hand) - world_pos(s, hand.forearm)
    return up / np.linalg.norm(up)


def cam_up(hand, args):
    """The camera's image-up axis: 'arm' (default, vanilla convention) or 'finger' (the old frame)."""
    if args.cam_up == "finger":
        d, _k, _n = measured_frame(hand)
        return d
    return measured_arm_up(hand)


# --------------------------------------------------------------------------------- camera
def oriented_camera(lo, hi, up, back, px_w, px_h, fov, margin=1.06, iters=5):
    """Perspective camera with a SPECIFIED image-up and image-back, framed on the world box [lo,hi]."""
    up = np.asarray(up, np.float64)
    back = np.asarray(back, np.float64)
    back = back - up * float(np.dot(back, up))
    up = up / np.linalg.norm(up)
    back = back / np.linalg.norm(back)
    right = np.cross(up, back)
    right /= np.linalg.norm(right)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                        for z in (lo[2], hi[2])], np.float64)
    center = (lo + hi) * 0.5
    d = corners - center
    hw = float(np.abs(d @ right).max())
    hh = float(np.abs(d @ up).max())
    uzmax = float((d @ back).max())
    aspect = float(px_w) / float(px_h)
    t = math.tan(math.radians(fov) * 0.5)
    dist = 1.0
    for _ in range(iters):
        half_h = max(hh, hw / aspect) * margin
        dist = half_h / t + uzmax
    eye = center + back * dist
    near = max(0.01, dist * 0.05)
    far = dist + float(np.ptp(d @ back)) * 2.0 + 5.0
    MVP = mr.perspective(fov, aspect, near, far) @ mr.look_at(eye, center, up)
    return MVP, center, eye, near, far, dist


def arm_box(hand, tip_pad, bottom_pad, radius, past=0.0, arm_up=None):
    """World-space box around hand + forearm only, built from bone positions, padded by `radius`.

    `past` (metres) additionally reaches `past` metres down the UPPER arm along `arm_up` (the
    elbow->wrist direction). That is what lets the sleeve fill the bottom of a 422x1200 canvas: the
    forearm alone is only 0.19 m, which cannot reach the bottom edge at the vanilla scale.
    """
    s = hand.scene
    d, k, n = measured_frame(hand)
    up = d if arm_up is None else np.asarray(arm_up, np.float64)
    pts = [world_pos(s, c[2]) for c in hand.fingers]
    pts.append(world_pos(s, hand.forearm))     # the elbow
    pts.append(world_pos(s, hand.hand))        # the wrist
    pts.append(world_pos(s, hand.fingers[2][1]))
    if past > 0.0:
        pts.append(world_pos(s, hand.forearm) - up * past)
    P = np.array(pts)
    lo = P.min(0) - radius
    hi = P.max(0) + radius
    hi = np.maximum(hi, P.max(0) + d * tip_pad)
    lo = np.minimum(lo, P.min(0) - up * bottom_pad)
    return lo, hi


def centred_box(centre, half):
    c = np.asarray(centre, np.float64)
    return c - half, c + half


# --------------------------------------------------------------------------------- rendering
def cull_to_arm(gp, gn, gu, gt, chain_pts, radius):
    """Keep only triangles whose centroid lies within `radius` of the elbow->wrist->fingertip
    polyline. The torso/hip sit ~0.14 m inboard of the arm, so this isolates arm + hand + sleeve
    without needing per-vertex skin data."""
    cen = gp.mean(axis=1)
    best = np.full(len(cen), 1e9)
    for a, b in zip(chain_pts[:-1], chain_pts[1:]):
        ab = b - a
        L2 = float(np.dot(ab, ab))
        if L2 < 1e-12:
            dd = np.linalg.norm(cen - a, axis=1)
        else:
            tt = np.clip(((cen - a) @ ab) / L2, 0.0, 1.0)
            proj = a + tt[:, None] * ab
            dd = np.linalg.norm(cen - proj, axis=1)
        best = np.minimum(best, dd)
    keep = best <= radius
    return gp[keep], gn[keep], gu[keep], gt[keep]


def project_pts(MVP, pts, W, H):
    """World (N,3) -> canvas pixels, matching the rasteriser's viewport (y down)."""
    p = np.concatenate([np.asarray(pts, np.float64), np.ones((len(pts), 1))], 1) @ MVP.T
    ndc = p[:, :2] / p[:, 3:4]
    return np.stack([(ndc[:, 0] + 1.0) * 0.5 * W, (1.0 - ndc[:, 1]) * 0.5 * H], 1)


def silhouette_tilt(mask):
    """Degrees off image-vertical of a finished silhouette: (forearm slope, principal axis).

    The forearm slope is the least-squares slope of (row -> silhouette centroid x) over the lower
    half of the silhouette; the principal axis is the second-order image moment. Both were measured
    the same way on every vanilla texture by .tools/out/hands/axis_tilt.py, so before/after are
    directly comparable.
    """
    ys, xs = np.nonzero(mask)
    if len(ys) < 8:
        return float("nan"), float("nan")
    y0, y1 = int(ys.min()), int(ys.max())
    yy, cx = [], []
    for y in range(y0 + (y1 - y0) // 2, y1 + 1):
        r = np.nonzero(mask[y])[0]
        if len(r):
            yy.append(y)
            cx.append(0.5 * (r[0] + r[-1]))
    slope = float("nan")
    if len(yy) >= 8:
        slope = math.degrees(math.atan(np.polyfit(np.asarray(yy, float),
                                                  np.asarray(cx, float), 1)[0]))
    X = xs.astype(float) - xs.mean()
    Y = ys.astype(float) - ys.mean()
    cov = np.array([[float((X * X).mean()), float((X * Y).mean())],
                    [float((X * Y).mean()), float((Y * Y).mean())]])
    ev, evec = np.linalg.eigh(cov)
    v = evec[:, int(np.argmax(ev))]
    pca = math.degrees(math.atan2(v[0], v[1]))
    if pca > 90:
        pca -= 180
    if pca < -90:
        pca += 180
    return slope, pca


# In the bind A-pose the hand hangs at hip height (measured: wrist y=1.02 m on a 1.70 m character),
# i.e. right beside the skirt, the hip ribbons AND the tips of her very long hair
# (mx_3015004_01_hair reaches x=-0.432 while the hand is at x=-0.365). A hand close-up therefore has
# to say WHICH GEOMETRY it wants or the crop fills with hair and cloth:
#   * keep only the two body meshes -- that alone removes hair, face and both staffs;
#   * keep only triangles near the FINGERTIP->WRIST->ELBOW polyline and start it AT the elbow, so
#     the upper arm, shoulder, torso and skirt can never enter the frame.
KEEP_PARTS = ("mx_3015004_01_body", "mx_3015004_01_body_02")

# How far BELOW the framed box the triangle-cull capsule must reach, in metres. The cull keeps
# triangles whose centroid is within --cull-radius of the chain, so the chain's own end cap is a hard
# edge of kept geometry; if that edge falls inside the frame it shows up as the row of thin white
# spikes/splinters along the bottom of the render. Reaching this far past the box pushes the cap
# outside the frame, so the arm is cut cleanly by the frame edge instead.
CULL_TAIL = 0.030


def scene_tris(rig, keep=None):
    # NOTE: resolve the module global at CALL time -- a default argument would bind the value that
    # existed when the def executed, so --keep-parts would silently do nothing.
    keep = KEEP_PARTS if keep is None else keep
    gp, gn, gu, gt = [], [], [], []
    for g, remap in zip(rig.geoms, rig.remaps):
        if keep and g["name"] not in keep:
            continue
        p = mr.build_part(rig.scene, g["name"], verbose=False, geom=g)
        gp.append(p["pos"])
        gn.append(p["nrm"])
        gu.append(p["uv"])
        gt.append(remap[p["tex"]])
    return (np.concatenate(gp, 0), np.concatenate(gn, 0), np.concatenate(gu, 0),
            np.concatenate(gt, 0))


def arm_chain(hand, d, past_elbow=0.06):
    """Fingertip -> wrist -> elbow -> a point `past_elbow` further up, as a polyline."""
    tip_mid = np.mean([world_pos(hand.scene, c[2]) for c in hand.fingers], axis=0)
    elbow = world_pos(hand.scene, hand.forearm)
    wrist = world_pos(hand.scene, hand.hand)
    return np.array([tip_mid, wrist, elbow, elbow - d * past_elbow])


def render_pose(rig, pose, MVP, W, H, ssaa, near, cull=None, shade_fwd=None, keep=None):
    rig.scene.reset_pose(pose)
    gp, gn, gu, gt = scene_tris(rig, keep)
    if cull is not None:
        gp, gn, gu, gt = cull_to_arm(gp, gn, gu, gt, cull[0], cull[1])
    shade = {"mode": "toon", "fwd": (shade_fwd if shade_fwd is not None else (0.0, 0.0, 1.0))}
    col, alp = mr.rasterize_fast(gp, gn, gu, gt, rig.tex_arrays, rig.tex_alphas,
                                 MVP, W * ssaa, H * ssaa, near, verbose=False,
                                 extras=rig.extras, shade=shade)
    col, alp = mrv.downsample(col, alp, ssaa, W, H)
    return mrv.to_rgba(col, alp)


def toon_opts(args):
    return dict(enabled=True, spec=args.spec, rim=args.rim, rim_power=args.rim_power,
                rim_color=(0.62, 0.82, 1.0), smoothness=0.055, half_lambert=True)


# --------------------------------------------------------------------------------- gestures
# `curls` is degrees of hinge per finger, indexed by the rig's Finger0..Finger4, i.e.
# [thumb, index, middle, ring, little] -- the mapping established by Hand._measure's docstring.
# A fully closed finger gets `--closed` degrees at EVERY one of its three joints (so the total
# flexion on that finger is 3x the value); the default 92 deg is a fist. The thumb does not share
# the fingers' hinge axis and physically cannot close as far, so it gets a fraction of that angle.
EXTENDED = {
    "point":    (Hand.INDEX,),
    "rock":     (),
    "paper":    (Hand.THUMB, Hand.INDEX, Hand.MIDDLE, Hand.RING, Hand.LITTLE),
    "scissors": (Hand.INDEX, Hand.MIDDLE),
}
SPREAD = {"point": 0.0, "rock": 0.0, "paper": 6.0, "scissors": 14.0}
# thumb flexion as a fraction of --closed. 0 = the bind pose (extended thumb).
THUMB_FRACTION = {"point": 0.45, "rock": 0.75, "paper": 0.0, "scissors": 0.45}
# Which fingers open, for the report.
GESTURE_NOTE = {
    "point": "index extended, middle/ring/little closed, thumb half-folded",
    "rock": "fist: all four closed, thumb folded across the palm",
    "paper": "open palm: all five extended and fanned",
    "scissors": "index+middle extended in a V, ring/little closed",
}


def curls_for(name, side, closed_deg):
    ext = EXTENDED[name]
    curls = []
    for i in range(5):
        if i in ext:
            curls.append(0.0)
        elif i == Hand.THUMB:
            curls.append(closed_deg * THUMB_FRACTION[name])
        else:
            curls.append(closed_deg)
    return curls, SPREAD[name]


def build_pose(hand, name, closed_deg, arm_dir):
    """-> (pose dict, camera frame (up, back_right_axis), curl description)."""
    pose = {}
    straighten_forearm(hand, pose, arm_dir)
    d, k, n = measured_frame(hand)
    curls, spread = curls_for(name, hand.side, closed_deg)
    pose_fingers(hand, pose, curls, spread)
    return pose, (d, k, n), curls


def palm_of(spec, name):
    """'back' / 'palm' for one gesture, from a single value or 4 comma-separated values."""
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    if len(parts) == 1:
        return parts[0]
    order = ("point", "rock", "paper", "scissors")
    try:
        return parts[order.index(name)]
    except (ValueError, IndexError):
        return parts[0]


def pose_arm(hand, pose, args):
    """Raise the arm when --upper-dir/--fore-dir are given, else straighten the forearm.

    Kept as one call site so every mode (probe/parts/build) poses the arm identically.
    """
    if args.upper_dir and args.fore_dir:
        u = np.array([float(v) for v in args.upper_dir.split(",")], np.float64)
        fd = np.array([float(v) for v in args.fore_dir.split(",")], np.float64)
        return raise_arm(hand, pose, u, fd)
    straighten_forearm(hand, pose,
                       np.array([float(v) for v in args.arm_dir.split(",")], np.float64))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("probe", "probe-signs", "parts", "build"))
    ap.add_argument("--side", default="L")
    ap.add_argument("--ssaa", type=int, default=3)
    ap.add_argument("--fov", type=float, default=26.0)
    ap.add_argument("--closed", type=float, default=92.0, help="degrees for a fully closed finger")
    ap.add_argument("--palm", default="back",
                    help="which face of the hand the camera sees: 'back' or 'palm' or, to choose per "
                         "gesture, exactly four comma-separated values in point,rock,paper,scissors "
                         "order. The four shipped textures are independent artworks (vanilla's are "
                         "hand-painted separately), so a per-gesture view is legitimate.")
    ap.add_argument("--arm-dir", default="0,-1,0",
                    help="world direction elbow->wrist when --upper-dir is empty")
    ap.add_argument("--upper-dir", default="",
                    help="world direction shoulder->elbow; a non-empty value raises the arm, "
                         "which is what gets the hand out of the hip/skirt/hair clutter")
    ap.add_argument("--fore-dir", default="",
                    help="world direction elbow->wrist when --upper-dir is set")
    ap.add_argument("--cull-radius", type=float, default=0.060)
    ap.add_argument("--keep-parts", default=",".join(KEEP_PARTS),
                    help="body meshes to render; mx_3015004_01_hair / _face / _weapon* are the "
                         "geometry that otherwise floods a hand close-up")
    ap.add_argument("--past-elbow", type=float, default=0.06,
                    help="how far UP the upper arm the cull/framing chain reaches, in metres. More "
                         "reaches further into the sleeve, which is the only geometry that can fill "
                         "the lower part of a 422x1200 canvas (the forearm alone is 0.19 m).")
    ap.add_argument("--no-cull", dest="cull", action="store_false")
    ap.add_argument("--rim", type=float, default=0.18)
    ap.add_argument("--rim-power", type=float, default=3.2)
    ap.add_argument("--spec", type=float, default=0.30)
    ap.add_argument("--cam-up", default="arm", choices=("arm", "finger"),
                    help="camera image-up axis: 'arm' = elbow->wrist (vanilla: forearm vertical), "
                         "'finger' = measured fingertip direction (the old, tilted frame)")
    ap.add_argument("--outline", type=int, default=2,
                    help="baked silhouette outline width in px (same as the in-combat flipbook)")
    ap.add_argument("--outline-color", default="0.055,0.075,0.16")
    ap.add_argument("--outdir", default=OUTDIR)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    arm_dir = np.array([float(v) for v in args.arm_dir.split(',')], np.float64)
    KEEP = tuple(p for p in args.keep_parts.split(',') if p)
    globals()['KEEP_PARTS'] = KEEP
    t0 = time.time()
    rig = mrv.Rig(BUNDLE, toon=toon_opts(args))
    rig.tid_to_chain = {}
    print("[rig] %d parts, %d look-dev entries, toon=%s (%.1fs)"
          % (len(rig.geoms), len(rig.extras), rig.use_toon, time.time() - t0))
    hand = Hand(rig.scene, args.side)
    print("[hand %s] bind elbow=%s wrist=%s" % (args.side, np.round(hand.elbow, 4),
                                                np.round(hand.wrist, 4)))
    print("[hand %s] bind finger_dir=%s knuckle=%s palm_n=%s"
          % (args.side, np.round(hand.finger_dir, 4), np.round(hand.knuckle, 4),
             np.round(hand.palm_n, 4)))
    for i, (b, t, c) in enumerate(zip(hand.bases, hand.tips, hand.fingers)):
        print("[hand %s] Finger%d base=%s tip=%s (bone %d)" % (args.side, i, np.round(b, 4),
                                                              np.round(t, 4), len(c)))
    # Numerical thumb discriminator, in the hand's own frame (k = knuckle line, n = palm normal,
    # d = finger direction), origin at the wrist. The thumb's metacarpal is NOT in the knuckle plane,
    # so it is the finger whose base is the outlier along k AND n.
    axes = np.stack([hand.knuckle, hand.palm_n, hand.finger_dir], axis=1)
    print("[hand %s] finger bases in (knuckle, palm_n, finger_dir) metres from the wrist:"
          % args.side)
    for i, b in enumerate(hand.bases):
        v = axes.T @ (b - hand.wrist)
        print("           Finger%d  k=%+.4f  n=%+.4f  d=%+.4f   |base-wrist|=%.4f"
              % (i, v[0], v[1], v[2], np.linalg.norm(b - hand.wrist)))
    # the curl axis is the knuckle line itself, in world space
    hand.curl_axis = hand.knuckle

    if args.mode == "probe":
        # Axis-aligned views of the posed hand. TWO rows, because the sleeve geometry that hangs off
        # the upper arm (`Bone_yixiu_L`, a large flat plate) swamps a hand-only crop:
        #   row 0 = hand only (wrist..fingertips, tight)
        #   row 1 = the whole forearm+hand as it will be framed in the shipped texture
        pose = {}
        pose_arm(hand, pose, args)
        d, k, n = measured_frame(hand)
        tip_mid = np.mean([world_pos(rig.scene, c[2]) for c in hand.fingers], axis=0)
        chain_hand = np.array([tip_mid, hand.wrist, hand.wrist - d * 0.02])
        chain_arm = arm_chain(hand, d, args.past_elbow)
        views = [("+palm_n", d, n), ("-palm_n", d, -n), ("+knuckle", d, k), ("-knuckle", d, -k)]
        tiles = []
        for row, (box, cull_r, tag) in enumerate((
                (centred_box((hand.wrist + tip_mid) * 0.5, 0.042), 0.038, "hand"),
                (None, args.cull_radius, "arm"))):
            lo, hi = arm_box(hand, 0.012, 0.010, 0.045) if box is None else box
            for lbl, up, back in views:
                MVP, c, e, near, _f, dist = oriented_camera(lo, hi, up, back, 512, 512,
                                                            args.fov, 1.08)
                arr = render_pose(rig, pose, MVP, 512, 512, args.ssaa, near,
                                  cull=(chain_hand if tag == "hand" else chain_arm, cull_r),
                                  shade_fwd=back)
                tiles.append(("%s %s" % (tag, lbl), arr))
                print("[probe] %-14s eye=%s dist=%.3f" % ("%s %s" % (tag, lbl), np.round(e, 3),
                                                          dist))
        sheet = Image.new("RGB", (4 * 520 + 8, 2 * 542 + 8), (16, 17, 21))
        dr = ImageDraw.Draw(sheet)
        for i, (lbl, arr) in enumerate(tiles):
            im = Image.fromarray(arr, "RGBA")
            bg = Image.new("RGBA", im.size, (16, 17, 21, 255))
            sheet.paste(Image.alpha_composite(bg, im).convert("RGB"),
                        (8 + (i % 4) * 520, 8 + (i // 4) * 542 + 20))
            dr.text((10 + (i % 4) * 520, 8 + (i // 4) * 542 + 4), lbl, fill=(240, 240, 245))
        p = os.path.join(args.outdir, "probe_views.png")
        sheet.save(p)
        print("[probe] -> %s" % p)
        return

    if args.mode == "probe-signs":
        # Fixes the curl direction EMPIRICALLY: the camera frame comes from the STRAIGHT-hand pose
        # (a curled hand's mean finger direction points across the palm, which would tilt the view),
        # and only the finger angles change between the two signs.
        tiles = []
        pose = {}
        pose_arm(hand, pose, args)
        d, k, n = measured_frame(hand)
        lo, hi = arm_box(hand, 0.020, 0.015, 0.050)
        chain = arm_chain(hand, d, args.past_elbow)
        for sgn in (+1.0, -1.0):
            CURL_SIGN[args.side] = sgn
            pose = {}
            pose_arm(hand, pose, args)
            pose_fingers(hand, pose, [70, 70, 70, 70, 45], 0.0)
            for lbl, bk in (("-n", -n), ("+n", n)):
                MVP, c, e, near, _f, dist = oriented_camera(lo, hi, d, bk, 384, 1024,
                                                            args.fov, 1.05)
                arr = render_pose(rig, pose, MVP, 384, 1024, args.ssaa, near,
                                  cull=(chain, args.cull_radius), shade_fwd=bk)
                tiles.append(("sign %+d  back=%s" % (sgn, lbl), arr))
        W = 384 + 8
        sheet = Image.new("RGB", (len(tiles) * W + 8, 1044), (16, 17, 21))
        dr = ImageDraw.Draw(sheet)
        for i, (lbl, arr) in enumerate(tiles):
            im = Image.fromarray(arr, "RGBA")
            bg = Image.new("RGBA", im.size, (16, 17, 21, 255))
            sheet.paste(Image.alpha_composite(bg, im).convert("RGB"), (8 + i * W, 28))
            dr.text((10 + i * W, 8), lbl, fill=(240, 240, 245))
        p = os.path.join(args.outdir, "probe_signs.png")
        sheet.save(p)
        print("[probe-signs] -> %s" % p)
        return

    if args.mode == "parts":
        # Which PART is which: render the six meshes separately through one camera that frames the
        # whole arm. This settles empirically what the geometry around the hand is -- a cull radius
        # alone could not, because it also pulls in whatever ribbons/ornaments sit nearby.
        pose = {}
        pose_arm(hand, pose, args)
        d, k, n = measured_frame(hand)
        back = -n if args.palm == "palm" else n
        lo, hi = arm_box(hand, 0.02, 0.02, 0.07)
        W = H = 512
        MVP, c, e, near, _f, dist = oriented_camera(lo, hi, d, back, W, H, args.fov, 1.25)
        rig.scene.reset_pose(pose)
        geo = []
        for g, remap in zip(rig.geoms, rig.remaps):
            pp = mr.build_part(rig.scene, g["name"], verbose=False, geom=g)
            geo.append((g["name"], pp["pos"], pp["nrm"], pp["uv"], remap[pp["tex"]]))
        chain = arm_chain(hand, d, args.past_elbow)
        tiles = []
        for nm, gp, gn, gu, gt in geo:
            gp2, gn2, gu2, gt2 = cull_to_arm(gp, gn, gu, gt, chain, args.cull_radius)
            col, alp = mr.rasterize_fast(gp2, gn2, gu2, gt2, rig.tex_arrays, rig.tex_alphas,
                                         MVP, W, H, near, verbose=False, extras=rig.extras,
                                         shade={"mode": "toon", "fwd": back})
            rgb = (mrv.to_rgba(col, alp)[..., :3].astype(np.float32) * 0.30).astype(np.uint8)
            rgb[..., 1] = np.maximum(rgb[..., 1], (alp * 255).astype(np.uint8))
            tiles.append(("%s (%d tris kept)" % (nm, len(gp2)),
                          np.dstack([rgb, (alp * 255).astype(np.uint8)])))
        gp, gn, gu, gt = scene_tris(rig, KEEP_PARTS)
        gp, gn, gu, gt = cull_to_arm(gp, gn, gu, gt, chain, args.cull_radius)
        print("[parts] KEEP_PARTS + cull %.3f m -> %d triangles" % (args.cull_radius, len(gp)))
        cen = gp.reshape(-1, 3)
        up, right = d, np.cross(d, back) / np.linalg.norm(np.cross(d, back))
        print("[parts] culled content: %.3f m along up (fingertip->elbow), %.3f m along right; "
              "aspect w/h = %.3f   (canvas aspect 0.352)"
              % (np.ptp(cen @ up), np.ptp(cen @ right), np.ptp(cen @ right) / max(1e-6, np.ptp(cen @ up))))
        col, alp = mr.rasterize_fast(gp, gn, gu, gt, rig.tex_arrays, rig.tex_alphas, MVP, W, H,
                                     near, verbose=False, extras=rig.extras,
                                     shade={"mode": "toon", "fwd": back})
        tiles.append(("SHIPPED (body+body_02, culled)", mrv.to_rgba(col, alp)))
        for nm, gp, _gn, _gu, _gt in geo:
            print("[parts] %-28s tris=%d  x=[%.3f,%.3f] y=[%.3f,%.3f] z=[%.3f,%.3f]"
                  % (nm, len(gp), gp[:, 0].min(), gp[:, 0].max(), gp[:, 1].min(), gp[:, 1].max(),
                     gp[:, 2].min(), gp[:, 2].max()))
        cols = 4
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (W + 8) + 8, rows * (H + 26) + 8), (14, 15, 19))
        dr = ImageDraw.Draw(sheet)
        for i, (nm, arr) in enumerate(tiles):
            im = Image.fromarray(arr, "RGBA")
            bg = Image.new("RGBA", im.size, (14, 15, 19, 255))
            x = 8 + (i % cols) * (W + 8)
            y = 8 + (i // cols) * (H + 26)
            sheet.paste(Image.alpha_composite(bg, im).convert("RGB"), (x, y + 18))
            dr.text((x + 2, y + 2), nm, fill=(240, 240, 245))
        p = os.path.join(args.outdir, "probe_parts.png")
        sheet.save(p)
        print("[parts] -> %s" % p)
        return

    # ---------------------------------------------------------------- build the four gestures
    #
    # FRAMING POLICY (measured, not guessed). Two numbers were measured off the vanilla art first
    # (.tools/out/charselect/van_hand_profile.py):
    #   * the forearm/sleeve "plateau" width is 231-302 px of the 422 canvas;
    #   * the hand region is 146-183 px of the 1200 canvas for point/scissors, 120-142 for paper,
    #     50-56 for a fist -- i.e. 4-15 % of the height;
    #   * the silhouette always reaches the BOTTOM edge (y1 = 1108-1122).
    # So the canvas is mostly ARM, not hand. Policy: render on a canvas 2x the vanilla size, then
    # choose the crop scale as min(fit the silhouette to the full height, fit it to 98 % of the
    # width) -- the height fit wins here, which puts the fingers at the top, runs the arm off the
    # bottom and lands the sleeve plateau at ~314 px (vanilla: 302). The camera's up/back axes come
    # from the STRAIGHT-hand pose so the gesture itself cannot tilt the view.
    BIG_W, BIG_H = VAN_W * 2, VAN_H * 2
    TOP_PAD, WIDTH_FILL = 14, 0.98
    summary = {}
    for name in ("point", "rock", "paper", "scissors"):
        pose = {}
        pose_arm(hand, pose, args)
        d, k, n = measured_frame(hand)          # <- pre-curl: fingers still straight
        curls, spread = curls_for(name, hand.side, args.closed)
        pose_fingers(hand, pose, curls, spread)
        print("[build] %s (%s): curls=%s spread=%.2f"
              % (name, GESTURE_NOTE[name], np.round(curls, 1), spread))

        back = -n if palm_of(args.palm, name) == "palm" else n
        up = cam_up(hand, args)
        br = np.cross(up, back)
        br /= np.linalg.norm(br)
        # the two angles this fix is about, measured on the posed rig rather than eyeballed
        _e = world_pos(rig.scene, hand.forearm)
        _w = world_pos(rig.scene, hand.hand)
        _arm = (_w - _e) / np.linalg.norm(_w - _e)
        print("[build] %s: cam-up=%s  forearm is %+.2f deg off image-vertical; "
              "wrist angle (fingers vs forearm) = %.2f deg"
              % (name, args.cam_up,
                 math.degrees(math.atan2(float(np.dot(_arm, br)), float(np.dot(_arm, up)))),
                 math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(d, up))))))))
        lo, hi = arm_box(hand, 0.020, 0.015, 0.060, args.past_elbow, up)
        MVP, c, e, near, _f, dist = oriented_camera(lo, hi, up, back, BIG_W, BIG_H, args.fov, 1.05)
        chain = arm_chain(hand, d, args.past_elbow + args.cull_radius + CULL_TAIL)
        arr = render_pose(rig, pose, MVP, BIG_W, BIG_H, args.ssaa, near,
                          cull=(chain, args.cull_radius) if args.cull else None, shade_fwd=back)
        a = arr[..., 3] > 8
        if not a.any():
            print("[build] %s: EMPTY RENDER -- nothing in frame" % name)
            continue
        ys, xs = np.nonzero(a)
        bx0, bx1, by0, by1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        bw, bh = bx1 - bx0 + 1, by1 - by0 + 1
        # crop scale, in big-render px -> final px
        sc = min((VAN_H - TOP_PAD) / float(bh), WIDTH_FILL * VAN_W / float(bw))
        sw, sh = VAN_W / sc, VAN_H / sc
        # horizontal centre: the mean of the five FINGERTIP pixels, so the hand (not the sleeve) is
        # what ends up centred -- then clamped so the whole silhouette stays inside the crop.
        proj = project_pts(MVP, [world_pos(rig.scene, c2[2]) for c2 in hand.fingers], BIG_W, BIG_H)
        cx = float(proj[:, 0].mean())
        # keep the whole silhouette (plus room for the baked outline) inside the crop:
        # cx - sw/2 <= bx0 and cx + sw/2 >= bx1. 8 px of slack, because apply_outline() dilates the
        # silhouette by --outline px AFTER the crop.
        cx = min(max(cx, bx1 - sw * 0.5 + 8.0), bx0 + sw * 0.5 - 8.0)
        sx0 = cx - sw * 0.5
        sy0 = by0 - TOP_PAD / sc
        im = Image.fromarray(arr, "RGBA").crop((int(round(sx0)), int(round(sy0)),
                                                int(round(sx0 + sw)), int(round(sy0 + sh))))
        im = im.resize((VAN_W, VAN_H), Image.LANCZOS)
        out = np.asarray(im, dtype=np.uint8)
        if args.outline:
            ocol = tuple(float(v) for v in args.outline_color.split(","))
            out = mr.apply_outline(out, ocol, args.outline)
        a2 = out[..., 3] > 8
        ys2, xs2 = np.nonzero(a2)
        bb = (int(xs2.min()), int(ys2.min()), int(xs2.max()), int(ys2.max())) if a2.any() else None
        # row-width profile: where does the hand end and the forearm/sleeve plateau begin?
        rows = a2.sum(1)
        nz = np.nonzero(rows)[0]
        plateau = int(np.median(rows[nz.max() - max(1, len(nz) // 4):nz.max() + 1])) if len(nz) else 0
        lim = 0.60 * plateau
        hands_end = int(nz.min())
        for y in range(int(nz.min()), int(nz.max()) + 1):
            if rows[y] >= lim:
                hands_end = y
                break
        t_slope, t_pca = silhouette_tilt(a2)
        print("[build] %s: big bbox x=[%d,%d] y=[%d,%d] (%dx%d)  crop scale=%.4f  dist=%.3f\n"
              "            -> 422x1200  alpha>8 %.1f%%  bbox=%s  plateau_w=%d px  "
              "hand region=%d px (%.1f%% of height)\n"
              "            -> FINISHED PNG tilt: forearm slope %+.2f deg, principal axis %+.2f deg "
              "off vertical;  vanilla: plateau 231-302 px, hand 4-15%%, tilt <0.5 deg"
              % (name, bx0, bx1, by0, by1, bw, bh, sc, dist, 100.0 * a2.mean(), bb, plateau,
                 hands_end - int(nz.min()), 100.0 * (hands_end - nz.min()) / 1200.0,
                 t_slope, t_pca))
        p = os.path.join(args.outdir, "multiplayer_hand_yetannia_%s.png" % name)
        Image.fromarray(out, "RGBA").save(p)
        Image.fromarray(out, "RGBA").resize((BIG_W, BIG_H), Image.NEAREST).save(
            os.path.join(args.outdir, "%s_2x.png" % name))
        summary[name] = dict(path=p, bbox=bb, curls=curls, spread=spread,
                             note=GESTURE_NOTE[name], fill=float(a2.mean()),
                             canvas=[VAN_W, VAN_H], crop_scale=float(sc),
                             plateau_w=plateau, hand_px=hands_end - int(nz.min()),
                             forearm_tilt_deg=t_slope, pca_tilt_deg=t_pca,
                             cam_up=args.cam_up)
    with open(os.path.join(args.outdir, "hands.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)

    # contact sheet: our four next to the vanilla ironclad four
    van = os.path.join(HERE, "out", "charselect", "vanilla_png")
    rows = [("vanilla ironclad", van, "multiplayer_hand_ironclad_%s.png"),
            ("yetannia", args.outdir, "multiplayer_hand_yetannia_%s.png")]
    cw, ch = 132, 376
    pad, lab = 8, 24
    sheet = Image.new("RGB", (pad + 4 * (cw + pad), lab + 2 * (ch + lab + pad)), (18, 19, 23))
    dr = ImageDraw.Draw(sheet)
    for j, g in enumerate(("point", "rock", "paper", "scissors")):
        dr.text((pad + j * (cw + pad) + 30, 6), g, fill=(255, 220, 120))
    for i, (lbl, d_, pat) in enumerate(rows):
        y = lab + i * (ch + lab + pad)
        dr.text((4, y + ch // 2), lbl, fill=(180, 220, 255))
        for j, g in enumerate(("point", "rock", "paper", "scissors")):
            fp = os.path.join(d_, pat % g)
            if not os.path.exists(fp):
                continue
            t = Image.open(fp).convert("RGBA")
            r = min(cw / t.width, ch / t.height)
            t = t.resize((max(1, int(t.width * r)), max(1, int(t.height * r))), Image.LANCZOS)
            bg = Image.new("RGB", (cw, ch), (52, 52, 58))
            bg.paste(t, ((cw - t.width) // 2, (ch - t.height) // 2), t)
            sheet.paste(bg, (pad + j * (cw + pad), y))
    sp = os.path.join(args.outdir, "hands_contact.png")
    sheet.save(sp)
    print("[build] contact sheet -> %s (%dx%d)" % (sp, sheet.width, sheet.height))


if __name__ == "__main__":
    main()
