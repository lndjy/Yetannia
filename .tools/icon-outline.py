"""Generate a character-icon outline the way the base game's own outlines are made.

WHAT THE VANILLA OUTLINE LAYER IS (measured, not guessed)
---------------------------------------------------------
Extracted from SlayTheSpire2.pck (see dump.gd) and compared pixel by pixel with its
character_icon_<id>.png counterpart:

  * same canvas size as the icon (88x88 for all five playable characters, 72x72 for the
    deprecated placeholder);
  * RGB is pure white EVERYWHERE (exactly one distinct colour across the whole texture,
    share 1.000) - the shape lives entirely in the alpha channel, and the alpha is binary
    (0 or 255, no soft edge);
  * the alpha shape is the icon's own alpha silhouette, FILLED, and grown by a few pixels:
    the best-fitting kernel over the seven vanilla pairs is a Euclidean disc,
    r = 4 px at 88 px and r = 3 px at 72 px, i.e. ~4.5% of the icon edge. Fits:
    ironclad 0.988, silent 0.977, defect 0.989, regent 0.981 (square r=3),
    necrobinder 0.988, random_character 0.983, deprecated 0.981 (IoU).

So the layer is a white "sticker" mask that the UI draws BEHIND the icon
(modulate black 0.5-0.75, show_behind_parent - see scenes/ui/multiplayer_vote_icon.tscn and
the Icon/Outline node in the bestiary scene), giving the icon a dark traced border.

This script reimplements exactly that: same size, white RGB, binary alpha,
dilate(alpha > threshold, disc(r)) with r = round(4/88 * size).

usage:
  python .tools/icon-outline.py selftest                 # reproduce the vanilla outlines
  python .tools/icon-outline.py make <icon.png> <out.png>
"""
import os
import sys
import numpy as np
from PIL import Image

# Measured from the seven vanilla icon/outline pairs: a disc of radius 4 at 88 px.
STROKE_RATIO = 4.0 / 88.0
# The icons carry a soft 1-2 px alpha fringe (alpha=1) that is NOT part of the silhouette;
# thresholding above it is what makes the fit sharp (alpha>0 overshoots by ~600 px on ironclad).
ALPHA_THRESHOLD = 8


def disc(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r + 0.5


def dilate(mask, kernel):
    r = kernel.shape[0] // 2
    h, w = mask.shape
    pad = np.pad(mask, r)
    out = np.zeros_like(mask)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if kernel[dy + r, dx + r]:
                out |= pad[r + dy:r + dy + h, r + dx:r + dx + w]
    return out


def outline_of(icon_path):
    """-> (RGBA uint8 array of the white outline, (w, h), r used)"""
    im = Image.open(icon_path).convert('RGBA')
    a = np.array(im)[:, :, 3]
    w, h = im.size
    r = max(1, int(round(STROKE_RATIO * max(w, h))))
    mask = dilate(a > ALPHA_THRESHOLD, disc(r))
    out = np.zeros((h, w, 4), np.uint8)
    out[:, :, :3] = 255
    out[:, :, 3] = np.where(mask, 255, 0)
    return out, (w, h), r


def make(icon_path, out_path):
    arr, size, r = outline_of(icon_path)
    Image.fromarray(arr, 'RGBA').save(out_path)
    print(f'{out_path}: {size[0]}x{size[1]} white + binary alpha, disc r={r} '
          f'({100.0 * r / max(size):.1f}% of the edge), opaque px={int((arr[:, :, 3] > 0).sum())}')


def selftest():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, 'pckdump', 'out')
    print(f'{"icon":22} {"size":>5} {"r":>2} {"IoU vs vanilla":>15} {"ours-only":>9} {"vanilla-only":>12}')
    for n in ['ironclad', 'silent', 'defect', 'regent', 'necrobinder', 'random_character',
              'deprecated_character']:
        base = os.path.join(out, f'images__ui__top_panel__character_icon_{n}.png')
        real = os.path.join(out, f'images__ui__top_panel__character_icon_{n}_outline.png')
        if not (os.path.exists(base) and os.path.exists(real)):
            print(f'{n:22} (not dumped)')
            continue
        arr, size, r = outline_of(base)
        mine = arr[:, :, 3] > 127
        theirs = np.array(Image.open(real).convert('RGBA'))[:, :, 3] > 127
        inter = int((mine & theirs).sum())
        union = int((mine | theirs).sum())
        print(f'{n:22} {size[0]:>5} {r:>2} {inter / union:>15.4f} '
              f'{int((mine & ~theirs).sum()):>9} {int((theirs & ~mine).sum()):>12}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    if cmd == 'selftest':
        selftest()
    elif cmd == 'make':
        make(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
