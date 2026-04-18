#!/usr/bin/env python3
"""WD-03: Improve default world with new objects."""
import json

world_path = "/opt/clawverse/backend/worlds/default.json"

with open(world_path) as f:
    world = json.load(f)

# Find highest existing obj ID number
existing_ids = [o["id"] for o in world["objects"]]
nums = []
for oid in existing_ids:
    try:
        nums.append(int(oid.split("_")[1]))
    except Exception:
        pass
next_num = max(nums) + 1 if nums else 20

def next_id():
    global next_num
    nid = f"obj_{next_num:03d}"
    next_num += 1
    return nid

# ── New objects to add ──────────────────────────────────────────────────────

# 1. Dock section near water (beach SE edge, around col 20-23, row 20-22)
#    Place 4 dock_plank tiles extending into the water direction
dock_planks = [
    {"type": "dock_plank", "col": 21, "row": 22, "z": 1},
    {"type": "dock_plank", "col": 22, "row": 21, "z": 1},
    {"type": "dock_plank", "col": 23, "row": 20, "z": 1},
    {"type": "dock_plank", "col": 24, "row": 19, "z": 1},
]

# 2. Fence around house — house is at col 14, row 14 (2x2 footprint covers 14-15, 14-15)
#    Place fences around it at a slight offset
fence_posts = [
    {"type": "fence_wood", "col": 13, "row": 13, "z": 1},  # NW
    {"type": "fence_wood", "col": 16, "row": 13, "z": 1},  # NE
    {"type": "fence_wood", "col": 13, "row": 16, "z": 1},  # SW
    {"type": "fence_wood", "col": 16, "row": 16, "z": 1},  # SE
]

# 3. Barrel near the house (right side of house)
barrel = [
    {"type": "barrel", "col": 17, "row": 14, "z": 1},
]

# 4. Table near the campfire (campfire is at col 18, row 17)
table = [
    {"type": "table_wood", "col": 19, "row": 16, "z": 1},
]

# 5. Well on the island (open grassy area, col 11, row 15)
well = [
    {"type": "well", "col": 11, "row": 15, "z": 1},
]

all_new = dock_planks + fence_posts + barrel + table + well

# Check for collisions with existing objects
existing_positions = {(o["col"], o["row"]) for o in world["objects"]}

added = 0
skipped = 0
for obj in all_new:
    pos = (obj["col"], obj["row"])
    if pos in existing_positions:
        print(f"  ⚠️  skip {obj['type']} at {pos} — occupied")
        skipped += 1
        continue
    new_entry = {"id": next_id(), **obj}
    world["objects"].append(new_entry)
    existing_positions.add(pos)
    print(f"  + {new_entry['id']} {obj['type']} @ ({obj['col']},{obj['row']})")
    added += 1

with open(world_path, "w") as f:
    json.dump(world, f, indent=2)

print(f"\n✅ default.json updated — added {added} objects, skipped {skipped}")
