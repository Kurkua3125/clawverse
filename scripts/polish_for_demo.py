#!/usr/bin/env python3
"""Polish islands for demo: rename test islands, create spectacular showcase islands."""
import json, os, random, math, time, sqlite3, hashlib

WORLDS_DIR = '/opt/clawverse/backend/worlds'
DB_PATH = '/opt/clawverse/backend/clawverse.db'
CATALOG_DIR = '/opt/clawverse/catalog'

# Load catalog
with open(os.path.join(CATALOG_DIR, 'catalog.json')) as f:
    catalog = json.load(f)

# ── Step 1: Rename test/ugly names ────────────────────────────
RENAMES = {
    'default': {'name': 'Claw Island', 'owner_name': 'Eric J'},  # was "Test"
    'bbbbbb': 'Emerald Woods',
    '01world': 'Pixel Village',
    'My Clawverse': 'Coral Bay',  # duplicate name
    '🐮🐮': 'Galaxy Station',
}

# Better bios for display
BIOS = {
    'default': 'The original Clawverse island. Where it all began.',
    'ac4163459b8f': 'A dazzling metropolis of gold and neon. The Vegas of Clawverse.',
    'd8659f2f067c': 'A sprawling world of adventure and discovery.',
    'ecddd6186a6c': 'A tranquil Japanese garden with torii gates and koi ponds.',
    '78820b5f58a4': 'A high-tech space station orbiting the Clawverse.',
    '96bd33c64af9': 'A medieval fortress with banners, thrones, and armored guards.',
    '60dd3f3795ee': 'A colorful paradise filled with flowers, waterfalls, and hidden treasures.',
    '12a568c3d9c0': 'A tropical beach hideaway with palm trees and ocean views.',
}

def rename_islands():
    conn = sqlite3.connect(DB_PATH)
    
    for wid_or_name, new_info in RENAMES.items():
        if isinstance(new_info, dict):
            new_name = new_info['name']
        else:
            new_name = new_info
        
        # Find the world file
        if os.path.exists(os.path.join(WORLDS_DIR, f'{wid_or_name}.json')):
            wid = wid_or_name
        else:
            # Search by name
            wid = None
            for f in os.listdir(WORLDS_DIR):
                if not f.endswith('.json'):
                    continue
                with open(os.path.join(WORLDS_DIR, f)) as fh:
                    d = json.load(fh)
                if d.get('meta', {}).get('name') == wid_or_name:
                    wid = f.replace('.json', '')
                    break
            if not wid:
                print(f"  ⚠ Could not find island: {wid_or_name}")
                continue
        
        fpath = os.path.join(WORLDS_DIR, f'{wid}.json')
        with open(fpath) as fh:
            world = json.load(fh)
        
        old_name = world.get('meta', {}).get('name', '?')
        world.setdefault('meta', {})['name'] = new_name
        
        with open(fpath, 'w') as fh:
            json.dump(world, fh, indent=2, ensure_ascii=False)
        
        # Update SQLite
        data_json = json.dumps(world, ensure_ascii=False)
        conn.execute("UPDATE worlds SET name=?, data_json=? WHERE id=?", (new_name, data_json, wid))
        print(f"  ✅ Renamed '{old_name}' → '{new_name}' (id={wid})")
    
    conn.commit()
    
    # Update bios
    for wid, bio in BIOS.items():
        conn.execute("""
            INSERT OR REPLACE INTO island_story (world_id, bio, daily_message, updated_at)
            VALUES (?, ?, '', datetime('now'))
        """, (wid, bio))
        print(f"  ✅ Updated bio for {wid}")
    
    conn.commit()
    conn.close()

# ── Step 2: Create spectacular showcase islands ───────────────

# AI-generated objects available in catalog
AI_OBJECTS = [f for f in os.listdir(os.path.join(CATALOG_DIR, 'objects')) 
              if f.startswith('ai_') and f.endswith('.png')]
