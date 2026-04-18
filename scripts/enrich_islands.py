#!/usr/bin/env python3
"""Enrich sparse islands with themed layouts for demo purposes.
Makes islands look lived-in and diverse."""

import json, os, random, math, hashlib, sys

WORLDS_DIR = '/opt/clawverse/backend/worlds'
CATALOG_DIR = '/opt/clawverse/catalog'

# Load catalog to know available objects
with open(os.path.join(CATALOG_DIR, 'catalog.json')) as f:
    catalog = json.load(f)

# Available terrain and objects from catalog
TERRAIN_TYPES = list(catalog.get('terrain', {}).keys()) if isinstance(catalog.get('terrain'), dict) else []
OBJECT_TYPES = list(catalog.get('objects', {}).keys()) if isinstance(catalog.get('objects'), dict) else []

# ── Theme definitions ──────────────────────────────────────────
# Each theme has terrain palette, object clusters, and layout style

THEMES = {
    'cozy_village': {
        'terrain': {
            'core': 'grass_plain', 'accent': ['grass_flowers', 'grass_dark', 'dirt_path'],
            'edge': ['sand_plain', 'water_shallow'],
        },
        'objects': {
            'buildings': ['house_cottage'] * 3 + ['well', 'mailbox'],
            'nature': ['tree_oak'] * 5 + ['tree_pine'] * 3 + ['flower_patch'] * 6,
            'decor': ['bench'] * 3 + ['lantern'] * 4 + ['sign_wood'] * 2 + ['fence_wood'] * 6,
            'features': ['campfire', 'barrel'] * 2 + ['pond'],
        },
        'paths': True,
    },
    'japanese_garden': {
        'terrain': {
            'core': 'grass_plain', 'accent': ['grass_dark', 'zen_sand', 'moss_stone'],
            'edge': ['sand_plain', 'water_shallow'],
        },
        'objects': {
            'buildings': ['torii_gate'],
            'nature': ['tree_oak'] * 3 + ['bamboo_cluster'] * 4 + ['bonsai'] * 3,
            'decor': ['stone_lantern'] * 5 + ['lantern'] * 3 + ['bench'] * 2,
            'features': ['koi_pond', 'fountain'] * 2 + ['pond'],
        },
        'paths': True,
    },
    'beach_paradise': {
        'terrain': {
            'core': 'sand_plain', 'accent': ['grass_plain', 'sand_shells', 'dirt_path'],
            'edge': ['water_shallow', 'water_deep'],
        },
        'objects': {
            'buildings': ['house_cottage', 'lighthouse'],
            'nature': ['tree_palm'] * 6 + ['flower_patch'] * 4,
            'decor': ['bench'] * 2 + ['lantern'] * 3 + ['dock_plank'] * 3 + ['sign_wood'],
            'features': ['campfire', 'barrel'] * 2 + ['chest'],
        },
        'paths': False,
    },
    'castle_kingdom': {
        'terrain': {
            'core': 'stone_plain', 'accent': ['castle_floor', 'castle_carpet', 'grass_dark'],
            'edge': ['stone_mossy', 'water_deep'],
        },
        'objects': {
            'buildings': ['castle_gate', 'house_cottage'],
            'nature': ['tree_oak'] * 3 + ['tree_pine'] * 2,
            'decor': ['throne', 'torch_wall'] * 3 + ['armor_stand'] * 2 + ['banner_red'] * 4 + ['lantern'] * 3,
            'features': ['chest'] * 2 + ['fountain', 'statue'],
        },
        'paths': True,
    },
    'enchanted_forest': {
        'terrain': {
            'core': 'grass_dark', 'accent': ['grass_plain', 'moss_stone', 'dirt_path'],
            'edge': ['grass_flowers', 'water_shallow'],
        },
        'objects': {
            'buildings': ['house_cottage'],
            'nature': ['tree_oak'] * 8 + ['tree_pine'] * 6 + ['bamboo_cluster'] * 3,
            'decor': ['lantern'] * 5 + ['stone_lantern'] * 3 + ['flower_patch'] * 4,
            'features': ['campfire', 'well', 'pond', 'fountain'],
        },
        'paths': True,
    },
    'space_station': {
        'terrain': {
            'core': 'metal_floor', 'accent': ['space_glass', 'stone_plain'],
            'edge': ['water_deep'],
        },
        'objects': {
            'buildings': ['control_panel'] * 2,
            'nature': ['space_plant'] * 4,
            'decor': ['antenna'] * 3 + ['robot'] * 2 + ['lantern'] * 4,
            'features': ['chest', 'barrel'] * 2,
        },
        'paths': False,
    },
    'flower_meadow': {
        'terrain': {
            'core': 'grass_flowers', 'accent': ['grass_plain', 'grass_cherry', 'dirt_path'],
            'edge': ['sand_plain', 'water_shallow'],
        },
        'objects': {
            'buildings': ['house_cottage', 'flower_gate'],
            'nature': ['tree_oak'] * 3 + ['tree_palm'] * 2 + ['garden_large'] * 3,
            'decor': ['flower_patch'] * 8 + ['bench'] * 3 + ['swing'] * 2 + ['lantern'] * 4,
            'features': ['fountain'] * 2 + ['well', 'pond'],
        },
        'paths': True,
    },
}

