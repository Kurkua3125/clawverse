# Sprint 14 — Backend Progress

## Status: ✅ ALL TASKS COMPLETE

### B1: Upgrade farm to 4x4 grid (16 plots) ✅
- Changed `FARM_ZONE` from dict-based 3x3 (cols 12-14, rows 19-21) to **set-based 4x4** (cols 12-15, rows 18-21)
- `FARM_ZONE` is now a `set()` of `(col, row)` tuples for O(1) lookup
- `FARM_ZONE_INFO` dict provides zone metadata for API responses (`min_col`, `max_col`, `min_row`, `max_row`, `total_plots: 16`)
- Verified planting works at all zone edges including new (15, 21)
- Planting outside zone correctly rejected

### B2: Farmville-style game mechanics ✅
All API routes implemented and tested:

| Route | Method | Status | Notes |
|-------|--------|--------|-------|
| `/api/farm` | GET | ✅ | Returns full farm state with crops, zone, stats |
| `/api/farm/plant` | POST | ✅ | Updated to use new zone + growth_time |
| `/api/farm/water/{crop_id}` | POST | ✅ | Doubles growth speed for 60s via `watered_boost_until` |
| `/api/farm/water_all` | POST | ✅ | Waters all non-ripe crops |
| `/api/farm/harvest/{crop_id}` | POST | ✅ | Returns XP + coins per crop type |
| `/api/farm/harvest_all` | POST | ✅ | Harvests all ripe, returns totals |
| `/api/farm/steal/{crop_id}` | POST | ✅ | 1/day/IP limit, visitor only |
| `/api/farm/growth` | GET | ✅ | Checks/updates all crop stages |

GET `/api/farm` response format matches spec exactly:
```json
{
  "crops": [{"id", "col", "row", "crop_type", "growth_stage", "planted_at", "growth_time", "last_watered", "watered_boost"}],
  "zone": {"min_col": 12, "max_col": 15, "min_row": 18, "max_row": 21, "total_plots": 16},
  "stats": {"planted", "growing", "ready", "empty", "total_harvested", "total_stolen"}
}
```

### B3: Crop growth timing ✅
- Growth stages: 0=seedling, 1=sprout, 2=growing, 3=ripe
- Stage transitions at: **20%, 50%, 100%** of growth time
- `_compute_growth_stage()` helper with watering boost support
- Watering doubles effective elapsed time for 60s window
- `GET /api/farm/growth` updates all stages in DB

### B4: Crop types with XP rewards ✅
```python
CROP_TYPES = {
    'carrot':  {'growth_time': 120, 'xp': 5,  'coins': 10, 'emoji': '🥕'},
    'potato':  {'growth_time': 180, 'xp': 8,  'coins': 15, 'emoji': '🥔'},
    'cabbage': {'growth_time': 240, 'xp': 10, 'coins': 20, 'emoji': '🥬'},
    'turnip':  {'growth_time': 300, 'xp': 12, 'coins': 25, 'emoji': '🟣'},
    'pumpkin': {'growth_time': 360, 'xp': 15, 'coins': 30, 'emoji': '🎃'},
}
```

### B5: Verification ✅
All curl tests pass:
- Plant → `{"ok": true, "crop_id": ..., "growth_time": ...}`
- GET /api/farm → Full state with zone + stats
- Water all → `{"ok": true, "watered_count": 4}`
- Harvest all → `{"ok": true, "total_xp": ..., "total_coins": ...}`
- Invalid crop type → 400
- Outside zone → 400
- Steal as owner → 403

### DB Changes (db.py)
- Added `last_watered` and `watered_boost_until` columns to crops table (with migration)
- New functions: `get_crops_with_watering()`, `water_crop_boost()`, `harvest_crop_v2()`, `update_crop_stage()`, `get_farm_stats()`

### Backend running at port 19003 ✅
