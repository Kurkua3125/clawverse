"""Create 3 differentiated demo worlds for Clawverse."""
import json, math, random, os, time
from datetime import datetime, timezone
import auth, db

WORLDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'worlds')
SIZE = 32
CX, CY = 15, 15

def make_island_shape(seed_offset=0):
    """Classic island with water border."""
    def dist(col, row):
        base = math.sqrt((col - CX)**2 + (row - CY)**2)
        angle = math.atan2(row - CY, col - CX)
        wobble = 1.8 * math.sin(3 * angle + 0.3 + seed_offset)
        wobble += 0.9 * math.sin(5 * angle + 1.2 + seed_offset * 0.5)
        wobble += 0.5 * math.sin(7 * angle + 2.1)
        return base - wobble * 0.55
    return dist

# ─── World 1: Sakura — Cherry Blossom Zen Garden ─────────────
def create_sakura():
    random.seed(777)
    dist = make_island_shape(0.7)
    terrain = []
    for row in range(SIZE):
        for col in range(SIZE):
            d = dist(col, row)
            r = random.random()
            if d > 13: t = 'water_deep'
            elif d > 11.5: t = 'water_shallow'
            elif d > 10.5: t = 'sand_plain'
            elif d > 9:
                t = 'grass_cherry' if r > 0.3 else 'grass_plain'
            else:
                if r < 0.12: t = 'zen_sand'
                elif r < 0.2: t = 'moss_stone'
                elif r < 0.35: t = 'grass_cherry'
                elif r < 0.42: t = 'dirt_path'
                else: t = 'grass_plain'
            terrain.append([col, row, 0, t])

    # Zen paths
    for i in range(12, 20):
        terrain = [[c,r,z,t] if not (c==i and r==15 and z==0) else [c,r,z,'dirt_path'] for c,r,z,t in terrain]
    for i in range(12, 19):
        terrain = [[c,r,z,t] if not (c==15 and r==i and z==0) else [c,r,z,'dirt_path'] for c,r,z,t in terrain]

    objects = [
        {'id': 'zen_torii', 'type': 'torii_gate', 'col': 15, 'row': 19, 'z': 1},
        {'id': 'zen_house', 'type': 'house_cottage', 'col': 13, 'row': 12, 'z': 1},
        {'id': 'zen_koi', 'type': 'koi_pond', 'col': 17, 'row': 13, 'z': 1},
        {'id': 'zen_bonsai1', 'type': 'bonsai', 'col': 12, 'row': 14, 'z': 1},
        {'id': 'zen_bonsai2', 'type': 'bonsai', 'col': 18, 'row': 14, 'z': 1},
        {'id': 'zen_slantern1', 'type': 'stone_lantern', 'col': 14, 'row': 17, 'z': 1},
        {'id': 'zen_slantern2', 'type': 'stone_lantern', 'col': 16, 'row': 17, 'z': 1},
        {'id': 'zen_bamboo1', 'type': 'bamboo_cluster', 'col': 10, 'row': 11, 'z': 1},
        {'id': 'zen_bamboo2', 'type': 'bamboo_cluster', 'col': 11, 'row': 10, 'z': 1},
        {'id': 'zen_bamboo3', 'type': 'bamboo_cluster', 'col': 19, 'row': 11, 'z': 1},
        {'id': 'zen_bench', 'type': 'bench', 'col': 19, 'row': 15, 'z': 1},
        {'id': 'zen_bridge', 'type': 'stone_bridge', 'col': 15, 'row': 13, 'z': 1},
        {'id': 'zen_flower1', 'type': 'flower_patch', 'col': 11, 'row': 16, 'z': 1},
        {'id': 'zen_flower2', 'type': 'flower_patch', 'col': 20, 'row': 13, 'z': 1},
        {'id': 'zen_fountain', 'type': 'fountain', 'col': 15, 'row': 15, 'z': 1},
        {'id': 'zen_tree1', 'type': 'tree_pine', 'col': 10, 'row': 14, 'z': 1},
        {'id': 'zen_tree2', 'type': 'tree_pine', 'col': 20, 'row': 10, 'z': 1},
    ]

    return {
        'meta': {'name': 'Cherry Blossom Garden', 'size': [SIZE, SIZE]},
        'terrain': terrain, 'objects': objects,
        'agent': {'col': 14, 'row': 16, 'direction': 'front', 'action': 'idle'},
    }

