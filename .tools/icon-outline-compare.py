"""Build the Task-2 evidence sheet: before/after of the outline layer, drawn the way the game draws it.

Layering model (taken from the extracted scene + decompiled code, not guessed):
  scenes/ui/multiplayer_vote_icon.tscn
    [node name="MapPointVoteIcon" type="TextureRect"]  custom_minimum_size = (24,24)  expand_mode = 3
    [node name="Outline" type="TextureRect" parent="."]
        modulate = Color(0, 0, 0, 0.7529412)
        show_behind_parent = true
        anchors_preset = 15 (full rect)
  -> both textures are stretched over the SAME square rect; the outline is painted first,
     modulated to black, and the icon is composited on top.
  The bestiary dialogue icon is the same shape with modulate (0,0,0,0.502) and a 56x56 rect.

Output: .tools/icon-outline-compare.png
  rows:  vanilla ironclad | Yetannia BEFORE (duplicate) | Yetannia AFTER (derived mask)
  cols:  base texture | outline layer alone (on a mid grey card) | the two composited
  each cell is rendered at the real 24 px slot size and then magnified with NEAREST.
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
VAN = os.path.join(HERE, 'pckdump', 'out')
PKC = os.path.join(HERE, 'pckproject', 'Yetannia', 'images', 'charui')
BEFORE = os.path.join(HERE, 'icon-outline-before')

SLOT = 24          # the real TextureRect minimum size in the vote-icon scene
ZOOM = 9           # magnification for the sheet
OUTLINE_MOD = np.array([0.0, 0.0, 0.0, 0.7529412])   # modulate on the Outline node
BG = np.array([71, 78, 92, 255], np.float64)          # mid-tone map-ish backdrop


def load(p):
    return np.array(Image.open(p).convert('RGBA')).astype(np.float64)


def fit(tex, slot):
    """STRETCH_SCALE into a square rect (both textures are 1:1, so this is exact)."""
    return np.array(Image.fromarray(tex.astype(np.uint8)).resize((slot, slot), Image.LANCZOS)).astype(np.float64)


def over(dst, src):
    """src composited over dst, both straight-alpha RGBA float arrays."""
    sa = src[:, :, 3:4] / 255.0
    da = dst[:, :, 3:4] / 255.0
    oa = sa + da * (1 - sa)
    rgb = np.where(oa > 0, (src[:, :, :3] * sa + dst[:, :, :3] * da * (1 - sa)) / np.maximum(oa, 1e-6), 0)
    return np.concatenate([rgb, oa * 255.0], axis=2)


def modulate(tex, color):
    out = tex.copy()
    out[:, :, :3] *= color[:3]
    out[:, :, 3] *= color[3]
    return out


def card(size, bg):
    a = np.zeros((size, size, 4), np.float64)
    a[:, :] = bg
    return a


def render(base_png, outline_png):
    base = fit(load(base_png), SLOT)
    outl = fit(load(outline_png), SLOT)
    # the outline node is behind the parent, modulated
    stage = card(SLOT, BG)
    stage = over(stage, modulate(outl, OUTLINE_MOD))
    composite = over(stage, base)
    # the outline layer on its own, over the same backdrop
    alone = over(card(SLOT, BG), modulate(outl, OUTLINE_MOD))
    return base, alone, composite


def mag(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((SLOT * ZOOM, SLOT * ZOOM), Image.NEAREST)


rows = [
    ('vanilla ironclad', os.path.join(VAN, 'images__ui__top_panel__character_icon_ironclad.png'),
     os.path.join(VAN, 'images__ui__top_panel__character_icon_ironclad_outline.png')),
    ('Yetannia BEFORE (duplicate art)', os.path.join(PKC, 'character_icon_yetannia.png'),
     os.path.join(BEFORE, 'character_icon_yetannia_outline.png')),
    ('Yetannia AFTER (derived mask)', os.path.join(PKC, 'character_icon_yetannia.png'),
     os.path.join(PKC, 'character_icon_yetannia_outline.png')),
]

pad = 10
cols = 3
W = pad + cols * (SLOT * ZOOM + pad)
H = pad + len(rows) * (SLOT * ZOOM + pad)
sheet = Image.new('RGBA', (W, H), (26, 28, 34, 255))
for r, (label, b, o) in enumerate(rows):
    base, alone, comp = render(b, o)
    for c, cell in enumerate((base, alone, comp)):
        sheet.alpha_composite(mag(cell), (pad + c * (SLOT * ZOOM + pad), pad + r * (SLOT * ZOOM + pad)))
    print(f'row {r}: {label}')

sheet.convert('RGB').save(os.path.join(HERE, 'icon-outline-compare.png'))
print('wrote .tools/icon-outline-compare.png')
print('columns: base texture | outline layer alone | base over outline (what the game draws)')
print('rows:    vanilla ironclad | Yetannia before | Yetannia after')
