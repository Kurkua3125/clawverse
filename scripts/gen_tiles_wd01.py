#!/usr/bin/env python3
"""WD-01: Generate 8 new pixel art tile images for Clawverse v1."""

from PIL import Image, ImageDraw
import os

# Ensure output dirs exist
os.makedirs("/opt/clawverse/catalog/terrain", exist_ok=True)
os.makedirs("/opt/clawverse/catalog/objects", exist_ok=True)

DARK = (20, 20, 20)  # universal dark outline

# ─────────────────────────────────────────────
# Helper: isometric diamond outline (128×64)
# ─────────────────────────────────────────────
def iso_diamond_pts(w=128, h=64):
    """Return 4-corner diamond polygon points."""
    cx, cy = w // 2, h // 2
    return [(cx, 0), (w - 1, cy), (cx, h - 1), (0, cy)]


def make_terrain_base(w=128, h=64, top_color=(100, 160, 80), side_color=None):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = iso_diamond_pts(w, h)
    d.polygon(pts, fill=top_color)
    d.polygon(pts, outline=DARK)
    return img, d


# ─────────────────────────────────────────────
# TERRAIN: pond.png  128×64
# ─────────────────────────────────────────────
def gen_pond():
    img = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = iso_diamond_pts()
    # Grass base
    d.polygon(pts, fill=(110, 170, 75))
    # Water ellipse in center
    d.ellipse([38, 18, 90, 46], fill=(60, 140, 180), outline=(30, 100, 140))
    # Inner water shimmer
    d.ellipse([48, 23, 80, 41], fill=(80, 160, 200), outline=None)
    # Lily pad (dark green dot)
    d.ellipse([57, 29, 71, 37], fill=(50, 120, 60), outline=(30, 80, 40))
    # Lily pad stem dot
    d.ellipse([62, 33, 66, 36], fill=(200, 60, 60))
    # Outline
    d.polygon(pts, outline=DARK)
    img.save("/opt/clawverse/catalog/terrain/pond.png")
    print("✅ pond.png")


# ─────────────────────────────────────────────
# TERRAIN: cliff_edge_n.png  128×64
# ─────────────────────────────────────────────
def gen_cliff_edge_n():
    img = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Full grass top diamond
    pts = iso_diamond_pts()
    d.polygon(pts, fill=(110, 170, 75))
    # Dark rock face – bottom half of diamond (south face)
    cx = 64
    # Rock face polygon: left-mid, right-mid, bottom tip, slightly above bottom
    rock_pts = [(0, 32), (128, 32), (96, 64), (32, 64)]
    d.polygon(rock_pts, fill=(80, 70, 60))
    # Rock texture lines
    for y_off in [38, 44, 50, 56]:
        x_start = int(cx - (y_off - 32) * 0.9)
        x_end = int(cx + (y_off - 32) * 0.9)
        d.line([(x_start, y_off), (x_end, y_off)], fill=(60, 52, 44), width=1)
    # Grass top ridge
    d.line([(0, 32), (128, 32)], fill=(80, 130, 50), width=2)
    # Small grass tufts on top
    for x in [30, 50, 70, 90]:
        d.line([(x, 26), (x - 2, 20)], fill=(60, 140, 50), width=1)
        d.line([(x, 26), (x + 2, 20)], fill=(60, 140, 50), width=1)
    # Outline
    d.polygon(pts, outline=DARK)
    img.save("/opt/clawverse/catalog/terrain/cliff_edge_n.png")
    print("✅ cliff_edge_n.png")


# ─────────────────────────────────────────────
# OBJECT: dock_plank.png  128×64  (iso plank)
# ─────────────────────────────────────────────
def gen_dock_plank():
    img = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = iso_diamond_pts()
    # Brown base
    d.polygon(pts, fill=(140, 100, 55))
    # Plank lines (horizontal across the diamond, parallel to iso top)
    for i in range(6):
        y = 8 + i * 8
        # Clip to diamond: at height y, width = y*(64/32) for upper half, etc.
        half_h = 32
        if y <= half_h:
            half_w = int(64 * y / half_h)
        else:
            half_w = int(64 * (64 - y) / half_h)
        x0 = 64 - half_w
        x1 = 64 + half_w
        d.line([(x0, y), (x1, y)], fill=(100, 68, 30), width=1)
    # Wood grain dots
    for x in [40, 60, 80]:
        d.point((x, 28), fill=(90, 60, 25))
        d.point((x, 36), fill=(90, 60, 25))
    # Outline
    d.polygon(pts, outline=DARK)
    img.save("/opt/clawverse/catalog/objects/dock_plank.png")
    print("✅ dock_plank.png")