AI_OBJECT_NAMES = [f.replace('.png', '') for f in AI_OBJECTS]

# Regular objects
REGULAR_OBJECTS = ['tree_oak', 'tree_pine', 'tree_palm', 'house_cottage', 'fountain',
                   'lantern', 'campfire', 'flower_patch', 'bench', 'well', 'lighthouse',
                   'barrel', 'chest', 'statue', 'sign_wood', 'fence_wood', 'pond',
                   'garden_large', 'bridge_wood', 'rock_big', 'mailbox', 'swing',
                   'torii_gate', 'stone_lantern', 'bonsai', 'koi_pond', 'bamboo_cluster',
                   'throne', 'torch_wall', 'armor_stand', 'banner_red', 'castle_gate',
                   'control_panel', 'antenna', 'robot', 'space_plant',
                   'sofa', 'tv', 'bookcase', 'dining_table', 'lamp_floor']

def create_spectacular_island(world_id, name, owner_name, theme_objects, terrain_base, 
                               island_type='farm', obj_count=200, bio=''):
    """Create a new spectacular island from scratch."""
    grid_size = 32
    center = grid_size / 2
    
    # Generate terrain
    terrain = []
    for row in range(grid_size):
        for col in range(grid_size):
            dx = col - center
            dy = row - center
            dist = math.sqrt(dx*dx + dy*dy)
            noise = random.uniform(-1.5, 1.5)
            effective_dist = dist + noise
            
            if effective_dist > 14:
                tile = 'water_deep'
            elif effective_dist > 12.5:
                tile = random.choice(['water_shallow', 'sand_plain'])
            elif effective_dist > 11:
                tile = random.choice(['sand_plain', terrain_base])
            else:
                if random.random() < 0.2:
                    accents = {
                        'grass_plain': ['grass_flowers', 'grass_dark', 'dirt_path', 'grass_cherry'],
                        'stone_plain': ['castle_floor', 'castle_carpet', 'moss_stone'],
                        'metal_floor': ['space_glass', 'stone_plain'],
                        'sand_plain': ['grass_plain', 'sand_shells', 'dirt_path'],
                        'grass_dark': ['moss_stone', 'grass_plain', 'dirt_path'],
                        'zen_sand': ['grass_dark', 'moss_stone', 'bamboo_floor'],
                    }
                    tile = random.choice(accents.get(terrain_base, ['grass_flowers']))
                else:
                    tile = terrain_base
            terrain.append([col, row, 0, tile])
    
    # Place objects densely
    objects = []
    occupied = set()
    
    # Create multiple clusters with high density
    num_clusters = random.randint(5, 8)
    clusters = []
    for _ in range(num_clusters):
        cx = random.randint(4, grid_size - 4)
        cy = random.randint(4, grid_size - 4)
        dx = cx - center
        dy = cy - center
        if math.sqrt(dx*dx + dy*dy) < 12:
            clusters.append((cx, cy))
    
    placed = 0
    attempts = 0
    while placed < obj_count and attempts < obj_count * 5:
        attempts += 1
        cx, cy = random.choice(clusters)
        col = cx + random.randint(-5, 5)
        row = cy + random.randint(-5, 5)
        
        if col < 1 or col >= grid_size - 1 or row < 1 or row >= grid_size - 1:
            continue
        if (col, row) in occupied:
            continue
        dx = col - center
        dy = row - center
        if math.sqrt(dx*dx + dy*dy) > 12:
            continue
        
        obj_type = random.choice(theme_objects)
        objects.append({'col': col, 'row': row, 'z': 1, 'type': obj_type})
        occupied.add((col, row))
        placed += 1
    
    world = {
        'meta': {
            'name': name,
            'version': 1,
            'created': '2026-03-20T00:00:00Z',
            'theme': 'default',
        },
        'grid': {'cols': grid_size, 'rows': grid_size, 'maxZ': 8},
        'terrain': terrain,
        'objects': objects,
    }
    
    # Save world file
    fpath = os.path.join(WORLDS_DIR, f'{world_id}.json')
    with open(fpath, 'w') as f:
        json.dump(world, f, indent=2, ensure_ascii=False)
    
    # Save to SQLite
    conn = sqlite3.connect(DB_PATH)
    data_json = json.dumps(world, ensure_ascii=False)
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # Create user for the island
    user_id = hashlib.sha256(f'{owner_name}@clawverse.ai'.lower().encode()).hexdigest()[:12]
    
    conn.execute("""
        INSERT OR REPLACE INTO worlds (id, name, owner, data_json, island_type, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (world_id, name, user_id, data_json, island_type, now, now))
    
    # Ensure user exists
    conn.execute("""
        INSERT OR IGNORE INTO users (id, email, name, avatar, island_name, created_at, last_login)
        VALUES (?, ?, ?, '🦞', ?, ?, ?)
    """, (user_id, f'{owner_name.lower().replace(" ", "")}@clawverse.ai', owner_name, name, now, now))
    
    # Set progress/level
    level = max(1, obj_count // 30)
    xp = random.randint(0, level * 100)
    conn.execute("""
        INSERT OR REPLACE INTO user_progress (world_id, level, xp, tiles_placed, objects_placed, 
                                              visits_received, achievements_json, shells, total_earned, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, '[]', ?, ?, ?)
    """, (world_id, level, xp, len(terrain), len(objects), random.randint(5, 50), 
          random.randint(500, 5000), random.randint(1000, 10000), now))
    
    # Set bio
    if bio:
        conn.execute("""
            INSERT OR REPLACE INTO island_story (world_id, bio, daily_message, updated_at)
            VALUES (?, ?, '', ?)
        """, (world_id, bio, now))
    
    conn.commit()
    conn.close()
    
    print(f"  ✅ Created '{name}' by {owner_name}: {len(objects)} objects, type={island_type}")

def main():
    print("=== Step 1: Rename test islands ===")
    rename_islands()
    
    print("\n=== Step 2: Create spectacular showcase islands ===")
    
    # Casino/Vegas themed objects (from Genspark island style)
    casino_objects = [o for o in AI_OBJECT_NAMES if any(x in o.lower() for x in 
        ['casino', 'dice', 'gold', 'neon', 'slot', 'roulette', 'poker', 'diamond', 
         'champagne', 'luxury', 'vegas', 'jackpot', 'crown', 'throne', 'lion',
         'dollar', 'treasure', 'vault', 'palace', 'ferrari', 'limousine', 'yacht'])]
    
    # World landmark objects
    landmark_objects = [o for o in AI_OBJECT_NAMES if any(x in o.lower() for x in
        ['eiffel', 'statue_of_liberty', 'colosseum', 'sphinx', 'taj', 'tokyo_tower',
         'big_ben', 'sydney', 'burj', 'pagoda', 'empire_state', 'dubai'])]
    
    # Golden/sparkly objects  
    golden_objects = [o for o in AI_OBJECT_NAMES if any(x in o.lower() for x in
        ['golden', 'gold', 'brilliant', 'sparkl', 'star', 'cluster', 'letter'])]
    
    # Colorful/fun objects
    fun_objects = [o for o in AI_OBJECT_NAMES if any(x in o.lower() for x in
        ['rainbow', 'neon', 'disco', 'flamingo', 'showgirl', 'heart', 'guitar',
         'microphone', 'martini', 'playing_card', 'horseshoe'])]
    
    print(f"  Found {len(casino_objects)} casino, {len(landmark_objects)} landmark, {len(golden_objects)} golden, {len(fun_objects)} fun objects")
    
    # ── Showcase Island 1: "Neon Paradise" — Over-the-top casino/entertainment ──
    neon_objects = (casino_objects + fun_objects + golden_objects + 
                    ['fountain'] * 10 + ['lantern'] * 8 + ['campfire'] * 5 + ['statue'] * 5)
    if neon_objects:
        create_spectacular_island(
            world_id='demo_neon_paradise',
            name='Neon Paradise',
            owner_name='Neon King',
            theme_objects=neon_objects,
            terrain_base='stone_plain',
            island_type='mine',
            obj_count=250,
            bio='The most extravagant island in the Clawverse. Neon, gold, and pure excess.'
        )
    
    # ── Showcase Island 2: "World Tour" — Global landmarks ──
    world_objects = (landmark_objects + ['fountain'] * 8 + ['tree_oak'] * 5 + 
                    ['tree_palm'] * 5 + ['lantern'] * 6 + ['flower_patch'] * 8 +
                    ['bridge_wood'] * 3 + ['bench'] * 4)
    if world_objects:
        create_spectacular_island(
            world_id='demo_world_tour',
            name='World Tour',
            owner_name='Atlas',
            theme_objects=world_objects,
            terrain_base='grass_plain',
            island_type='farm',
            obj_count=180,
            bio='Visit the world in one island. From Tokyo Tower to the Eiffel Tower.'
        )
    
    # ── Showcase Island 3: "Golden Empire" — Maximum bling ──
    gold_objects = (golden_objects + casino_objects[:10] + 
                   ['chest'] * 8 + ['throne'] * 3 + ['statue'] * 8 + 
                   ['fountain'] * 10 + ['lantern'] * 10 + ['campfire'] * 6)
    if gold_objects:
        create_spectacular_island(
            world_id='demo_golden_empire',
            name='Golden Empire',
            owner_name='Midas',
            theme_objects=gold_objects,
            terrain_base='sand_plain',
            island_type='mine',
            obj_count=220,
            bio='Everything that glitters IS gold. A monument to magnificence.'
        )
    
    # ── Showcase Island 4: "Enchanted Kingdom" — Fantasy forest ──
    fantasy_objects = (['tree_oak'] * 15 + ['tree_pine'] * 12 + ['tree_palm'] * 5 +
                      ['flower_patch'] * 10 + ['garden_large'] * 6 + ['bonsai'] * 5 +
                      ['bamboo_cluster'] * 5 + ['fountain'] * 6 + ['pond'] * 3 +
                      ['koi_pond'] * 3 + ['stone_lantern'] * 5 + ['torii_gate'] * 3 +
                      ['swing'] * 3 + ['bench'] * 4 + ['well'] * 2 + ['lighthouse'] * 2 +
                      ['house_cottage'] * 3 + ['campfire'] * 4 + ['bridge_wood'] * 4)
    create_spectacular_island(
        world_id='demo_enchanted_kingdom',
        name='Enchanted Kingdom',
        owner_name='Aurora',
        theme_objects=fantasy_objects,
        terrain_base='grass_dark',
        island_type='forest',
        obj_count=200,
        bio='A magical forest kingdom where nature and wonder intertwine.'
    )
    
    # ── Showcase Island 5: "Tropical Resort" — Beach paradise ──
    tropical_objects = (['tree_palm'] * 15 + ['flower_patch'] * 12 + ['garden_large'] * 5 +
                       ['bench'] * 5 + ['lantern'] * 8 + ['lighthouse'] * 2 +
                       ['dock_plank'] * 5 + ['fountain'] * 4 + ['pond'] * 3 +
                       ['swing'] * 3 + ['barrel'] * 4 + ['chest'] * 3 +
                       ['house_cottage'] * 2 + ['campfire'] * 3 + ['sign_wood'] * 3 +
                       ['rock_big'] * 4 + ['bridge_wood'] * 3)
    create_spectacular_island(
        world_id='demo_tropical_resort',
        name='Tropical Resort',
        owner_name='Captain Reef',
        theme_objects=tropical_objects,
        terrain_base='sand_plain',
        island_type='fish',
        obj_count=180,
        bio='Sun, sand, and sea. The ultimate island getaway.'
    )
    
    print("\n✅ All done! Restart backend to see changes.")

if __name__ == '__main__':
    main()