# ─── World 2: Captain — Castle Fortress ──────────────────────
def create_captain():
    random.seed(42)
    terrain = []
    # Full landmass with moat — no island, a fortified castle
    for row in range(SIZE):
        for col in range(SIZE):
            r = random.random()
            # Outer water border (thin)
            edge_dist = min(col, row, SIZE-1-col, SIZE-1-row)
            # Moat around castle center
            castle_dist = max(abs(col - CX), abs(row - CY))

            if edge_dist <= 1:
                t = 'water_deep'
            elif edge_dist <= 2:
                t = 'sand_plain'
            elif castle_dist >= 12:
                # Outer forest
                if r < 0.05: t = 'stone_plain'
                elif r < 0.15: t = 'dirt_path'
                elif r < 0.25: t = 'grass_dark'
                else: t = 'grass_plain'
            elif castle_dist >= 9:
                # Moat
                t = 'water_shallow' if castle_dist == 9 else ('water_deep' if castle_dist == 10 else 'grass_plain')
                if castle_dist == 11: t = 'grass_plain'
                if castle_dist == 10: t = 'water_deep'
                if castle_dist == 9: t = 'water_shallow'
            elif castle_dist >= 7:
                # Castle walls area
                if r < 0.3: t = 'castle_wall'
                elif r < 0.5: t = 'castle_floor'
                else: t = 'stone_plain'
            elif castle_dist >= 4:
                # Inner courtyard
                if r < 0.15: t = 'castle_carpet'
                elif r < 0.35: t = 'castle_floor'
                elif r < 0.45: t = 'dirt_path'
                else: t = 'stone_plain'
            else:
                # Throne room center
                if r < 0.4: t = 'castle_carpet'
                elif r < 0.6: t = 'castle_floor'
                else: t = 'stone_plain'

            terrain.append([col, row, 0, t])

    # Castle bridge across moat (north)
    for i in range(9, 13):
        terrain = [[c,r,z,t] if not (c==CX and r==CY-i+CY and z==0 and 9<=max(abs(c-CX),abs(r-CY))<=11)
                   else [c,r,z,'stone_plain'] for c,r,z,t in terrain]

    objects = [
        {'id': 'c_throne', 'type': 'throne', 'col': CX, 'row': CY, 'z': 1},
        {'id': 'c_gate', 'type': 'castle_gate', 'col': CX, 'row': CY+7, 'z': 1},
        {'id': 'c_torch1', 'type': 'torch_wall', 'col': CX-3, 'row': CY-3, 'z': 1},
        {'id': 'c_torch2', 'type': 'torch_wall', 'col': CX+3, 'row': CY-3, 'z': 1},
        {'id': 'c_torch3', 'type': 'torch_wall', 'col': CX-3, 'row': CY+3, 'z': 1},
        {'id': 'c_torch4', 'type': 'torch_wall', 'col': CX+3, 'row': CY+3, 'z': 1},
        {'id': 'c_armor1', 'type': 'armor_stand', 'col': CX-2, 'row': CY-1, 'z': 1},
        {'id': 'c_armor2', 'type': 'armor_stand', 'col': CX+2, 'row': CY-1, 'z': 1},
        {'id': 'c_banner1', 'type': 'banner_red', 'col': CX-1, 'row': CY-4, 'z': 1},
        {'id': 'c_banner2', 'type': 'banner_red', 'col': CX+1, 'row': CY-4, 'z': 1},
        {'id': 'c_lighthouse', 'type': 'lighthouse', 'col': CX+6, 'row': CY-5, 'z': 1},
        {'id': 'c_campfire', 'type': 'campfire', 'col': CX-4, 'row': CY+5, 'z': 1},
        {'id': 'c_well', 'type': 'well', 'col': CX+4, 'row': CY+4, 'z': 1},
        # Outer forest trees
        {'id': 'c_tree1', 'type': 'tree_oak', 'col': 4, 'row': 4, 'z': 1},
        {'id': 'c_tree2', 'type': 'tree_pine', 'col': 27, 'row': 5, 'z': 1},
        {'id': 'c_tree3', 'type': 'tree_oak', 'col': 5, 'row': 26, 'z': 1},
        {'id': 'c_tree4', 'type': 'tree_pine', 'col': 26, 'row': 27, 'z': 1},
        {'id': 'c_tree5', 'type': 'tree_oak', 'col': 3, 'row': 15, 'z': 1},
        {'id': 'c_tree6', 'type': 'tree_pine', 'col': 28, 'row': 16, 'z': 1},
        {'id': 'c_rock1', 'type': 'rock_big', 'col': 6, 'row': 8, 'z': 1},
        {'id': 'c_rock2', 'type': 'rock_big', 'col': 25, 'row': 22, 'z': 1},
    ]

    return {
        'meta': {'name': 'Castle Fortress', 'size': [SIZE, SIZE]},
        'terrain': terrain, 'objects': objects,
        'agent': {'col': CX+1, 'row': CY+2, 'direction': 'front', 'action': 'idle'},
    }

