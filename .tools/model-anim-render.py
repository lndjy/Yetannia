# model-anim-render.py -- render clip motion: per-frame PNGs, a contact sheet and an animated GIF.
#
# Reuses model-render.py unchanged for everything about meshes/textures/skinning/rasterising; the
# only additions are (a) Scene.local_pose, which re-poses the prefab hierarchy per frame, and
# (b) a FIXED camera for the whole clip so that what moves on screen is the character, not the frame.
# The clip -> bone TRS decoding lives in model-anim-clip.py (see the header there for the format).
#
# usage:
#   python .tools/model-anim-render.py zd_daiji
#   python .tools/model-anim-render.py zd_jn_01 --height 320 --step 1
#   python .tools/model-anim-render.py --all
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


def _imp(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mr = _imp("model_render", os.path.join(HERE, "model-render.py"))
ma = _imp("model_anim_clip", os.path.join(HERE, "model-anim-clip.py"))

BUNDLE = mr.DEFAULT_BUNDLE
OUTROOT = os.path.join(HERE, "out", "render", "anim")
BG = (26, 28, 34, 255)

ORDER = ["zd_daiji", "zd_jn_01", "zd_chuchang"]


# ------------------------------------------------------------------ setup
class Rig(object):
    """Everything that is decoded once and re-posed per frame.

    Texture policy: `geom["tex_ids"]` is a list of per-material combination tuples
    (albedo, shadow, light, metal, eye), so the global texture list keeps the SHADOW map next to the
    albedo it belongs to. `self.extras[tp]` then hands the rasteriser the per-material cel data
    (shadow map array + authored toon parameters) for whichever global slot a triangle landed in.
    """

    def __init__(self, bundle, toon=None):
        self.scene = mr.Scene(bundle)
        self.tid_to_chain = {}
        self.geoms = []
        for nm in mr.PARTS:
            try:
                self.geoms.append(mr.decode_part(self.scene, nm, verbose=False))
            except KeyError as e:
                print("  skip part: %s" % e)
        # global texture list (combination tuples) + per part remap
        used = []
        for g in self.geoms:
            for t in g["tex_ids"]:
                if t is not None and t not in used:
                    used.append(t)
        self.tex_arrays, self.tex_alphas, self.tex_names = [], [], []
        self.extras = []
        self.toon = dict(toon or {})
        self.use_toon = bool(self.toon.get("enabled"))
        for t in used:
            alb = t[0]
            arr = self.scene.texture_image(alb) if alb is not None else None
            nm = (mr.gg(self.scene.textures[alb].read(), "m_Name")
                  if alb in self.scene.textures else str(alb))
            if arr is None:
                self.tex_arrays.append(None)
                self.tex_alphas.append(False)
                self.tex_names.append(nm)
            else:
                a = arr[..., 3]
                self.tex_arrays.append(arr)
                self.tex_alphas.append(float((a < 0.98).mean()) > 0.02)
                self.tex_names.append(nm)
            # per-channel look-dev maps, keyed by the SAME global index as the albedo
            chans = dict(zip(mr.CHANNEL_ORDER, t[1:]))
            ex = {}
            for c in ("shadow", "metal"):
                tp = chans.get(c)
                ex[c] = self.scene.texture_image(tp) if tp is not None else None
            # the material record that carries _DiffuseThreshold / _SpecColor / _SpecularIntensity
            mat = None
            for g in self.geoms:
                for mi, combo in enumerate(g["tex_ids"]):
                    if combo == t:
                        mat = g.get("mat_slots", [])[mi] if mi < len(g.get("mat_slots", [])) else None
                        break
                if mat is not None:
                    break
            ex["params"] = mr.toon_params(mat, self.toon)
            ex["material"] = (mat or {}).get("info", {}).get("name")
            self.extras.append(ex)
        self.used = used
        self.remaps = []
        for g in self.geoms:
            self.remaps.append(np.array([used.index(t) if t is not None else -1
                                         for t in g["tex_ids"]], np.int64))

    def posed_tris(self):
        """Skin every part at the scene's current pose -> global triangle arrays."""
        gp, gn, gu, gt = [], [], [], []
        for g, remap in zip(self.geoms, self.remaps):
            p = mr.build_part(self.scene, g["name"], verbose=False, geom=g)
            gi = remap[p["tex"]]
            gp.append(p["pos"])
            gn.append(p["nrm"])
            gu.append(p["uv"])
            gt.append(gi)
        gp = np.concatenate(gp, 0)
        gn = np.concatenate(gn, 0)
        gu = np.concatenate(gu, 0)
        gt = np.concatenate(gt, 0)
        gt[gt < 0] = 0
        return gp, gn, gu, gt

    def bbox_over_clip(self, clip, frames, offsets=None):
        """-> (lo_all, hi_all, lo_char, hi_char) over the given frames; 'char' excludes the two
        weapon parts, whose bones the animations swing a long way out of the body."""
        lo = np.array([1e9] * 3)
        hi = np.array([-1e9] * 3)
        clo = np.array([1e9] * 3)
        chi = np.array([-1e9] * 3)
        for f in frames:
            self.scene.reset_pose(clip.pose(f))
            off = offsets[f] if offsets else 0.0
            for g, remap in zip(self.geoms, self.remaps):
                p = mr.build_part(self.scene, g["name"], verbose=False, geom=g)
                V = p["P"] - off
                lo = np.minimum(lo, V.min(0))
                hi = np.maximum(hi, V.max(0))
                if not g["name"].endswith(("weapon", "weapon01")):
                    clo = np.minimum(clo, V.min(0))
                    chi = np.maximum(chi, V.max(0))
        return lo, hi, clo, chi

    def root_offsets(self, clip, frames, follow):
        """Per-frame translation to subtract so that a moving character stays in frame.

        'xz' keeps the character centred horizontally while still showing the jumps; 'none' leaves
        the world alone (the honest fixed-camera view, which is what the idle/entrance use).
        """
        if follow == "none":
            return None
        root = None
        for t in clip.attr_tid[2]:
            if (self.tid_to_chain.get(t) or "").endswith("Bip001"):
                root = t
                break
        if root is None:
            print("  ! follow=%s requested but no Bip001 in this clip; using a fixed camera" % follow)
            return None
        out, base = {}, None
        for f in frames:
            self.scene.reset_pose(clip.pose(f))
            p = np.array(self.scene.world_matrix(root)[:3, 3])
            if base is None:
                base = p.copy()
            d = p - base
            if follow == "xz":
                d[1] = 0.0
            out[f] = d
        tr = np.array([out[f] for f in frames])
        print("  follow=%s: root moves %.3f m in x, %.3f in y, %.3f in z over the clip"
              % (follow, float(np.ptp(tr[:, 0])), float(np.ptp(tr[:, 1])),
                 float(np.ptp(tr[:, 2]))))
        return out


def camera_for(lo, hi, height, fov, fwd, margin=1.10, aspect_override=None):
    center = (lo + hi) * 0.5
    size = np.maximum(hi - lo, 1e-6)
    if aspect_override is None:
        W_ = max(128, int(round(height * (size[0] / size[1]) / 2.0)) * 2)
        W_ = min(W_, height * 2)
    else:
        W_ = int(round(height * aspect_override / 2.0)) * 2
    aspect = float(W_) / float(height)
    half_h = size[1] * 0.5 * margin
    half_w = size[0] * 0.5 * margin
    t = math.tan(math.radians(fov) * 0.5)
    fit = max(half_h / t, half_w / (t * aspect))
    # the nearest point of the subject sits half its depth in front of the centre, so extra distance
    # is only needed for HALF the depth - using the full depth is what makes the subject tiny.
    dist = fit + size[2] * 0.5
    eye = center + fwd * dist
    near = max(0.05, dist * 0.02)
    far = dist + size[2] * 3 + 10.0
    MVP = mr.perspective(fov, aspect, near, far) @ mr.look_at(eye, center, np.array([0.0, 1.0, 0.0]))
    return MVP, W_, height, center, eye, near, far


def downsample(col, alp, ssaa, W, H):
    if ssaa <= 1:
        return col, alp
    pm = (col * alp[..., None]).reshape(H, ssaa, W, ssaa, 3).mean(axis=(1, 3))
    al = alp.reshape(H, ssaa, W, ssaa).mean(axis=(1, 3))
    return pm / np.maximum(al[..., None], 1e-6), al


def to_rgba(col, alp):
    out = np.zeros(col.shape[:2] + (4,), np.uint8)
    out[..., :3] = np.clip(col * 255.0 + 0.5, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alp * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return out


def composite_over_bg(rgba):
    bg = Image.new("RGBA", (rgba.shape[1], rgba.shape[0]), BG)
    return Image.alpha_composite(bg, Image.fromarray(rgba, "RGBA")).convert("RGB")


# ------------------------------------------------------------------ render one clip
def render_clip(name, args):
    clips, _h2t, tid_to_chain = ma.load_clips(BUNDLE)
    if name not in clips:
        raise SystemExit("no clip %s (have %s)" % (name, sorted(clips)))
    clip = clips[name]
    tag = name + args.suffix
    outdir = os.path.join(OUTROOT, tag)
    os.makedirs(outdir, exist_ok=True)
    frames = list(range(0, clip.frame_count, args.step))
    if args.max_frames and len(frames) > args.max_frames:
        sel = np.linspace(0, len(frames) - 1, args.max_frames).round().astype(int)
        frames = [frames[i] for i in sorted(set(sel))]
    print("\n=== %s: %d frames of %d (step %d), %dx%d px ==="
          % (name, len(frames), clip.frame_count, args.step, 0, args.height))
    print(clip.layout_str())

    rig = Rig(BUNDLE)
    rig.tid_to_chain = tid_to_chain
    t0 = time.time()
    offsets = rig.root_offsets(clip, frames, args.follow)
    lo, hi, clo, chi = rig.bbox_over_clip(clip, frames, offsets)
    print("  animated bbox all parts : min=%s max=%s" % (np.round(lo, 3), np.round(hi, 3)))
    print("  animated bbox character : min=%s max=%s (%.1fs)"
          % (np.round(clo, 3), np.round(chi, 3), time.time() - t0))
    fwd = np.array([0.0, 0.0, -1.0 if args.flip_z else 1.0])
    # frame on the character; keep the (possibly far-flung) weapons in view too unless asked not to
    flo, fhi = (lo, hi) if args.fit == "all" else (clo, chi)
    MVP, W, H, center, eye, near, far = camera_for(flo, fhi, args.height, args.fov, fwd,
                                                  margin=args.margin)
    print("  camera: %dx%d eye=%s target=%s fov=%.0f (fit=%s)" % (W, H, np.round(eye, 3),
                                                                 np.round(center, 3), args.fov,
                                                                 args.fit))

    names, metas = [], []
    raster = mr.rasterize_fast if args.fast else mr.rasterize
    t0 = time.time()
    for i, f in enumerate(frames):
        rig.scene.reset_pose(clip.pose(f))
        gp, gn, gu, gt = rig.posed_tris()
        if offsets:
            gp = gp - offsets[f]
        col, alp = raster(gp, gn, gu, gt, rig.tex_arrays, rig.tex_alphas,
                          MVP, W * args.ssaa, H * args.ssaa, near, verbose=False)
        col, alp = downsample(col, alp, args.ssaa, W, H)
        rgba = to_rgba(col, alp)
        p = os.path.join(outdir, "%s_%03d.png" % (tag, f))
        Image.fromarray(rgba, "RGBA").save(p)
        names.append(p)
        cov = float((alp > 0.5).mean()) * 100.0
        metas.append({"frame": f, "time": round(float(clip.times[f]), 4), "coverage_pct": cov,
                      "bbox_min": gp.min(0).round(4).tolist(), "bbox_max": gp.max(0).round(4).tolist()})
        if (i + 1) % 10 == 0 or i == 0:
            el = time.time() - t0
            print("   frame %3d/%d  cov=%.2f%%  %.2fs elapsed (%.2fs/frame)"
                  % (i + 1, len(frames), cov, el, el / (i + 1)))
    dt = time.time() - t0
    print("  %d frames in %.1fs (%.2f s/frame)" % (len(frames), dt, dt / max(1, len(frames))))

    # ---------- contact sheet
    sheet_n = min(args.sheet, len(names))
    sel = [names[i] for i in np.linspace(0, len(names) - 1, sheet_n).round().astype(int)]
    ims = [Image.open(p).convert("RGB") for p in sel]
    cols = min(4, sheet_n) if sheet_n > 3 else sheet_n
    rows = int(math.ceil(sheet_n / float(cols)))
    pad, lab = 8, 18
    cw = max(im.width for im in ims)
    ch = max(im.height for im in ims)
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + pad + lab) + pad),
                      (18, 19, 23))
    dr = ImageDraw.Draw(sheet)
    for i, (p, im) in enumerate(zip(sel, ims)):
        c, r = i % cols, i // cols
        x = pad + c * (cw + pad)
        y = pad + r * (ch + pad + lab)
        idx = names.index(p)
        dr.text((x + 2, y + 3), "frame %d   t=%.3fs" % (frames[idx], clip.times[frames[idx]]),
                fill=(235, 235, 240))
        sheet.paste(im, (x, y + lab))
    sp = os.path.join(OUTROOT, "%s_sheet.png" % tag)
    sheet.save(sp)
    print("  wrote %s (%dx%d, %d frames)" % (sp, sheet.width, sheet.height, sheet_n))

    # ---------- animated GIF
    fps = args.gif_fps
    step_frames = max(1, int(round((clip.rate * args.step) / float(fps))))
    gif_src = [names[i] for i in range(0, len(names), step_frames)]
    gifs = [composite_over_bg(np.asarray(Image.open(p).convert("RGBA"))) for p in gif_src]
    if args.gif_scale != 1.0:
        gifs = [im.resize((max(64, int(round(im.width * args.gif_scale))),
                           max(64, int(round(im.height * args.gif_scale)))), Image.LANCZOS)
                for im in gifs]
    gp_ = os.path.join(OUTROOT, "%s.gif" % tag)
    dur = int(round(1000.0 * step_frames * args.step / clip.rate))
    gifs[0].save(gp_, save_all=True, append_images=gifs[1:], duration=dur, loop=0,
                 optimize=True, disposal=2)
    print("  wrote %s (%d frames, %d ms/frame = %.1f fps)"
          % (gp_, len(gifs), dur, 1000.0 / max(1, dur)))

    # ---------- centroid motion (evidence that the render actually moves)
    arrs = [np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 127 for p in names]
    cents = []
    for a in arrs:
        ys, xs = np.nonzero(a)
        cents.append([float(xs.mean()) if len(xs) else 0.0, float(ys.mean()) if len(ys) else 0.0])
    cents = np.array(cents)
    span = (cents.max(0) - cents.min(0)) if len(cents) else np.zeros(2)
    print("  silhouette centroid travel over the clip: %.2f px x, %.2f px y" % (span[0], span[1]))

    meta = dict(clip=name, frames=frames, image_size=[W, H], sheet=sp, gif=gp_,
                layout=dict(n=clip.n, frames_total=clip.frame_count, rate=clip.rate,
                            stop_time=clip.stop_time,
                            pos=[clip.Ps, clip.Pd, clip.Pc], rot=[clip.Rs, clip.Rd, clip.Rc],
                            scl=[clip.Ss, clip.Sd, clip.Sc]),
                max_quat_norm_err=clip.rot_norm_err,
                animated_bbox=[lo.tolist(), hi.tolist()],
                camera=dict(eye=eye.tolist(), target=center.tolist(), fov=args.fov),
                centroid_travel_px=span.tolist(), per_frame=metas)
    json.dump(meta, open(os.path.join(outdir, "%s_frames.json" % tag), "w", encoding="utf-8"),
              indent=1)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--height", type=int, default=384)
    ap.add_argument("--ssaa", type=int, default=1)
    ap.add_argument("--fov", type=float, default=30.0)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--gif-fps", type=float, default=15.0)
    ap.add_argument("--gif-scale", type=float, default=1.0)
    ap.add_argument("--no-fast", dest="fast", action="store_false",
                    help="use the original per-triangle rasteriser (identical output, much slower)")
    ap.add_argument("--sheet", type=int, default=12)
    ap.add_argument("--suffix", default="", help="tag appended to every output name")
    ap.add_argument("--margin", type=float, default=1.04)
    ap.add_argument("--fit", choices=("char", "all"), default="char")
    ap.add_argument("--follow", choices=("none", "xz", "xyz"), default="none",
                    help="subtract the skeleton root's translation so a dashing clip stays in frame")
    ap.add_argument("--flip-z", action="store_true")
    args = ap.parse_args()
    names = args.clips or ([None] if not args.all else [])
    if args.all:
        names = ORDER
    if not names:
        names = [ORDER[0]]
    os.makedirs(OUTROOT, exist_ok=True)
    for nm in names:
        render_clip(nm, args)


if __name__ == "__main__":
    main()
