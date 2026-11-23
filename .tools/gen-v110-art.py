# Generates placeholder art for the v1.1.0 additions (two event portraits + one relic icon pair).
# Deliberately simple flat-colour compositions: enough to tell the scenes/relic apart and to verify the
# asset pipeline, to be replaced by hand-painted art later.
import math
import os
from PIL import Image, ImageDraw, ImageFilter

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
IMG = os.path.join(ROOT, ".tools", "pckproject", "Yetannia", "images")


def weld(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def radial_glow(size, center, color, radius):
    """Additive-ish soft glow layer."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 28
    for i in range(steps, 0, -1):
        t = i / steps
        r = radius * t
        alpha = int(48 * (1 - t) ** 1.6)
        d.ellipse(
            [center[0] - r, center[1] - r, center[0] + r, center[1] + r],
            fill=(color[0], color[1], color[2], alpha),
        )
    return layer.filter(ImageFilter.GaussianBlur(radius * 0.08))


def memory_prophet():
    size = (1024, 1408)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    glow = radial_glow(size, (512, 760), (90, 150, 255), 520)
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)

    # cloak silhouette
    d.polygon(
        [(512, 300), (300, 430), (235, 1080), (330, 1340), (512, 1370), (694, 1340),
         (789, 1080), (724, 430)],
        fill=(38, 34, 56, 255),
    )
    # inner cloak shading
    d.polygon(
        [(512, 350), (356, 470), (312, 1060), (388, 1290), (512, 1310), (636, 1290),
         (712, 1060), (668, 470)],
        fill=(52, 47, 78, 255),
    )
    # hood
    d.ellipse([382, 250, 642, 560], fill=(30, 27, 45, 255))
    d.ellipse([404, 276, 620, 520], fill=(60, 54, 88, 255))
    # face shadow
    d.ellipse([440, 320, 584, 500], fill=(26, 22, 36, 255))
    # blue hair strands spilling out of the hood
    for i, x in enumerate((430, 452, 476, 548, 574, 596)):
        d.polygon(
            [(x, 300 + i % 2 * 14), (x + 12, 330), (x + 4, 470 + i * 18), (x - 8, 440)],
            fill=(96, 168, 255, 210),
        )
    # a hint of two pale eyes inside the shadow
    d.ellipse([474, 392, 500, 408], fill=(190, 225, 255, 235))
    d.ellipse([524, 392, 550, 408], fill=(190, 225, 255, 235))
    # hands stroking the cloak
    d.ellipse([404, 846, 500, 918], fill=(214, 200, 205, 255))
    d.ellipse([524, 846, 620, 918], fill=(214, 200, 205, 255))
    # faint sigil above the head
    for k in range(6):
        a = math.radians(60 * k)
        x = 512 + int(80 * math.cos(a))
        y = 178 + int(80 * math.sin(a))
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(150, 210, 255, 190))
    img.save(weld(os.path.join(IMG, "events", "memory_prophet.png")))
    print("memory_prophet", img.size)


def ritual_of_harmony():
    size = (1024, 1408)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    # two energy fields: order (blue-gold) left, chaos (dark crimson) right
    img = Image.alpha_composite(img, radial_glow(size, (330, 720), (120, 180, 255), 470))
    img = Image.alpha_composite(img, radial_glow(size, (700, 720), (150, 40, 70), 470))
    d = ImageDraw.Draw(img)

    # floor
    d.ellipse([150, 1030, 880, 1230], fill=(24, 22, 30, 255))
    # dais steps
    for i, inset in enumerate((0, 40, 80)):
        d.ellipse([300 + inset, 1030 + i * 26, 730 - inset, 1120 + i * 32],
                  fill=(44, 42, 56, 255), outline=(84, 80, 104, 255), width=3)
    # ritual circle
    d.ellipse([352, 940, 676, 1090], outline=(130, 190, 255, 220), width=6)
    d.ellipse([392, 972, 636, 1062], outline=(255, 210, 120, 200), width=3)
    # left order pillar: rising blue-gold light
    for k in range(7):
        x = 250 + k * 9
        d.line([(x, 1040), (x + 26, 520 - k * 24)], fill=(120, 190, 255, 60 + k * 12), width=4)
    # right chaos pillar: writhing dark tendrils
    for k in range(7):
        x = 700 + k * 8
        pts = []
        for s in range(0, 24):
            t = s / 23.0
            pts.append((x + int(24 * math.sin(t * 7 + k)), int(1040 - t * 480)))
        d.line(pts, fill=(150, 50, 80, 70 + k * 10), width=5)
    # central figure silhouette (the player, small)
    d.polygon([(512, 700), (472, 760), (460, 980), (512, 1010), (564, 980), (552, 760)],
              fill=(30, 28, 40, 255))
    d.ellipse([486, 650, 538, 710], fill=(30, 28, 40, 255))
    img.save(weld(os.path.join(IMG, "events", "ritual_of_harmony.png")))
    print("ritual_of_harmony", img.size)


def relic_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    # round bronze medallion
    d.ellipse([s * 0.05, s * 0.05, s * 0.95, s * 0.95], fill=(56, 42, 66, 255),
              outline=(196, 158, 92, 255), width=max(2, s // 32))
    # two interlocking chain links (the "pact")
    for cx, cy, col in ((s * 0.40, s * 0.48, (214, 178, 110, 255)), (s * 0.60, s * 0.56, (176, 142, 84, 255))):
        d.ellipse([cx - s * 0.17, cy - s * 0.11, cx + s * 0.17, cy + s * 0.11],
                  outline=col, width=max(2, s // 24))
    # small blue gem at the top
    d.ellipse([s * 0.44, s * 0.16, s * 0.56, s * 0.28], fill=(120, 190, 255, 255),
              outline=(220, 240, 255, 255), width=1)
    return img


def main():
    memory_prophet()
    ritual_of_harmony()
    small = relic_icon(64)
    small.save(weld(os.path.join(IMG, "relics", "xinans_pact.png")))
    big = relic_icon(256).resize((256, 256), Image.LANCZOS)
    big.save(weld(os.path.join(IMG, "relics_big", "xinans_pact.png")))
    print("relic icons written")


if __name__ == "__main__":
    main()
