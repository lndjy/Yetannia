# model-anim-checkfast.py -- must rasterize_fast() match rasterize() bit-for-bit-ish?
# usage: python .tools/model-anim-checkfast.py [clip] [frame] [height]
import importlib.util
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def _imp(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, HERE)
rr = _imp("model_anim_render", os.path.join(HERE, "model-anim-render.py"))
mr, ma = rr.mr, rr.ma

clipname = sys.argv[1] if len(sys.argv) > 1 else "zd_daiji"
frame = int(sys.argv[2]) if len(sys.argv) > 2 else 20
height = int(sys.argv[3]) if len(sys.argv) > 3 else 384

clips, _a, _b = ma.load_clips(rr.BUNDLE)
clip = clips[clipname]
rig = rr.Rig(rr.BUNDLE)
frames = [0, clip.frame_count // 2, clip.frame_count - 1]
lo, hi, clo, chi = rig.bbox_over_clip(clip, frames)
MVP, W, H, center, eye, near, far = rr.camera_for(clo, chi, height, 30.0,
                                                  np.array([0.0, 0.0, 1.0]), margin=1.04)
print("camera %dx%d near=%.4f" % (W, H, near))
rig.scene.reset_pose(clip.pose(frame))
gp, gn, gu, gt = rig.posed_tris()
print("triangles: %d" % len(gp))
t = time.time()
c1, a1 = mr.rasterize(gp, gn, gu, gt, rig.tex_arrays, rig.tex_alphas, MVP, W, H, near,
                      verbose=False)
t1 = time.time() - t
t = time.time()
c2, a2 = mr.rasterize_fast(gp, gn, gu, gt, rig.tex_arrays, rig.tex_alphas, MVP, W, H, near,
                           verbose=False)
t2 = time.time() - t
print("slow %.2fs   fast %.2fs   speedup %.1fx" % (t1, t2, t1 / max(t2, 1e-9)))
da = np.abs(a1 - a2)
dc = np.abs(c1 - c2)
print("alpha: max abs diff %.3e, pixels differing >0.02: %d (%.3f%% of frame)"
      % (da.max(), int((da > 0.02).sum()), 100.0 * (da > 0.02).mean()))
print("color: max abs diff %.3e on covered pixels (%.5f%% differ >0.02)"
      % (dc[da < 0.02].max() if (da < 0.02).any() else -1,
         100.0 * (dc > 0.02).mean()))