# ─────────────────────────────────────────────
# OBJECT: fence_wood.png  80×60
# ─────────────────────────────────────────────
def gen_fence_wood():
    img = Image.new("RGBA", (80, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Two fence posts
    post_color = (160, 115, 65)
    post_dark = (110, 75, 35)
    post_shadow = (80, 55, 25)

    def draw_post(cx, top_y, height=40):
        w = 8
        # Top face (light)
        d.rectangle([cx - w // 2, top_y, cx + w // 2, top_y + height], fill=post_color, outline=DARK)
        # Shadow right side
        d.line([(cx + w // 2, top_y + 2), (cx + w // 2, top_y + height)], fill=post_shadow, width=2)
        # Point cap
        d.polygon([(cx - w // 2, top_y), (cx, top_y - 8), (cx + w // 2, top_y)], fill=post_dark, outline=DARK)

    draw_post(18, 10, 42)
    draw_post(62, 10, 42)

    # Horizontal rails
    for y in [20, 36]:
        d.rectangle([18, y, 62, y + 5], fill=(150, 108, 58), outline=DARK)
        d.line([(19, y + 1), (61, y + 1)], fill=(180, 140, 80), width=1)  # highlight top

    img.save("/opt/clawverse/catalog/objects/fence_wood.png")
    print("✅ fence_wood.png")


# ─────────────────────────────────────────────
# OBJECT: barrel.png  60×70
# ─────────────────────────────────────────────
def gen_barrel():
    img = Image.new("RGBA", (60, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Body – rounded rectangle
    body_color = (160, 110, 60)
    body_dark  = (110, 72, 30)
    body_light = (200, 150, 90)
    # Main body
    d.ellipse([8, 8, 52, 24], fill=body_light, outline=DARK)   # top cap
    d.rectangle([8, 16, 52, 56], fill=body_color, outline=None)
    d.ellipse([8, 48, 52, 64], fill=body_dark, outline=DARK)    # bottom cap
    # Side shading (right)
    for x in range(46, 53):
        alpha = int(80 * (x - 46) / 6)
        d.line([(x, 16), (x, 56)], fill=(60, 40, 15, alpha))
    # Metal hoops
    hoop_color = (70, 70, 70)
    for y in [22, 38, 54]:
        d.ellipse([8, y - 3, 52, y + 3], fill=None, outline=hoop_color)
        d.line([(8, y), (52, y)], fill=hoop_color, width=2)
    # Outline body
    d.line([(8, 16), (8, 56)], fill=DARK, width=1)
    d.line([(52, 16), (52, 56)], fill=DARK, width=1)
    img.save("/opt/clawverse/catalog/objects/barrel.png")
    print("✅ barrel.png")


# ─────────────────────────────────────────────
# OBJECT: chest.png  70×60
# ─────────────────────────────────────────────
def gen_chest():
    img = Image.new("RGBA", (70, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    chest_brown = (150, 100, 50)
    chest_dark  = (90, 55, 20)
    chest_light = (190, 145, 80)
    gold        = (220, 180, 40)
    gold_dark   = (160, 120, 20)

    # Bottom box
    d.rectangle([5, 32, 65, 58], fill=chest_brown, outline=DARK)
    # Shadow right side
    d.rectangle([58, 33, 65, 57], fill=chest_dark)
    # Top lid (slightly curved)
    d.rectangle([5, 18, 65, 36], fill=chest_light, outline=DARK)
    d.ellipse([5, 12, 65, 36], fill=chest_light, outline=DARK)
    # Lid shadow
    d.rectangle([58, 19, 65, 35], fill=(150, 110, 55))
    # Wood planks on front
    for y in [36, 44, 52]:
        d.line([(6, y), (64, y)], fill=chest_dark, width=1)
    # Gold clasp (center)
    d.rectangle([30, 30, 40, 42], fill=gold, outline=gold_dark)
    d.rectangle([33, 34, 37, 38], fill=gold_dark)
    # Corner brackets
    for x in [5, 58]:
        d.rectangle([x, 32, x + 6, 38], fill=gold, outline=gold_dark)
        d.rectangle([x, 52, x + 6, 58], fill=gold, outline=gold_dark)

    img.save("/opt/clawverse/catalog/objects/chest.png")
    print("✅ chest.png")


# ─────────────────────────────────────────────
# OBJECT: table_wood.png  90×70
# ─────────────────────────────────────────────
def gen_table_wood():
    img = Image.new("RGBA", (90, 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    wood  = (170, 120, 65)
    dark  = (100, 65, 25)
    light = (210, 165, 100)

    # Table top – iso diamond-ish parallelogram
    top_pts = [(10, 25), (45, 10), (80, 25), (45, 40)]
    d.polygon(top_pts, fill=light, outline=DARK)
    # Wood grain lines
    for i in range(3):
        off = i * 8 - 8
        d.line([(18 + off, 30), (45 + off, 14)], fill=wood, width=1)

    # Legs (4 corners of top polygon)
    leg_h = 28
    for x, y in [(14, 28), (42, 14), (76, 28), (42, 42)]:
        d.line([(x, y), (x - 2, y + leg_h)], fill=dark, width=3)
        d.line([(x - 2, y + leg_h - 2), (x + 2, y + leg_h - 2)], fill=DARK, width=1)

    # Front face of tabletop
    side_pts = [(10, 25), (45, 40), (45, 48), (10, 33)]
    d.polygon(side_pts, fill=wood, outline=DARK)
    right_pts = [(45, 40), (80, 25), (80, 33), (45, 48)]
    d.polygon(right_pts, fill=dark, outline=DARK)

    img.save("/opt/clawverse/catalog/objects/table_wood.png")
    print("✅ table_wood.png")


# ─────────────────────────────────────────────
# OBJECT: well.png  80×100
# ─────────────────────────────────────────────
def gen_well():
    img = Image.new("RGBA", (80, 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    stone      = (150, 145, 135)
    stone_dark = (100, 95, 85)
    stone_lite = (190, 185, 175)
    wood_brown = (150, 105, 55)
    wood_dark  = (100, 68, 28)
    roof_red   = (180, 80, 50)

    # Well shaft – cylinder
    d.ellipse([15, 52, 65, 68], fill=stone, outline=DARK)           # top rim
    d.rectangle([15, 58, 65, 82], fill=stone, outline=None)
    d.ellipse([15, 72, 65, 88], fill=stone_dark, outline=DARK)      # bottom rim
    # Stone texture on shaft
    for y in [62, 70, 78]:
        d.line([(16, y), (64, y)], fill=stone_dark, width=1)
    for x in [28, 42, 56]:
        d.line([(x, 58), (x, 82)], fill=stone_dark, width=1)
    # Outline shaft sides
    d.line([(15, 58), (15, 82)], fill=DARK, width=1)
    d.line([(65, 58), (65, 82)], fill=DARK, width=1)

    # Water inside
    d.ellipse([18, 54, 62, 66], fill=(60, 130, 180), outline=(40, 100, 140))

    # Two support posts
    for x in [16, 58]:
        d.rectangle([x, 28, x + 6, 62], fill=wood_brown, outline=DARK)
        d.line([(x + 5, 29), (x + 5, 61)], fill=wood_dark, width=1)

    # Cross beam
    d.rectangle([10, 26, 70, 34], fill=wood_brown, outline=DARK)
    d.line([(11, 27), (69, 27)], fill=(200, 150, 90), width=1)

    # Rope & bucket handle
    d.line([(40, 34), (40, 54)], fill=(120, 90, 50), width=2)
    d.ellipse([34, 46, 46, 56], fill=None, outline=(80, 60, 30))

    # Roof (triangle / pitched)
    roof_pts = [(5, 28), (40, 6), (75, 28)]
    d.polygon(roof_pts, fill=roof_red, outline=DARK)
    # Roof ridge
    d.line([(5, 28), (40, 6)], fill=(220, 100, 60), width=1)
    d.line([(40, 6), (75, 28)], fill=(140, 50, 30), width=1)
    # Roof tiles
    for i in range(4):
        y = 10 + i * 5
        hw = int(35 * (y - 6) / 22)
        d.line([(40 - hw, y), (40 + hw, y)], fill=(140, 55, 30), width=1)

    img.save("/opt/clawverse/catalog/objects/well.png")
    print("✅ well.png")


# ─── Run all ───
if __name__ == "__main__":
    gen_pond()
    gen_cliff_edge_n()
    gen_dock_plank()
    gen_fence_wood()
    gen_barrel()
    gen_chest()
    gen_table_wood()
    gen_well()
    print("\nAll 8 tiles generated.")
