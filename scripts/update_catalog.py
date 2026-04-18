#!/usr/bin/env python3
"""WD-02: Register new tiles in catalog/catalog.json"""
import json

catalog_path = "/opt/clawverse/catalog/catalog.json"

with open(catalog_path) as f:
    catalog = json.load(f)

# New terrain entries
new_terrain = [
    {
        "id": "pond",
        "name": "Pond",
        "category": "water",
        "file": "terrain/pond.png"
    },
    {
        "id": "cliff_edge_n",
        "name": "Cliff Edge North",
        "category": "cliff",
        "file": "terrain/cliff_edge_n.png"
    }
]

# New object entries
new_objects = [
    {
        "id": "dock_plank",
        "name": "Dock Plank",
        "category": "structure",
        "file": "objects/dock_plank.png",
        "footprint": [1, 1],
        "walkable": True
    },
    {
        "id": "fence_wood",
        "name": "Wooden Fence",
        "category": "structure",
        "file": "objects/fence_wood.png",
        "footprint": [1, 1],
        "walkable": False
    },
    {
        "id": "barrel",
        "name": "Barrel",
        "category": "furniture",
        "file": "objects/barrel.png",
        "footprint": [1, 1],
        "walkable": False
    },
    {
        "id": "chest",
        "name": "Treasure Chest",
        "category": "furniture",
        "file": "objects/chest.png",
        "footprint": [1, 1],
        "walkable": False
    },
    {
        "id": "table_wood",
        "name": "Wooden Table",
        "category": "furniture",
        "file": "objects/table_wood.png",
        "footprint": [1, 1],
        "walkable": False
    },
    {
        "id": "well",
        "name": "Stone Well",
        "category": "structure",
        "file": "objects/well.png",
        "footprint": [1, 1],
        "walkable": False
    }
]

# Append only if not already present
existing_terrain_ids = {t["id"] for t in catalog["terrain"]}
existing_object_ids  = {o["id"] for o in catalog["objects"]}

added_terrain = 0
for entry in new_terrain:
    if entry["id"] not in existing_terrain_ids:
        catalog["terrain"].append(entry)
        added_terrain += 1
        print(f"  + terrain: {entry['id']}")

added_objects = 0
for entry in new_objects:
    if entry["id"] not in existing_object_ids:
        catalog["objects"].append(entry)
        added_objects += 1
        print(f"  + object:  {entry['id']}")

with open(catalog_path, "w") as f:
    json.dump(catalog, f, indent=2)

print(f"\n✅ catalog.json updated — +{added_terrain} terrain, +{added_objects} objects")