def generate_island_terrain(grid_size=32, theme_config=None):
    """Generate varied terrain with an island shape."""
    terrain = []
    center = grid_size / 2
    
    if not theme_config:
        theme_config = random.choice(list(THEMES.values()))['terrain']
    
    core = theme_config['core']
    accents = theme_config['accent']
    edges = theme_config['edge']
    
    for row in range(grid_size):
        for col in range(grid_size):
            dx = col - center
            dy = row - center
            dist = math.sqrt(dx*dx + dy*dy)
            
            # Island shape with some noise
            noise = random.uniform(-2, 2)
            effective_dist = dist + noise
            
            if effective_dist > 14:
                # Water edge
                tile = 'water_deep'
            elif effective_dist > 12:
                # Beach/edge
                tile = random.choice(edges)
            elif effective_dist > 10:
                # Accent zone
                tile = random.choice(accents + [core])
            else:
                # Core island
                if random.random() < 0.15:
                    tile = random.choice(accents)
                else:
                    tile = core
            
            terrain.append([col, row, 0, tile])
    
    return terrain

def place_objects_clustered(grid_size, objects_list, existing_objects=None):
    """Place objects in natural-looking clusters."""
    placed = []
    occupied = set()
    
    if existing_objects:
        for o in existing_objects:
            occupied.add((o.get('col', 0), o.get('row', 0)))
            placed.append(o)
    
    center = grid_size / 2
    
    # Shuffle and place objects
    all_objects = []
    for category, items in objects_list.items():
        all_objects.extend(items)
    
    random.shuffle(all_objects)
    
    # Create cluster centers (3-5 clusters)
    num_clusters = random.randint(3, 5)
    clusters = []
    for _ in range(num_clusters):
        cx = random.randint(5, grid_size - 5)
        cy = random.randint(5, grid_size - 5)
        # Make sure cluster center is on land
        dx = cx - center
        dy = cy - center
        if math.sqrt(dx*dx + dy*dy) < 11:
            clusters.append((cx, cy))
    
    if not clusters:
        clusters = [(int(center), int(center))]
    
    for obj_type in all_objects:
        # Pick a cluster to place near
        cx, cy = random.choice(clusters)
        
        # Try to place within cluster radius
        for _ in range(20):
            col = cx + random.randint(-4, 4)
            row = cy + random.randint(-4, 4)
            
            if col < 1 or col >= grid_size - 1 or row < 1 or row >= grid_size - 1:
                continue
            if (col, row) in occupied:
                continue
            
            # Check it's on land (not too far from center)
            dx = col - center
            dy = row - center
            if math.sqrt(dx*dx + dy*dy) > 11:
                continue
            
            placed.append({
                'col': col,
                'row': row,
                'z': 1,
                'type': obj_type,
            })
            occupied.add((col, row))
            break
    
    return placed

def add_paths(terrain, grid_size=32):
    """Add dirt paths connecting clusters."""
    center = int(grid_size / 2)
    # Simple cross-path through center
    path_tiles = set()
    
    # Horizontal path
    for col in range(5, grid_size - 5):
        row = center + random.randint(-1, 1)
        if 0 <= row < grid_size:
            path_tiles.add((col, row))
    
    # Vertical path
    for row in range(5, grid_size - 5):
        col = center + random.randint(-1, 1)
        if 0 <= col < grid_size:
            path_tiles.add((col, row))
    
    # Apply paths to terrain
    for i, t in enumerate(terrain):
        if (t[0], t[1]) in path_tiles:
            terrain[i] = [t[0], t[1], 0, 'dirt_path']
    
    return terrain

