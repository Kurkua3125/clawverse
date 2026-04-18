"""Generate isometric thumbnail images for island worlds."""
import json, os, math
from PIL import Image, ImageDraw

# Tile colors for isometric rendering
TILE_COLORS = {
    'water_deep': (30, 80, 140),
    'water_shallow': (50, 120, 180),
    'sand_plain': (220, 200, 140),
    'sand_shells': (210, 190, 130),
    'grass_plain': (80, 160, 80),
    'grass_dark': (60, 130, 60),
    'grass_flowers': (90, 170, 100),
    'flowers_wild': (140, 180, 100),
    'dirt_path': (160, 120, 70),
    'stone_plain': (140, 140, 140),
    'stone_boulder': (120, 120, 120),
}

OBJECT_COLORS = {
    'tree_oak': (40, 120, 40),
    'tree_pine': (30, 100, 50),
    'tree_palm': (60, 140, 50),
    'house_cottage': (180, 100, 60),
    'campfire': (220, 140, 40),
    'lantern': (255, 200, 80),
    'flower_patch': (220, 120, 160),
    'lighthouse': (200, 200, 200),
    'well': (100, 80, 60),
    'pond': (60, 130, 200),
    'bench': (140, 100, 60),
    'sign_wood': (160, 120, 60),
    'fence_wood': (140, 110, 60),
    'barrel': (120, 80, 40),
    'rock_big': (110, 110, 110),
    'mailbox': (100, 100, 180),
}

def iso_to_screen(col, row, tile_w=8, tile_h=4):
    """Convert isometric tile coords to screen pixel coords."""
    sx = (col - row) * tile_w // 2
    sy = (col + row) * tile_h // 2
    return sx, sy

def generate_thumbnail(world_data, width=320, height=200):
    """Generate a thumbnail image for a world. Returns PIL Image."""
    terrain = world_data.get('terrain', [])
    objects = world_data.get('objects', [])
    
    if not terrain:
        # Empty world — nice placeholder: ocean gradient + mini island + ripples
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)

        # 1. Vertical gradient: deep blue top → lighter blue-teal bottom
        top_color = (15, 25, 60)
        bot_color = (25, 60, 100)
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(top_color[0] + (bot_color[0] - top_color[0]) * t)
            g = int(top_color[1] + (bot_color[1] - top_color[1]) * t)
            b = int(top_color[2] + (bot_color[2] - top_color[2]) * t)
            draw.line([(0, y), (width - 1, y)], fill=(r, g, b))

        # 2. Small isometric island in center (5x5 diamond of sand/grass)
        cx, cy = width // 2, height // 2
        tile_w, tile_h = 10, 5  # pixel size per tile

        island_tiles = []
        for dc in range(-2, 3):
            for dr in range(-2, 3):
                if abs(dc) + abs(dr) <= 2:
                    island_tiles.append((dc, dr))

        for dc, dr in island_tiles:
            sx = cx + (dc - dr) * tile_w // 2
            sy = cy + (dc + dr) * tile_h // 2
            dist = abs(dc) + abs(dr)
            # Edge tiles = sand, inner tiles = grass
            if dist >= 2:
                color = (220, 200, 140)  # sand
            elif dist == 1:
                color = (80, 160, 80)  # grass
            else:
                color = (60, 140, 60)  # darker grass center
            diamond = [
                (sx, sy - tile_h),
                (sx + tile_w, sy),
                (sx, sy + tile_h),
                (sx - tile_w, sy),
            ]
            draw.polygon(diamond, fill=color)

        # Small dark-green dot in center as a tree
        draw.ellipse([cx - 3, cy - 6, cx + 3, cy], fill=(40, 110, 40))

        # 3. Water ripple arcs around the island
        ripple_color = (45, 90, 140)
        for offset, radius in [(30, 38), (40, 50), (52, 44)]:
            # Draw arcs as thin ellipses at various positions around island
            for angle_start in [200, 330, 80]:
                rx = cx + int(offset * math.cos(math.radians(angle_start)))
                ry = cy + int(offset * 0.5 * math.sin(math.radians(angle_start)))
                draw.arc(
                    [rx - radius, ry - radius // 3, rx + radius, ry + radius // 3],
                    start=angle_start, end=angle_start + 60,
                    fill=ripple_color, width=1,
                )

        return img
    
    # Calculate bounds
    tile_w, tile_h = 8, 4
    
    # Find terrain extent
    cols = [t[0] for t in terrain]
    rows = [t[1] for t in terrain]
    min_col, max_col = min(cols), max(cols)
    min_row, max_row = min(rows), max(rows)
    
    # Calculate screen bounds
    corners = [
        iso_to_screen(min_col, min_row, tile_w, tile_h),
        iso_to_screen(max_col, min_row, tile_w, tile_h),
        iso_to_screen(min_col, max_row, tile_w, tile_h),
        iso_to_screen(max_col, max_row, tile_w, tile_h),
    ]
    sx_min = min(c[0] for c in corners) - tile_w
    sx_max = max(c[0] for c in corners) + tile_w
    sy_min = min(c[1] for c in corners) - tile_h
    sy_max = max(c[1] for c in corners) + tile_h * 2
    
    world_w = sx_max - sx_min
    world_h = sy_max - sy_min
    
    # Scale to fit
    scale = min(width / world_w, height / world_h) * 0.9
    offset_x = (width - world_w * scale) / 2 - sx_min * scale
    offset_y = (height - world_h * scale) / 2 - sy_min * scale
    
    # Create image with dark ocean background
    img = Image.new('RGB', (width, height), (15, 30, 60))
    draw = ImageDraw.Draw(img)
    
    tw = max(2, int(tile_w * scale))
    th = max(1, int(tile_h * scale))
    
    # Draw terrain
    for t in terrain:
        col, row, z, tile_type = t[0], t[1], t[2], t[3]
        sx, sy = iso_to_screen(col, row, tile_w, tile_h)
        px = int(sx * scale + offset_x)
        py = int(sy * scale + offset_y)
        
        color = TILE_COLORS.get(tile_type, (80, 160, 80))
        
        # Draw isometric diamond
        diamond = [
            (px, py - th),           # top
            (px + tw, py),            # right
            (px, py + th),            # bottom
            (px - tw, py),            # left
        ]
        draw.polygon(diamond, fill=color)
    
    # Draw objects as slightly raised colored dots
    for obj in objects:
        col, row = obj.get('col', 0), obj.get('row', 0)
        obj_type = obj.get('type', '')
        sx, sy = iso_to_screen(col, row, tile_w, tile_h)
        px = int(sx * scale + offset_x)
        py = int(sy * scale + offset_y) - max(1, int(2 * scale))
        
        color = OBJECT_COLORS.get(obj_type, (160, 120, 80))
        r = max(2, int(3 * scale))
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color)
    
    return img

def generate_and_save(world_id, world_data, output_dir):
    """Generate thumbnail and save as PNG. Returns file path."""
    os.makedirs(output_dir, exist_ok=True)
    img = generate_thumbnail(world_data)
    path = os.path.join(output_dir, f'{world_id}.png')
    img.save(path, 'PNG', optimize=True)
    return path

def regenerate_all(db_module, output_dir):
    """Regenerate thumbnails for all worlds."""
    worlds = db_module.list_worlds(limit=100)
    count = 0
    for w in worlds:
        world_data = db_module.load_world(w['id'])
        if world_data:
            generate_and_save(w['id'], world_data, output_dir)
            count += 1
    return count