# ─── World 3: Luna — Space Station ──────────────────────────
def create_luna():
    random.seed(2026)
    terrain = []
    # Hexagonal space station shape on void background
    for row in range(SIZE):
        for col in range(SIZE):
            r = random.random()
            # Distance from center
            d = math.sqrt((col - CX)**2 + (row - CY)**2)
            # Hexagonal shape
            angle = math.atan2(row - CY, col - CX)
            hex_r = 11 + 1.5 * math.cos(6 * angle)

            if d > hex_r + 1:
                # Space void
                t = 'water_deep'  # dark space
            elif d > hex_r:
                t = 'space_glass'  # edge windows
            elif d > hex_r - 2:
                # Outer ring - corridors
                if r < 0.3: t = 'metal_floor'
                elif r < 0.5: t = 'space_glass'
                else: t = 'metal_floor'
            elif d > 5:
                # Inner ring - living quarters
                if r < 0.2: t = 'metal_floor'
                elif r < 0.35: t = 'tile_floor'
                elif r < 0.45: t = 'carpet_blue'
                else: t = 'metal_floor'
            else:
                # Core - command center
                if r < 0.35: t = 'carpet_blue'
                elif r < 0.6: t = 'metal_floor'
                else: t = 'tile_floor'

            terrain.append([col, row, 0, t])

    objects = [
        {'id': 's_control', 'type': 'control_panel', 'col': CX, 'row': CY, 'z': 1},
        {'id': 's_antenna1', 'type': 'antenna', 'col': CX, 'row': CY-4, 'z': 1},
        {'id': 's_antenna2', 'type': 'antenna', 'col': CX+5, 'row': CY, 'z': 1},
        {'id': 's_robot1', 'type': 'robot', 'col': CX-2, 'row': CY+1, 'z': 1},
        {'id': 's_robot2', 'type': 'robot', 'col': CX+3, 'row': CY-2, 'z': 1},
        {'id': 's_plant1', 'type': 'space_plant', 'col': CX-4, 'row': CY-3, 'z': 1},
        {'id': 's_plant2', 'type': 'space_plant', 'col': CX+4, 'row': CY+3, 'z': 1},
        {'id': 's_plant3', 'type': 'space_plant', 'col': CX-3, 'row': CY+4, 'z': 1},
        {'id': 's_lamp1', 'type': 'lamp_floor', 'col': CX-2, 'row': CY-3, 'z': 1},
        {'id': 's_lamp2', 'type': 'lamp_floor', 'col': CX+2, 'row': CY+3, 'z': 1},
        {'id': 's_sofa', 'type': 'sofa', 'col': CX+3, 'row': CY+1, 'z': 1},
        {'id': 's_tv', 'type': 'tv', 'col': CX+4, 'row': CY-1, 'z': 1},
        {'id': 's_bookcase', 'type': 'bookcase', 'col': CX-5, 'row': CY, 'z': 1},
        {'id': 's_table', 'type': 'dining_table', 'col': CX-1, 'row': CY+3, 'z': 1},
        {'id': 's_lantern1', 'type': 'lantern', 'col': CX-5, 'row': CY-5, 'z': 1},
        {'id': 's_lantern2', 'type': 'lantern', 'col': CX+5, 'row': CY+5, 'z': 1},
        {'id': 's_lantern3', 'type': 'lantern', 'col': CX+5, 'row': CY-5, 'z': 1},
        {'id': 's_lantern4', 'type': 'lantern', 'col': CX-5, 'row': CY+5, 'z': 1},
    ]

    return {
        'meta': {'name': 'Space Station Claw', 'size': [SIZE, SIZE]},
        'terrain': terrain, 'objects': objects,
        'agent': {'col': CX-1, 'row': CY-1, 'direction': 'right', 'action': 'idle'},
    }

# ─── Main ────────────────────────────────────────────────────
demos = [
    {
        'email': 'sakura@clawverse.demo',
        'name': 'Sakura',
        'avatar': '🌸',
        'island_name': 'Cherry Blossom Garden',
        'create_fn': create_sakura,
    },
    {
        'email': 'captain@clawverse.demo',
        'name': 'Captain Claw',
        'avatar': '🏰',
        'island_name': 'Castle Fortress',
        'create_fn': create_captain,
    },
    {
        'email': 'luna@clawverse.demo',
        'name': 'Luna',
        'avatar': '🚀',
        'island_name': 'Space Station Claw',
        'create_fn': create_luna,
    },
]

for d in demos:
    user = auth.get_or_create_user(d['email'], d['name'])
    user_id = user['id']
    auth.update_user(user_id, name=d['name'], avatar=d['avatar'], island_name=d['island_name'])

    world_data = d['create_fn']()
    world_id = user_id

    # Save
    world_file = os.path.join(WORLDS_DIR, f'{world_id}.json')
    with open(world_file, 'w') as f:
        json.dump(world_data, f, ensure_ascii=False)
    db.save_world(world_id, world_data, owner_id=user_id)
    db.ensure_progress(world_id)

    # Add fake visits
    for j in range(random.randint(20, 100)):
        ts = time.time() - random.randint(0, 86400 * 7)
        emojis = ['🦞','🐱','🌟','🎉','👋','🐢','🦊','🌺','🎸','⚡']
        names = ['Visitor','Claw Fan','Explorer','Wanderer','Stargazer','Builder','Nomad']
        db.add_visit(world_id, random.choice(emojis), '', random.choice(names), ts)

    print(f'✅ {d["name"]} ({d["avatar"]}) — {d["island_name"]} (world={world_id})')

print('\nDone! All 3 demo worlds created.')