def enrich_world(world_path, theme_name=None):
    """Enrich a single world file."""
    with open(world_path) as f:
        world = json.load(f)
    
    current_objects = world.get('objects', [])
    current_terrain = world.get('terrain', [])
    grid_size = world.get('grid', {}).get('cols', 32)
    
    # Pick a theme
    if theme_name:
        theme = THEMES[theme_name]
    else:
        theme = random.choice(list(THEMES.values()))
        theme_name = [k for k, v in THEMES.items() if v == theme][0]
    
    # Only enrich if current objects are sparse (< 30)
    if len(current_objects) > 40:
        print(f"  Skipping (already {len(current_objects)} objects)")
        return False
    
    # Generate new terrain
    new_terrain = generate_island_terrain(grid_size, theme['terrain'])
    
    # Place objects
    new_objects = place_objects_clustered(grid_size, theme['objects'], current_objects)
    
    # Add paths if theme supports it
    if theme.get('paths'):
        new_terrain = add_paths(new_terrain, grid_size)
    
    # Update world
    world['terrain'] = new_terrain
    world['objects'] = new_objects
    
    # Save
    with open(world_path, 'w') as f:
        json.dump(world, f, indent=2, ensure_ascii=False)
    
    print(f"  Applied theme '{theme_name}': {len(new_objects)} objects, {len(new_terrain)} terrain tiles")
    return True

# ── Island type assignments for variety ─────────────────────
ISLAND_TYPE_MAP = {
    'Space Station Claw': ('space_station', 'mine'),
    'Castle Fortress': ('castle_kingdom', 'mine'),
    'Cherry Blossom Garden': ('japanese_garden', 'forest'),
    'Rachland': ('flower_meadow', 'farm'),
    'JiamingClawWorld': ('cozy_village', 'farm'),
    'Ernieland': ('beach_paradise', 'fish'),
    'Viclaw Land': ('enchanted_forest', 'forest'),
    'Jensen Daijobu': ('japanese_garden', 'farm'),
    'Crazy Rabbit': ('cozy_village', 'farm'),
    'aranya': ('flower_meadow', 'farm'),
    'Abby\'s Clawverse': ('beach_paradise', 'fish'),
    'My Clawverse': ('cozy_village', 'farm'),  # 362c
    'bbbbbb': ('enchanted_forest', 'forest'),
    'Hello World': ('cozy_village', 'farm'),
    'Sunland': ('beach_paradise', 'fish'),
    'Kaka': ('castle_kingdom', 'mine'),
    'superluna\'s world': ('flower_meadow', 'farm'),
    'RedIsland': ('enchanted_forest', 'forest'),
    'Malden Island': ('japanese_garden', 'farm'),
    '01world': ('cozy_village', 'farm'),
    'Test': ('cozy_village', 'farm'),
}

def main():
    # Process each world
    import sqlite3
    db_path = '/opt/clawverse/backend/clawverse.db'
    
    for fname in sorted(os.listdir(WORLDS_DIR)):
        if not fname.endswith('.json'):
            continue
        if fname in ('sprint1_backup.json', 'test_backup.json', 'magical_land.json', 'untitled.json'):
            continue
        
        wid = fname.replace('.json', '')
        fpath = os.path.join(WORLDS_DIR, fname)
        
        with open(fpath) as f:
            world = json.load(f)
        
        name = world.get('meta', {}).get('name', '?')
        num_objs = len(world.get('objects', []))
        
        print(f"\n{wid} ({name}): {num_objs} objects")
        
        # Skip already rich islands
        if name in ('Genspark', "link's land") or num_objs > 40:
            print(f"  Skipping (rich enough)")
            continue
        
        # Get theme assignment
        theme_name = None
        island_type = 'farm'
        if name in ISLAND_TYPE_MAP:
            theme_name, island_type = ISLAND_TYPE_MAP[name]
        else:
            # Random assignment
            theme_name = random.choice(list(THEMES.keys()))
            types = ['farm', 'farm', 'farm', 'fish', 'mine', 'forest']
            island_type = random.choice(types)
        
        enrich_world(fpath, theme_name)
        
        # Update island_type in SQLite
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("UPDATE worlds SET island_type=? WHERE id=?", (island_type, wid))
            conn.commit()
            
            # Also persist world JSON to SQLite
            with open(fpath) as f:
                data_json = f.read()
            conn.execute("UPDATE worlds SET data_json=? WHERE id=?", (data_json, wid))
            conn.commit()
            conn.close()
            print(f"  Updated SQLite: island_type={island_type}")
        except Exception as e:
            print(f"  SQLite error: {e}")
    
    print("\n✅ Done! Restart backend to see changes.")

if __name__ == '__main__':
    main()
