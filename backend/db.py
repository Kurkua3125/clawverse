"""Clawverse v1 — SQLite persistence layer."""
import sqlite3, json, os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clawverse.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS worlds (
        id TEXT PRIMARY KEY,
        name TEXT,
        owner TEXT DEFAULT 'anonymous',
        data_json TEXT,
        created_at TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT DEFAULT 'default',
        emoji TEXT,
        from_url TEXT DEFAULT '',
        from_name TEXT DEFAULT 'Anonymous',
        message TEXT DEFAULT '',
        ts REAL
    );
    CREATE TABLE IF NOT EXISTS islands (
        id TEXT PRIMARY KEY,
        name TEXT,
        owner TEXT,
        url TEXT UNIQUE,
        avatar TEXT DEFAULT '🦞',
        obj_count INTEGER DEFAULT 0,
        last_seen TEXT
    );
    CREATE TABLE IF NOT EXISTS user_progress (
        world_id TEXT PRIMARY KEY,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        tiles_placed INTEGER DEFAULT 0,
        objects_placed INTEGER DEFAULT 0,
        visits_received INTEGER DEFAULT 0,
        achievements_json TEXT DEFAULT '[]',
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS world_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT DEFAULT 'default',
        label TEXT,
        data_json TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS island_story (
        world_id TEXT PRIMARY KEY,
        bio TEXT DEFAULT '',
        daily_message TEXT DEFAULT '',
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT DEFAULT 'default',
        visitor_id TEXT DEFAULT '',
        visitor_name TEXT DEFAULT 'Anonymous',
        object_type TEXT DEFAULT '',
        col INTEGER DEFAULT 0,
        row INTEGER DEFAULT 0,
        message TEXT DEFAULT '',
        placed_in_world INTEGER DEFAULT 0,
        ts REAL
    );
    CREATE TABLE IF NOT EXISTS evolutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT DEFAULT 'default',
        evolution_id TEXT,
        title TEXT,
        description TEXT,
        applied INTEGER DEFAULT 0,
        created_at TEXT,
        applied_at TEXT
    );
    CREATE TABLE IF NOT EXISTS page_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT,
        ts REAL,
        ip TEXT
    );
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY,
        api_key TEXT DEFAULT '',
        api_provider TEXT DEFAULT 'genspark',
        daily_ai_calls INTEGER DEFAULT 0,
        last_reset_date TEXT DEFAULT '',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS island_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        island_id TEXT NOT NULL,
        created_at TEXT,
        UNIQUE(user_id, island_id)
    );
    """)
    # Indexes for lobby query performance (GROUP BY world_id)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_page_views_world ON page_views(world_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_world ON visits(world_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fav_user ON island_favorites(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fav_island ON island_favorites(island_id)")
    # Island Passport — visitor stamp collection
    conn.execute("""CREATE TABLE IF NOT EXISTS island_passport (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        island_id TEXT NOT NULL,
        island_name TEXT DEFAULT '',
        island_avatar TEXT DEFAULT '🦞',
        island_level INTEGER DEFAULT 1,
        stamped_at TEXT,
        UNIQUE(user_id, island_id)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_passport_user ON island_passport(user_id)")
    conn.commit()
    conn.close()

def migrate_visits_from_json(visits_json_path):
    """One-time migration: import visits.json → SQLite visits table."""
    try:
        with open(visits_json_path) as f:
            data = json.load(f)
        visits = data.get('visits', [])
        if not visits:
            return 0
        conn = get_conn()
        count = 0
        for v in visits:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO visits (world_id, emoji, from_url, from_name, ts) VALUES (?,?,?,?,?)",
                    ('default', v.get('emoji','❓'), v.get('from_url',''), v.get('from_name','Anonymous'), v.get('ts',0))
                )
                count += 1
            except Exception:
                pass
        conn.commit()
        conn.close()
        return count
    except Exception as e:
        return 0

def get_visits(world_id='default', limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM visits WHERE world_id=? ORDER BY ts DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_visit(world_id='default', emoji='❓', from_url='', from_name='Anonymous', ts=None, message=''):
    if ts is None:
        ts = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    # Add message column if not exists (migration)
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN message TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.execute(
        "INSERT INTO visits (world_id, emoji, from_url, from_name, message, ts) VALUES (?,?,?,?,?,?)",
        (world_id, emoji, from_url, from_name, message or '', ts)
    )
    conn.commit()
    conn.close()
    _invalidate_worlds_cache()

# ── Page Views (passive visit tracking) ───────────────────────

def record_page_view(world_id, ip):
    """Record a page view. Dedup: max 1 per IP per world per hour."""
    import time
    conn = get_conn()
    now = time.time()
    one_hour_ago = now - 3600
    existing = conn.execute(
        "SELECT id FROM page_views WHERE world_id=? AND ip=? AND ts>?",
        (world_id, ip, one_hour_ago)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO page_views (world_id, ts, ip) VALUES (?,?,?)",
            (world_id, now, ip)
        )
        conn.commit()
        _invalidate_worlds_cache()
    conn.close()

def get_page_view_count(world_id):
    """Return total page view count for a world."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM page_views WHERE world_id=?",
        (world_id,)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0

def get_progress(world_id='default'):
    conn = get_conn()
    row = conn.execute('SELECT * FROM user_progress WHERE world_id=?', (world_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def ensure_progress(world_id='default'):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO user_progress
          (world_id, level, xp, tiles_placed, objects_placed, visits_received, achievements_json, updated_at)
        VALUES (?,1,0,0,0,0,'[]',?)
    """, (world_id, now))
    conn.commit()
    conn.close()

def record_progress_event(world_id, event_type):
    """Record event, gain XP, level up if needed. Returns dict with result."""
    xp_map = {'place_tile': 5, 'place_object': 10, 'receive_visit': 15}
    xp_gain = xp_map.get(event_type, 0)
    if xp_gain == 0:
        return {'ok': False, 'error': 'unknown event'}

    now = datetime.now(timezone.utc).isoformat()
    ensure_progress(world_id)

    col_map = {
        'place_tile':     'tiles_placed',
        'place_object':   'objects_placed',
        'receive_visit':  'visits_received',
    }
    col = col_map[event_type]

    conn = get_conn()
    conn.execute(
        f"UPDATE user_progress SET {col}={col}+1, xp=xp+?, updated_at=? WHERE world_id=?",
        (xp_gain, now, world_id)
    )
    row = conn.execute("SELECT level, xp FROM user_progress WHERE world_id=?", (world_id,)).fetchone()
    level, xp = row['level'], row['xp']
    leveled_up = False
    while xp >= level * 100:
        xp -= level * 100
        level += 1
        leveled_up = True
    if leveled_up:
        conn.execute(
            "UPDATE user_progress SET level=?, xp=?, updated_at=? WHERE world_id=?",
            (level, xp, now, world_id)
        )
    conn.commit()
    conn.close()
    # Daily quest: earn_xp
    try:
        advance_quest(world_id, 'earn_xp', xp_gain)
    except Exception:
        pass
    return {'ok': True, 'xp_gained': xp_gain, 'leveled_up': leveled_up,
            'new_level': level if leveled_up else None}

def get_achievements(world_id='default'):
    conn = get_conn()
    row = conn.execute('SELECT achievements_json FROM user_progress WHERE world_id=?', (world_id,)).fetchone()
    conn.close()
    if not row:
        return []
    return json.loads(row['achievements_json'] or '[]')

def set_achievements(world_id, achievements):
    now = datetime.now(timezone.utc).isoformat()
    ensure_progress(world_id)
    conn = get_conn()
    conn.execute(
        "UPDATE user_progress SET achievements_json=?, updated_at=? WHERE world_id=?",
        (json.dumps(achievements), now, world_id)
    )
    conn.commit()
    conn.close()

def save_snapshot(world_id, label, data_json):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO world_snapshots (world_id, label, data_json, created_at) VALUES (?,?,?,?)",
        (world_id, label, data_json, now)
    )
    conn.commit()
    # Keep only last 20 snapshots per world
    conn.execute("""
        DELETE FROM world_snapshots WHERE world_id=? AND id NOT IN (
            SELECT id FROM world_snapshots WHERE world_id=? ORDER BY id DESC LIMIT 20
        )
    """, (world_id, world_id))
    conn.commit()
    conn.close()

def get_snapshots(world_id='default', limit=20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, world_id, label, created_at FROM world_snapshots WHERE world_id=? ORDER BY id DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_snapshot(snapshot_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM world_snapshots WHERE id=?", (snapshot_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_story(world_id='default'):
    conn = get_conn()
    row = conn.execute("SELECT * FROM island_story WHERE world_id=?", (world_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def set_story(world_id='default', bio='', daily_message=''):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO island_story (world_id, bio, daily_message, updated_at)
        VALUES (?,?,?,?)
    """, (world_id, bio, daily_message, now))
    conn.commit()
    conn.close()

def get_gifts(world_id='default', limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM gifts WHERE world_id=? ORDER BY ts DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_visitor_gift_count(world_id, visitor_id):
    """Count gifts left by this visitor on this world today."""
    today_start = datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM gifts WHERE world_id=? AND visitor_id=? AND ts>=?",
        (world_id, visitor_id, today_start)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0

def add_gift(world_id='default', visitor_id='', visitor_name='Anonymous',
             object_type='', col=0, row=0, message='', ts=None):
    if ts is None:
        ts = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    cursor = conn.execute(
        """INSERT INTO gifts (world_id, visitor_id, visitor_name, object_type, col, row, message, placed_in_world, ts)
           VALUES (?,?,?,?,?,?,?,0,?)""",
        (world_id, visitor_id, visitor_name, object_type, col, row, message, ts)
    )
    gift_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return gift_id

def mark_gift_placed(gift_id):
    conn = get_conn()
    conn.execute("UPDATE gifts SET placed_in_world=1 WHERE id=?", (gift_id,))
    conn.commit()
    conn.close()

def get_pending_evolutions(world_id='default'):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM evolutions WHERE world_id=? AND applied=0 ORDER BY created_at ASC",
        (world_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_applied_evolutions(world_id='default', limit=20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM evolutions WHERE world_id=? AND applied=1 ORDER BY applied_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_evolution(world_id='default', evolution_id='', title='', description=''):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    # Check if this evolution already exists (pending or applied)
    exists = conn.execute(
        "SELECT id FROM evolutions WHERE world_id=? AND evolution_id=?",
        (world_id, evolution_id)
    ).fetchone()
    if exists:
        conn.close()
        return None
    cursor = conn.execute(
        "INSERT INTO evolutions (world_id, evolution_id, title, description, applied, created_at) VALUES (?,?,?,?,0,?)",
        (world_id, evolution_id, title, description, now)
    )
    evo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return evo_id

def apply_evolution(evolution_id_int):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE evolutions SET applied=1, applied_at=? WHERE id=?",
        (now, evolution_id_int)
    )
    conn.commit()
    conn.close()

# ── Coin Currency ──────────────────────────────────────────────

def init_coins():
    """Add shells column to user_progress if not exists (DB col stays 'shells')."""
    conn = get_conn()
    try:
        conn.execute("ALTER TABLE user_progress ADD COLUMN shells INTEGER DEFAULT 200")
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE user_progress ADD COLUMN total_earned INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.close()

def get_wallet(world_id='default'):
    """Return current coin balance."""
    ensure_progress(world_id)
    conn = get_conn()
    row = conn.execute('SELECT shells, total_earned FROM user_progress WHERE world_id=?', (world_id,)).fetchone()
    conn.close()
    if not row:
        return {'coins': 200, 'total_earned': 0}
    return {'coins': row['shells'] if row['shells'] is not None else 200,
            'total_earned': row['total_earned'] if row['total_earned'] is not None else 0}

def spend_coins(world_id, amount, reason=''):
    """Deduct coins. Returns {'ok':True, 'remaining':X} or {'ok':False, 'error':...}."""
    ensure_progress(world_id)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    row = conn.execute('SELECT shells FROM user_progress WHERE world_id=?', (world_id,)).fetchone()
    current = row['shells'] if row and row['shells'] is not None else 200
    if current < amount:
        conn.close()
        return {'ok': False, 'error': 'Not enough coins', 'coins': current, 'need': amount}
    new_balance = current - amount
    conn.execute('UPDATE user_progress SET shells=?, updated_at=? WHERE world_id=?',
                 (new_balance, now, world_id))
    conn.commit()
    conn.close()
    return {'ok': True, 'remaining': new_balance}

def earn_coins(world_id, amount, reason=''):
    """Add coins. Returns new balance."""
    ensure_progress(world_id)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    row = conn.execute('SELECT shells, total_earned FROM user_progress WHERE world_id=?', (world_id,)).fetchone()
    current = row['shells'] if row and row['shells'] is not None else 200
    total = row['total_earned'] if row and row['total_earned'] is not None else 0
    new_balance = current + amount
    new_total = total + amount
    conn.execute('UPDATE user_progress SET shells=?, total_earned=?, updated_at=? WHERE world_id=?',
                 (new_balance, new_total, now, world_id))
    conn.commit()
    conn.close()
    return {'coins': new_balance, 'total_earned': new_total}

def save_world(world_id, world_data, owner_id=None):
    """Persist world data to SQLite."""
    conn = get_conn()
    data_json = json.dumps(world_data, ensure_ascii=False)
    name = world_data.get('meta', {}).get('name', 'Claw Island')
    now = datetime.now(timezone.utc).isoformat()
    if owner_id:
        conn.execute("""
            INSERT INTO worlds (id, name, owner, data_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET data_json=?, name=?, owner=?, updated_at=?
        """, (world_id, name, owner_id, data_json, now, now, data_json, name, owner_id, now))
    else:
        conn.execute("""
            INSERT INTO worlds (id, name, data_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET data_json=?, name=?, updated_at=?
        """, (world_id, name, data_json, now, now, data_json, name, now))
    conn.commit()
    conn.close()

def load_world(world_id):
    """Load world data from SQLite. Returns dict or None."""
    conn = get_conn()
    row = conn.execute("SELECT data_json FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    if row and row['data_json']:
        return json.loads(row['data_json'])
    return None

def resolve_world_id(world_id_or_name):
    """Resolve a world ID or name/slug to the actual world ID.
    First tries exact ID match, then case-insensitive name match.
    Returns the resolved world_id or None."""
    conn = get_conn()
    # Try exact ID match
    row = conn.execute("SELECT id FROM worlds WHERE id=?", (world_id_or_name,)).fetchone()
    if row:
        conn.close()
        return row['id']
    # Try case-insensitive name match
    row = conn.execute("SELECT id FROM worlds WHERE LOWER(name)=LOWER(?)", (world_id_or_name,)).fetchone()
    if row:
        conn.close()
        return row['id']
    # Try slug match: convert hyphens to spaces (e.g., "claw-island" → "claw island")
    slug_as_name = world_id_or_name.replace('-', ' ')
    row = conn.execute("SELECT id FROM worlds WHERE LOWER(name)=LOWER(?)", (slug_as_name,)).fetchone()
    if row:
        conn.close()
        return row['id']
    # Try reverse slug match: convert DB names to slug form (spaces→hyphens) and compare
    row = conn.execute("SELECT id FROM worlds WHERE LOWER(REPLACE(name, ' ', '-'))=LOWER(?)", (world_id_or_name,)).fetchone()
    conn.close()
    if row:
        return row['id']
    return None

def get_world_owner(world_id):
    """Get the owner of a world. Returns owner id string or None."""
    conn = get_conn()
    row = conn.execute("SELECT owner FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    return row['owner'] if row else None

import time as _time

# ── In-memory cache for list_worlds (lobby) ──────────────────
_worlds_cache = {}  # key: sort -> {'data': [...], 'ts': float}
_WORLDS_CACHE_TTL = 30  # seconds

def _invalidate_worlds_cache():
    """Clear the in-memory lobby cache (call after writes that affect counts)."""
    _worlds_cache.clear()

def list_worlds(limit=50, sort='popular', search='', island_type=''):
    """List all worlds with metadata (for island directory).
    Uses pre-aggregated JOINs instead of per-row subqueries,
    plus a 30-second in-memory cache to avoid repeated DB hits.
    Optional search (name LIKE) and island_type filter."""
    cache_key = f'{sort}:{limit}:{search}:{island_type}'
    cached = _worlds_cache.get(cache_key)
    if cached and (_time.time() - cached['ts']) < _WORLDS_CACHE_TTL:
        return cached['data']

    conn = get_conn()
    ALLOWED_SORT_ORDERS = {
        'recent': 'w.updated_at DESC',
        'popular': 'visit_count DESC, w.updated_at DESC',
        'rated': 'rating_avg DESC, rating_count DESC, visit_count DESC',
        'level': 'COALESCE(p.level, 1) DESC, visit_count DESC',
        'trending': 'recent_visits DESC, visit_count DESC, w.updated_at DESC',
    }
    order = ALLOWED_SORT_ORDERS.get(sort, ALLOWED_SORT_ORDERS['popular'])

    where_clauses = []
    params = []
    if search:
        where_clauses.append("(LOWER(w.name) LIKE ? OR LOWER(COALESCE(w.island_tags,'')) LIKE ?)")
        params.append(f'%{search.lower()}%')
        params.append(f'%{search.lower()}%')
    if island_type:
        where_clauses.append("w.island_type = ?")
        params.append(island_type)
    where_clauses.append("COALESCE(w.unlisted, 0) = 0")
    where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    ts_24h_ago = _time.time() - 86400
    params_list = [ts_24h_ago] + params + [limit]
    rows = conn.execute(f"""
        SELECT w.id, w.name, w.owner, w.updated_at, w.created_at, w.island_type,
               COALESCE(pv.cnt, 0) + COALESCE(v.cnt, 0) as visit_count,
               COALESCE(p.level, 1) as level,
               COALESCE(p.objects_placed, 0) as objects_placed,
               COALESCE(s.bio, '') as bio,
               w.island_mood, w.island_mood_emoji, w.welcome_message, w.island_tags, w.accent_color, w.announcement, w.unlisted,
               COALESCE(rv.avg_rating, 0) as rating_avg,
               COALESCE(rv.cnt, 0) as rating_count,
               COALESCE(rpv.cnt, 0) as recent_visits
        FROM worlds w
        LEFT JOIN (SELECT world_id, COUNT(*) as cnt FROM page_views WHERE ts > ? GROUP BY world_id) rpv ON rpv.world_id = w.id
        LEFT JOIN (SELECT world_id, COUNT(*) as cnt FROM page_views GROUP BY world_id) pv ON pv.world_id = w.id
        LEFT JOIN (SELECT world_id, COUNT(*) as cnt FROM visits GROUP BY world_id) v ON v.world_id = w.id
        LEFT JOIN user_progress p ON p.world_id = w.id
        LEFT JOIN island_story s ON s.world_id = w.id
        LEFT JOIN (SELECT world_id, AVG(rating) as avg_rating, COUNT(*) as cnt FROM island_reviews GROUP BY world_id) rv ON rv.world_id = w.id
        {where_sql}
        ORDER BY {order} LIMIT ?
    """, params_list).fetchall()
    conn.close()
    result = [dict(r) for r in rows]
    _worlds_cache[cache_key] = {'data': result, 'ts': _time.time()}
    return result

def get_popular_tags(limit=20):
    """Return the most popular island tags across all listed worlds.
    Returns a list of dicts: [{"tag": str, "count": int}, ...]"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT island_tags FROM worlds WHERE island_tags IS NOT NULL AND island_tags != '' AND COALESCE(unlisted, 0) = 0"
    ).fetchall()
    conn.close()
    from collections import Counter
    tag_counts = Counter()
    for row in rows:
        for tag in row['island_tags'].split(','):
            tag = tag.strip().lower()
            if tag:
                tag_counts[tag] += 1
    return [{"tag": t, "count": c} for t, c in tag_counts.most_common(limit)]


def get_user_world_id(user_id):
    """Get the world ID owned by a user. Returns world_id or None."""
    conn = get_conn()
    row = conn.execute("SELECT id FROM worlds WHERE owner=?", (user_id,)).fetchone()
    conn.close()
    return row['id'] if row else None

# Initialize DB on import
init_db()
init_coins()

# ── Farming System ────────────────────────────────────────────

def init_farming():
    """Create farming tables if not exist."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS crops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT DEFAULT 'default',
        col INTEGER NOT NULL,
        row INTEGER NOT NULL,
        crop_type TEXT DEFAULT 'carrot',
        planted_at REAL NOT NULL,
        grow_seconds INTEGER DEFAULT 120,
        stage TEXT DEFAULT 'seedling',
        harvested INTEGER DEFAULT 0,
        stolen INTEGER DEFAULT 0,
        last_watered REAL DEFAULT 0,
        watered_boost_until REAL DEFAULT 0,
        ts REAL
    );
    CREATE TABLE IF NOT EXISTS steal_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT DEFAULT 'default',
        crop_id INTEGER NOT NULL,
        thief_ip TEXT DEFAULT '',
        thief_name TEXT DEFAULT 'Anonymous',
        crop_type TEXT DEFAULT 'carrot',
        ts REAL
    );
    CREATE TABLE IF NOT EXISTS player_turnips (
        world_id TEXT PRIMARY KEY,
        amount INTEGER DEFAULT 0,
        bought_price INTEGER DEFAULT 0,
        bought_day TEXT DEFAULT '',
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS feed_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT DEFAULT 'default',
        event_type TEXT NOT NULL,
        description TEXT DEFAULT '',
        emoji TEXT DEFAULT '🌱',
        ts REAL
    );
    """)
    # Migration: add watering columns to existing crops table
    try:
        conn.execute("ALTER TABLE crops ADD COLUMN last_watered REAL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE crops ADD COLUMN watered_boost_until REAL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.commit()
    conn.close()

# Crop helpers
def plant_crop(world_id, col, row, crop_type='carrot', grow_seconds=120):
    """Plant a crop. Returns crop id."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    # Remove any existing crop at same location
    conn.execute("DELETE FROM crops WHERE world_id=? AND col=? AND row=? AND harvested=0 AND stolen=0",
                 (world_id, col, row))
    cursor = conn.execute(
        "INSERT INTO crops (world_id, col, row, crop_type, planted_at, grow_seconds, stage, harvested, stolen, ts) VALUES (?,?,?,?,?,?,'seedling',0,0,?)",
        (world_id, col, row, crop_type, now, grow_seconds, now)
    )
    crop_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return crop_id

def get_crops(world_id='default'):
    """Get all active (not harvested, not stolen) crops with current stage."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM crops WHERE world_id=? AND harvested=0 AND stolen=0",
        (world_id,)
    ).fetchall()
    conn.close()
    crops = []
    for r in rows:
        c = dict(r)
        elapsed = now - c['planted_at']
        grow_s = c['grow_seconds']
        pct = elapsed / grow_s if grow_s > 0 else 1.0
        if pct < 0.25:
            c['stage'] = 'seed'
        elif pct < 0.5:
            c['stage'] = 'sprout'
        elif pct < 1.0:
            c['stage'] = 'growing'
        else:
            c['stage'] = 'ripe'
        crops.append(c)
    return crops

def water_crop(world_id, crop_id):
    """Water a crop to speed up growth by 20%. Returns crop data or None."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM crops WHERE id=? AND world_id=? AND harvested=0 AND stolen=0",
        (crop_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    c = dict(row)
    elapsed = now - c['planted_at']
    if elapsed >= c['grow_seconds']:
        conn.close()
        return None  # already ripe
    # Reduce grow time by 20%
    new_grow = max(10, int(c['grow_seconds'] * 0.8))
    conn.execute("UPDATE crops SET grow_seconds=?, ts=? WHERE id=?", (new_grow, now, crop_id))
    conn.commit()
    c['grow_seconds'] = new_grow
    conn.close()
    return c

def harvest_crop(world_id, crop_id):
    """Harvest a ripe crop. Returns crop data or None if not ripe."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM crops WHERE id=? AND world_id=? AND harvested=0 AND stolen=0",
        (crop_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    c = dict(row)
    elapsed = now - c['planted_at']
    if elapsed < c['grow_seconds']:
        conn.close()
        return None  # not ripe yet
    conn.execute("UPDATE crops SET harvested=1, stage='harvested', ts=? WHERE id=?", (now, crop_id))
    conn.commit()
    conn.close()
    return c

def steal_crop(world_id, crop_id, thief_ip, thief_name='Anonymous'):
    """Steal a ripe crop. Returns crop or None.
    Rate limit: each thief can steal up to 5 crops per world per day (like QQ Farm)."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    # Check if this thief already stole too many from this world today
    today_start = datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM steal_log WHERE world_id=? AND thief_name=? AND ts>=?",
        (world_id, thief_name, today_start)
    ).fetchone()
    if existing['cnt'] >= 5:  # max 5 steals per world per day
        conn.close()
        return None, "already_stolen_today"
    
    row = conn.execute(
        "SELECT * FROM crops WHERE id=? AND world_id=? AND harvested=0 AND stolen=0",
        (crop_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return None, "not_found"
    
    c = dict(row)
    elapsed = now - c['planted_at']
    if elapsed < c['grow_seconds']:
        conn.close()
        return None, "not_ripe"
    
    conn.execute("UPDATE crops SET stolen=1, stage='stolen', ts=? WHERE id=?", (now, crop_id))
    conn.execute(
        "INSERT INTO steal_log (world_id, crop_id, thief_ip, thief_name, crop_type, ts) VALUES (?,?,?,?,?,?)",
        (world_id, crop_id, thief_ip, thief_name, c['crop_type'], now)
    )
    conn.commit()
    conn.close()
    return c, "ok"

# ── Sprint 14: New farming helpers ─────────────────────────────

def get_crops_with_watering(world_id='default'):
    """Get all active crops including watering fields."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM crops WHERE world_id=? AND harvested=0 AND stolen=0",
        (world_id,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        c = dict(r)
        # Ensure watering fields exist (backward compat)
        c.setdefault('last_watered', 0)
        c.setdefault('watered_boost_until', 0)
        result.append(c)
    return result

def water_crop_boost(world_id, crop_id):
    """Water a crop — doubles growth speed for 60s. Returns crop dict or None."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM crops WHERE id=? AND world_id=? AND harvested=0 AND stolen=0",
        (crop_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    c = dict(row)
    # Set watered_boost_until to now + 60s
    boost_until = now + 60
    conn.execute(
        "UPDATE crops SET last_watered=?, watered_boost_until=?, ts=? WHERE id=?",
        (now, boost_until, now, crop_id)
    )
    conn.commit()
    c['last_watered'] = now
    c['watered_boost_until'] = boost_until
    conn.close()
    return c

def harvest_crop_v2(world_id, crop_id):
    """Harvest a ripe crop (v2 — stage check done in app.py). Returns crop dict or None."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM crops WHERE id=? AND world_id=? AND harvested=0 AND stolen=0",
        (crop_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    c = dict(row)
    conn.execute("UPDATE crops SET harvested=1, stage='harvested', ts=? WHERE id=?", (now, crop_id))
    conn.commit()
    conn.close()
    return c

def update_crop_stage(world_id, crop_id, stage_name):
    """Update the stage field in the DB."""
    conn = get_conn()
    conn.execute("UPDATE crops SET stage=? WHERE id=? AND world_id=?", (stage_name, crop_id, world_id))
    conn.commit()
    conn.close()

def get_farm_stats(world_id='default'):
    """Get total_harvested and total_stolen counts."""
    conn = get_conn()
    harvested = conn.execute(
        "SELECT COUNT(*) as cnt FROM crops WHERE world_id=? AND harvested=1",
        (world_id,)
    ).fetchone()['cnt']
    stolen = conn.execute(
        "SELECT COUNT(*) as cnt FROM crops WHERE world_id=? AND stolen=1",
        (world_id,)
    ).fetchone()['cnt']
    conn.close()
    return {'total_harvested': harvested, 'total_stolen': stolen}


# Feed events helpers
def add_feed_event(world_id, event_type, description, emoji='🌱'):
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    conn.execute(
        "INSERT INTO feed_events (world_id, event_type, description, emoji, ts) VALUES (?,?,?,?,?)",
        (world_id, event_type, description, emoji, now)
    )
    conn.commit()
    conn.close()

def get_feed_events(world_id='default', limit=30):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM feed_events WHERE world_id=? ORDER BY ts DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Turnip market helpers
def get_player_turnips(world_id='default'):
    conn = get_conn()
    row = conn.execute("SELECT * FROM player_turnips WHERE world_id=?", (world_id,)).fetchone()
    conn.close()
    return dict(row) if row else {'world_id': world_id, 'amount': 0, 'bought_price': 0, 'bought_day': '', 'updated_at': ''}

def set_player_turnips(world_id, amount, bought_price=0, bought_day=''):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO player_turnips (world_id, amount, bought_price, bought_day, updated_at)
        VALUES (?,?,?,?,?)
    """, (world_id, amount, bought_price, bought_day, now))
    conn.commit()
    conn.close()

# Run migration on import
init_farming()

# ── Daily Spin & Combat System ────────────────────────────────

def init_combat():
    """Create tables for spin/raid/shield system."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS daily_spins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        result TEXT NOT NULL,
        value INTEGER DEFAULT 0,
        target_world TEXT DEFAULT '',
        ts REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS shields (
        world_id TEXT PRIMARY KEY,
        count INTEGER DEFAULT 0,
        max_count INTEGER DEFAULT 3,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS raids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raider_world TEXT NOT NULL,
        raider_name TEXT DEFAULT '',
        target_world TEXT NOT NULL,
        coins_stolen INTEGER DEFAULT 0,
        blocked_by_shield INTEGER DEFAULT 0,
        ts REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS attacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_world TEXT NOT NULL,
        attacker_name TEXT DEFAULT '',
        target_world TEXT NOT NULL,
        destroyed_object TEXT DEFAULT '',
        repair_cost INTEGER DEFAULT 0,
        blocked_by_shield INTEGER DEFAULT 0,
        ts REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS destroyed_objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        object_id TEXT NOT NULL,
        object_type TEXT NOT NULL,
        col INTEGER DEFAULT 0,
        row INTEGER DEFAULT 0,
        repair_cost INTEGER DEFAULT 0,
        repaired INTEGER DEFAULT 0,
        destroyed_by TEXT DEFAULT '',
        ts REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS action_tokens (
        world_id TEXT NOT NULL,
        token_type TEXT NOT NULL,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (world_id, token_type)
    );
    """)
    conn.commit()
    conn.close()

def get_tokens(world_id):
    """Get attack and raid token counts."""
    conn = get_conn()
    rows = conn.execute("SELECT token_type, count FROM action_tokens WHERE world_id=?", (world_id,)).fetchall()
    conn.close()
    result = {'attack': 0, 'raid': 0}
    for r in rows:
        result[r['token_type']] = r['count']
    return result

def add_token(world_id, token_type, amount=1):
    """Add action tokens."""
    conn = get_conn()
    conn.execute("""
        INSERT INTO action_tokens (world_id, token_type, count) VALUES (?,?,?)
        ON CONFLICT(world_id, token_type) DO UPDATE SET count=count+?
    """, (world_id, token_type, amount, amount))
    conn.commit()
    conn.close()

def use_token(world_id, token_type):
    """Use 1 token. Returns True if available."""
    conn = get_conn()
    row = conn.execute("SELECT count FROM action_tokens WHERE world_id=? AND token_type=?",
                       (world_id, token_type)).fetchone()
    if not row or row['count'] <= 0:
        conn.close()
        return False
    conn.execute("UPDATE action_tokens SET count=count-1 WHERE world_id=? AND token_type=?",
                 (world_id, token_type))
    conn.commit()
    conn.close()
    return True

def get_spins_today(world_id):
    """Count how many spins a world has used today."""
    today_start = datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM daily_spins WHERE world_id=? AND ts>=?",
        (world_id, today_start)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0

def record_spin(world_id, result, value=0, target_world=''):
    """Record a spin result."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_spins (world_id, result, value, target_world, ts) VALUES (?,?,?,?,?)",
        (world_id, result, value, target_world, now)
    )
    conn.commit()
    conn.close()

def get_shields(world_id):
    """Get current shield count for a world."""
    conn = get_conn()
    row = conn.execute("SELECT count FROM shields WHERE world_id=?", (world_id,)).fetchone()
    conn.close()
    return row['count'] if row else 0

def add_shield(world_id, amount=1, max_shields=3):
    """Add shields (capped at max)."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT INTO shields (world_id, count, max_count, updated_at) VALUES (?,?,?,?)
        ON CONFLICT(world_id) DO UPDATE SET count=MIN(count+?, ?), updated_at=?
    """, (world_id, min(amount, max_shields), max_shields, now, amount, max_shields, now))
    conn.commit()
    current = get_shields(world_id)
    conn.close()
    return current

def use_shield(world_id):
    """Use 1 shield. Returns True if shield was available."""
    conn = get_conn()
    row = conn.execute("SELECT count FROM shields WHERE world_id=?", (world_id,)).fetchone()
    if not row or row['count'] <= 0:
        conn.close()
        return False
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE shields SET count=count-1, updated_at=? WHERE world_id=?", (now, world_id))
    conn.commit()
    conn.close()
    return True

def record_raid(raider_world, raider_name, target_world, coins_stolen, blocked=False):
    """Record a raid event."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    conn.execute(
        "INSERT INTO raids (raider_world, raider_name, target_world, coins_stolen, blocked_by_shield, ts) VALUES (?,?,?,?,?,?)",
        (raider_world, raider_name, target_world, coins_stolen, 1 if blocked else 0, now)
    )
    conn.commit()
    conn.close()

def record_attack(attacker_world, attacker_name, target_world, destroyed_object='', repair_cost=0, blocked=False):
    """Record an attack event."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    conn.execute(
        "INSERT INTO attacks (attacker_world, attacker_name, target_world, destroyed_object, repair_cost, blocked_by_shield, ts) VALUES (?,?,?,?,?,?,?)",
        (attacker_world, attacker_name, target_world, destroyed_object, repair_cost, 1 if blocked else 0, now)
    )
    conn.commit()
    conn.close()

def add_destroyed_object(world_id, object_id, object_type, col, row, repair_cost, destroyed_by=''):
    """Mark an object as destroyed (needs repair)."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    conn.execute(
        "INSERT INTO destroyed_objects (world_id, object_id, object_type, col, row, repair_cost, repaired, destroyed_by, ts) VALUES (?,?,?,?,?,?,0,?,?)",
        (world_id, object_id, object_type, col, row, repair_cost, destroyed_by, now)
    )
    conn.commit()
    conn.close()

def get_destroyed_objects(world_id):
    """Get all unrepaired destroyed objects."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM destroyed_objects WHERE world_id=? AND repaired=0",
        (world_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def repair_object(destroyed_id):
    """Mark a destroyed object as repaired."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("UPDATE destroyed_objects SET repaired=1 WHERE id=?", (destroyed_id,))
    conn.commit()
    conn.close()

def get_recent_raids(world_id, limit=10):
    """Get recent raids against a world."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM raids WHERE target_world=? ORDER BY ts DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_recent_attacks(world_id, limit=10):
    """Get recent attacks against a world."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM attacks WHERE target_world=? ORDER BY ts DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

init_combat()

# ── Ranch / Pasture System ────────────────────────────────────

def init_ranch():
    """Create ranch tables if not exist."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS animals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT DEFAULT 'default',
        col INTEGER NOT NULL,
        row INTEGER NOT NULL,
        animal_type TEXT DEFAULT 'chicken',
        placed_at REAL NOT NULL,
        grow_seconds INTEGER DEFAULT 120,
        last_fed REAL DEFAULT 0,
        fed_boost_until REAL DEFAULT 0,
        last_collected REAL DEFAULT 0,
        collect_cooldown INTEGER DEFAULT 90,
        stage TEXT DEFAULT 'baby',
        collected INTEGER DEFAULT 0,
        feed_count INTEGER DEFAULT 0,
        collect_count INTEGER DEFAULT 0,
        ts REAL
    );
    """)
    conn.commit()
    conn.close()


def place_animal(world_id, col, row, animal_type='chicken', grow_seconds=120, collect_cooldown=90):
    """Place an animal. Returns animal id."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    # Remove any existing animal at same location
    conn.execute("DELETE FROM animals WHERE world_id=? AND col=? AND row=? AND collected=0",
                 (world_id, col, row))
    cursor = conn.execute(
        "INSERT INTO animals (world_id, col, row, animal_type, placed_at, grow_seconds, collect_cooldown, stage, collected, last_fed, fed_boost_until, last_collected, feed_count, collect_count, ts) VALUES (?,?,?,?,?,?,?,'baby',0,0,0,0,0,0,?)",
        (world_id, col, row, animal_type, now, grow_seconds, collect_cooldown, now)
    )
    animal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return animal_id


def get_animals(world_id='default'):
    """Get all active (not collected/removed) animals with current stage."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM animals WHERE world_id=? AND collected=0",
        (world_id,)
    ).fetchall()
    conn.close()
    animals = []
    for r in rows:
        a = dict(r)
        a.setdefault('last_fed', 0)
        a.setdefault('fed_boost_until', 0)
        a.setdefault('last_collected', 0)
        elapsed = now - a['placed_at']
        grow_s = a['grow_seconds']
        if elapsed >= grow_s:
            # Animal is adult — check if product is ready
            last_collect = a.get('last_collected', 0) or 0
            cooldown = a.get('collect_cooldown', 90) or 90
            if last_collect > 0:
                time_since_collect = now - last_collect
                if time_since_collect >= cooldown:
                    a['stage'] = 'ready'
                else:
                    a['stage'] = 'adult'
            else:
                # Never collected — ready once adult + cooldown passed
                time_since_adult = elapsed - grow_s
                if time_since_adult >= cooldown:
                    a['stage'] = 'ready'
                else:
                    a['stage'] = 'adult'
        else:
            pct = elapsed / grow_s if grow_s > 0 else 1.0
            if pct < 0.5:
                a['stage'] = 'baby'
            else:
                a['stage'] = 'growing'
        animals.append(a)
    return animals


def feed_animal_boost(world_id, animal_id):
    """Feed an animal — doubles growth/collection speed for 60s. Returns animal dict or None."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM animals WHERE id=? AND world_id=? AND collected=0",
        (animal_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    a = dict(row)
    boost_until = now + 60
    conn.execute(
        "UPDATE animals SET last_fed=?, fed_boost_until=?, feed_count=feed_count+1, ts=? WHERE id=?",
        (now, boost_until, now, animal_id)
    )
    conn.commit()
    a['last_fed'] = now
    a['fed_boost_until'] = boost_until
    conn.close()
    return a


def collect_animal_product(world_id, animal_id):
    """Collect product from a ready animal. Returns animal dict or None if not ready."""
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM animals WHERE id=? AND world_id=? AND collected=0",
        (animal_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    a = dict(row)
    elapsed = now - a['placed_at']
    if elapsed < a['grow_seconds']:
        conn.close()
        return None  # still baby/growing
    last_collect = a.get('last_collected', 0) or 0
    cooldown = a.get('collect_cooldown', 90) or 90
    if last_collect > 0:
        if (now - last_collect) < cooldown:
            conn.close()
            return None  # not ready yet
    else:
        time_since_adult = elapsed - a['grow_seconds']
        if time_since_adult < cooldown:
            conn.close()
            return None
    # Collect!
    conn.execute(
        "UPDATE animals SET last_collected=?, collect_count=collect_count+1, ts=? WHERE id=?",
        (now, now, animal_id)
    )
    conn.commit()
    a['last_collected'] = now
    a['collect_count'] = (a.get('collect_count', 0) or 0) + 1
    conn.close()
    return a


def get_ranch_stats(world_id='default'):
    """Get total collected count."""
    conn = get_conn()
    total = conn.execute(
        "SELECT COALESCE(SUM(collect_count), 0) as cnt FROM animals WHERE world_id=?",
        (world_id,)
    ).fetchone()['cnt']
    conn.close()
    return {'total_collected': total}


init_ranch()

# ── Economy System: Island Types, Inventory, Crafting, Market, Prices, Combat ──

import random as _random
import hashlib

def init_economy():
    """Create economy system tables."""
    conn = get_conn()
    # Add island_type to worlds
    try:
        conn.execute("ALTER TABLE worlds ADD COLUMN island_type TEXT DEFAULT 'farm'")
        conn.commit()
    except Exception:
        pass
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS inventory (
        world_id TEXT NOT NULL,
        resource TEXT NOT NULL,
        amount INTEGER DEFAULT 0,
        PRIMARY KEY (world_id, resource)
    );
    CREATE TABLE IF NOT EXISTS crafting_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        recipe_id TEXT NOT NULL,
        start_time REAL NOT NULL,
        done_time REAL NOT NULL,
        collected INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS market_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id TEXT NOT NULL,
        seller_name TEXT DEFAULT '',
        resource TEXT NOT NULL,
        amount INTEGER NOT NULL,
        price_per_unit INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT DEFAULT 'active'
    );
    CREATE TABLE IF NOT EXISTS gathering_plots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        zone_type TEXT NOT NULL,
        col INTEGER NOT NULL,
        row INTEGER NOT NULL,
        resource_type TEXT NOT NULL,
        planted_at REAL NOT NULL,
        grow_seconds INTEGER DEFAULT 120,
        stage TEXT DEFAULT 'placed',
        harvested INTEGER DEFAULT 0,
        ts REAL
    );
    CREATE TABLE IF NOT EXISTS defense_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        defense_type TEXT NOT NULL,
        placed_at TEXT NOT NULL,
        uses_remaining INTEGER DEFAULT 1,
        active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS servants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        servant_type TEXT NOT NULL,
        durability INTEGER DEFAULT 20,
        max_durability INTEGER DEFAULT 20,
        created_at TEXT NOT NULL,
        last_used TEXT DEFAULT '',
        total_uses INTEGER DEFAULT 0
    );
    """)
    conn.commit()
    # Migration: add land_level column for land expansion system
    try:
        conn.execute("ALTER TABLE worlds ADD COLUMN land_level INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.close()

# ── Land Expansion System ─────────────────────────────────────
# Defines island land levels: each upgrade increases map size and farm plots
LAND_LEVELS = {
    0: {'name': 'Starter',  'size': 24, 'cost': 0,    'farm_plots': 16},
    1: {'name': 'Expanded', 'size': 32, 'cost': 500,  'farm_plots': 20},
    2: {'name': 'Large',    'size': 40, 'cost': 2000, 'farm_plots': 25},
    3: {'name': 'Massive',  'size': 48, 'cost': 5000, 'farm_plots': 30},
}


def get_land_level(world_id):
    """Get current land level and info for a world.
    Returns dict with level, name, size, farm_plots, and next_level info."""
    conn = get_conn()
    row = conn.execute("SELECT land_level FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    current_level = row['land_level'] if row and row['land_level'] is not None else 0
    current_info = LAND_LEVELS.get(current_level, LAND_LEVELS[0])
    # Next level info (None if already max)
    next_level = current_level + 1
    next_info = LAND_LEVELS.get(next_level)
    result = {
        'level': current_level,
        'name': current_info['name'],
        'size': current_info['size'],
        'farm_plots': current_info['farm_plots'],
        'max_level': max(LAND_LEVELS.keys()),
    }
    if next_info:
        result['next'] = {
            'level': next_level,
            'name': next_info['name'],
            'size': next_info['size'],
            'cost': next_info['cost'],
            'farm_plots': next_info['farm_plots'],
        }
    else:
        result['next'] = None
    return result


def upgrade_land(world_id):
    """Upgrade land to the next level (deducts coins from owner).
    Returns {'ok': True, ...} on success, or {'ok': False, 'error': ...} on failure."""
    conn = get_conn()
    row = conn.execute("SELECT land_level FROM worlds WHERE id=?", (world_id,)).fetchone()
    current_level = row['land_level'] if row and row['land_level'] is not None else 0
    next_level = current_level + 1
    next_info = LAND_LEVELS.get(next_level)
    if not next_info:
        conn.close()
        return {'ok': False, 'error': 'Already at maximum land level'}
    conn.close()
    # Deduct coins
    cost = next_info['cost']
    spend_result = spend_coins(world_id, cost, f'land_upgrade_to_{next_level}')
    if not spend_result['ok']:
        return {'ok': False, 'error': 'Not enough coins', 'coins': spend_result.get('coins', 0), 'need': cost}
    # Apply upgrade
    conn = get_conn()
    conn.execute("UPDATE worlds SET land_level=? WHERE id=?", (next_level, world_id))
    conn.commit()
    conn.close()
    return {
        'ok': True,
        'new_level': next_level,
        'name': next_info['name'],
        'size': next_info['size'],
        'farm_plots': next_info['farm_plots'],
        'cost': cost,
        'remaining_coins': spend_result['remaining'],
    }


ISLAND_TYPES = ['farm', 'fish', 'mine', 'forest']

ISLAND_RESOURCES = {
    'farm':   {'primary': ['cabbage', 'carrot', 'pumpkin'], 'secondary': ['wood', 'fruit'], 'weak': ['fish', 'iron_ore']},
    'fish':   {'primary': ['fish', 'shrimp', 'pearl'],      'secondary': ['iron_ore', 'stone'], 'weak': ['wood', 'cabbage']},
    'mine':   {'primary': ['iron_ore', 'gem', 'stone'],     'secondary': ['fish', 'shrimp'],   'weak': ['wood', 'cabbage']},
    'forest': {'primary': ['wood', 'fruit', 'mushroom'],    'secondary': ['cabbage'],          'weak': ['fish', 'iron_ore']},
}

RESOURCE_YIELD = {'primary': 5.0, 'secondary': 1.0, 'weak': 0.2}

RESOURCE_GROW_TIMES = {
    'cabbage': 120, 'carrot': 180, 'pumpkin': 300, 'turnip': 240,
    'fish': 150, 'shrimp': 180, 'pearl': 360,
    'iron_ore': 200, 'gem': 400, 'stone': 150,
    'wood': 180, 'fruit': 150, 'mushroom': 240,
}

RESOURCE_EMOJIS = {
    'cabbage': '🥬', 'carrot': '🥕', 'pumpkin': '🎃', 'turnip': '🫑',
    'fish': '🐟', 'shrimp': '🦐', 'pearl': '🦪',
    'iron_ore': '⛏️', 'gem': '💎', 'stone': '🪨',
    'wood': '🪵', 'fruit': '🍎', 'mushroom': '🍄',
    'axe': '🪓', 'warhammer': '⚒️', 'bomb': '💣', 'torch': '🔥',
    'servant_gatherer': '🦞', 'servant_thief': '🦹', 'servant_trader': '🏪',
    'stone_wall_defense': '🧱', 'watchtower': '🗼', 'guard_dog': '🐕',
}

RESOURCE_STAGE_EMOJIS = {
    'farm':   {'placed': '🌱', 'growing': '🌿', 'almost': '🌾', 'ready': '🥬'},
    'fish':   {'placed': '🪤', 'growing': '🫧', 'almost': '🐟', 'ready': '🐟'},
    'mine':   {'placed': '⛏️', 'growing': '🪨', 'almost': '💎', 'ready': '💎'},
    'forest': {'placed': '🌱', 'growing': '🌲', 'almost': '🪵', 'ready': '🪵'},
}

def get_island_type(world_id):
    conn = get_conn()
    row = conn.execute("SELECT island_type FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    if row and row['island_type']:
        return row['island_type']
    return 'farm'

def set_island_type(world_id, island_type):
    conn = get_conn()
    conn.execute("UPDATE worlds SET island_type=? WHERE id=?", (island_type, world_id))
    conn.commit()
    conn.close()

def assign_random_island_type(world_id):
    current = get_island_type(world_id)
    if current and current != 'farm':
        return current
    itype = _random.choice(ISLAND_TYPES)
    set_island_type(world_id, itype)
    return itype

def get_resource_tier(island_type, resource):
    info = ISLAND_RESOURCES.get(island_type, ISLAND_RESOURCES['farm'])
    if resource in info['primary']:
        return 'primary'
    elif resource in info['secondary']:
        return 'secondary'
    elif resource in info['weak']:
        return 'weak'
    return None

# ── Inventory ─────────────────────────────────────────────────

def get_inventory(world_id):
    conn = get_conn()
    rows = conn.execute("SELECT resource, amount FROM inventory WHERE world_id=? AND amount>0", (world_id,)).fetchall()
    conn.close()
    return {r['resource']: r['amount'] for r in rows}

def add_to_inventory(world_id, resource, amount):
    if amount <= 0:
        return
    conn = get_conn()
    conn.execute("""
        INSERT INTO inventory (world_id, resource, amount) VALUES (?,?,?)
        ON CONFLICT(world_id, resource) DO UPDATE SET amount=amount+?
    """, (world_id, resource, amount, amount))
    conn.commit()
    conn.close()

def remove_from_inventory(world_id, resource, amount):
    conn = get_conn()
    row = conn.execute("SELECT amount FROM inventory WHERE world_id=? AND resource=?", (world_id, resource)).fetchone()
    current = row['amount'] if row else 0
    if current < amount:
        conn.close()
        return False
    new_amount = current - amount
    if new_amount <= 0:
        conn.execute("DELETE FROM inventory WHERE world_id=? AND resource=?", (world_id, resource))
    else:
        conn.execute("UPDATE inventory SET amount=? WHERE world_id=? AND resource=?", (new_amount, world_id, resource))
    conn.commit()
    conn.close()
    return True

def check_inventory(world_id, requirements):
    inv = get_inventory(world_id)
    missing = {}
    for res, need in requirements.items():
        have = inv.get(res, 0)
        if have < need:
            missing[res] = need - have
    return len(missing) == 0, missing

def deduct_inventory(world_id, requirements):
    ok, missing = check_inventory(world_id, requirements)
    if not ok:
        return False
    for res, amount in requirements.items():
        if not remove_from_inventory(world_id, res, amount):
            return False
    return True

# ── Gathering Plots ───────────────────────────────────────────

def place_gathering(world_id, zone_type, col, row, resource_type, grow_seconds=120):
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    conn.execute("DELETE FROM gathering_plots WHERE world_id=? AND col=? AND row=? AND harvested=0",
                 (world_id, col, row))
    cursor = conn.execute(
        "INSERT INTO gathering_plots (world_id, zone_type, col, row, resource_type, planted_at, grow_seconds, stage, harvested, ts) VALUES (?,?,?,?,?,?,?,'placed',0,?)",
        (world_id, zone_type, col, row, resource_type, now, grow_seconds, now)
    )
    plot_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plot_id

def get_gathering_plots(world_id):
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM gathering_plots WHERE world_id=? AND harvested=0",
        (world_id,)
    ).fetchall()
    conn.close()
    plots = []
    for r in rows:
        p = dict(r)
        elapsed = now - p['planted_at']
        grow_s = p['grow_seconds']
        pct = elapsed / grow_s if grow_s > 0 else 1.0
        if pct < 0.33:
            p['stage'] = 'placed'
        elif pct < 0.66:
            p['stage'] = 'growing'
        elif pct < 1.0:
            p['stage'] = 'almost'
        else:
            p['stage'] = 'ready'
        p['progress'] = min(1.0, pct)
        plots.append(p)
    return plots

def harvest_gathering(world_id, plot_id):
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM gathering_plots WHERE id=? AND world_id=? AND harvested=0",
        (plot_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    p = dict(row)
    elapsed = now - p['planted_at']
    if elapsed < p['grow_seconds']:
        conn.close()
        return None
    conn.execute("UPDATE gathering_plots SET harvested=1, stage='harvested', ts=? WHERE id=?", (now, plot_id))
    conn.commit()
    conn.close()
    return p

# ── Crafting ──────────────────────────────────────────────────

RECIPES = {
    # ⚔️ Weapons (Lv2) — destroy enemy buildings. Expensive to discourage spam.
    'axe':              {'name': 'Axe 🪓',             'inputs': {'wood': 8, 'iron_ore': 3},               'output': 'axe',              'time': 15, 'min_level': 2, 'category': 'weapon', 'coin_cost': 100},
    'warhammer':        {'name': 'War Hammer ⚒️',      'inputs': {'iron_ore': 8, 'stone': 5},              'output': 'warhammer',        'time': 20, 'min_level': 2, 'category': 'weapon', 'coin_cost': 200},
    'bomb':             {'name': 'Bomb 💣',            'inputs': {'iron_ore': 5, 'gem': 2, 'mushroom': 5}, 'output': 'bomb',             'time': 25, 'min_level': 3, 'category': 'weapon', 'coin_cost': 500},
    'torch':            {'name': 'Torch 🔥',           'inputs': {'wood': 3, 'fruit': 3},                  'output': 'torch',            'time': 10, 'min_level': 2, 'category': 'weapon', 'coin_cost': 50},
    # 🦞 Servants (Lv2/3) — automation. Very expensive: snowball effect.
    'servant_gatherer': {'name': 'Gatherer 🦞',        'inputs': {'wood': 20, 'iron_ore': 10},             'output': 'servant_gatherer', 'time': 30, 'min_level': 2, 'category': 'servant', 'coin_cost': 1000},
    'servant_thief':    {'name': 'Thief 🦹',           'inputs': {'gem': 5, 'mushroom': 10},               'output': 'servant_thief',    'time': 30, 'min_level': 3, 'category': 'servant', 'coin_cost': 2000},
    'servant_trader':   {'name': 'Trader 🏪',          'inputs': {'pearl': 5, 'fish': 15},                 'output': 'servant_trader',   'time': 30, 'min_level': 3, 'category': 'servant', 'coin_cost': 3000},
    # 🛡️ Defense (Lv2) — protect your island. Moderate cost.
    'stone_wall_defense': {'name': 'Stone Wall 🧱',    'inputs': {'stone': 10},                            'output': 'stone_wall_defense', 'time': 20, 'min_level': 2, 'category': 'defense', 'coin_cost': 50},
    'watchtower':       {'name': 'Watchtower 🗼',      'inputs': {'wood': 10, 'iron_ore': 5},              'output': 'watchtower',       'time': 25, 'min_level': 2, 'category': 'defense', 'coin_cost': 150},
    'guard_dog':        {'name': 'Guard Dog 🐕',       'inputs': {'fish': 15, 'cabbage': 10},              'output': 'guard_dog',        'time': 30, 'min_level': 2, 'category': 'defense', 'coin_cost': 200},
}

def start_crafting(world_id, recipe_id):
    recipe = RECIPES.get(recipe_id)
    if not recipe:
        return {'ok': False, 'error': 'Unknown recipe'}
    progress = get_progress(world_id)
    player_level = progress['level'] if progress else 1
    if player_level < recipe.get('min_level', 1):
        return {'ok': False, 'error': f'Need level {recipe["min_level"]}'}
    ok, missing = check_inventory(world_id, recipe['inputs'])
    if not ok:
        return {'ok': False, 'error': 'Missing resources', 'missing': missing}
    if not deduct_inventory(world_id, recipe['inputs']):
        return {'ok': False, 'error': 'Failed to deduct resources'}
    # After deducting resources, check coin_cost
    coin_cost = recipe.get('coin_cost', 0)
    if coin_cost > 0:
        wallet = get_wallet(world_id)
        if wallet['coins'] < coin_cost:
            # Refund resources (add back)
            for res, amt in recipe['inputs'].items():
                add_to_inventory(world_id, res, amt)
            return {'ok': False, 'error': f'Need {coin_cost} coins'}
        spend_coins(world_id, coin_cost, f'craft_{recipe_id}')
    now = datetime.now(timezone.utc).timestamp()
    done_time = now + recipe['time']
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO crafting_queue (world_id, recipe_id, start_time, done_time, collected) VALUES (?,?,?,?,0)",
        (world_id, recipe_id, now, done_time)
    )
    craft_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {'ok': True, 'craft_id': craft_id, 'recipe': recipe_id, 'done_in': recipe['time']}

def get_crafting_queue(world_id):
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    rows = conn.execute("SELECT * FROM crafting_queue WHERE world_id=? AND collected=0", (world_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        item = dict(r)
        item['done'] = now >= item['done_time']
        item['remaining'] = max(0, item['done_time'] - now)
        recipe = RECIPES.get(item['recipe_id'], {})
        item['recipe_name'] = recipe.get('name', item['recipe_id'])
        item['output'] = recipe.get('output', '')
        result.append(item)
    return result

def collect_crafted(world_id, craft_id):
    now = datetime.now(timezone.utc).timestamp()
    conn = get_conn()
    row = conn.execute("SELECT * FROM crafting_queue WHERE id=? AND world_id=? AND collected=0", (craft_id, world_id)).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Not found'}
    if now < row['done_time']:
        conn.close()
        return {'ok': False, 'error': 'Not done yet', 'remaining': row['done_time'] - now}
    recipe = RECIPES.get(row['recipe_id'], {})
    output = recipe.get('output', '')
    conn.execute("UPDATE crafting_queue SET collected=1 WHERE id=?", (craft_id,))
    conn.commit()
    conn.close()
    if output:
        add_to_inventory(world_id, output, 1)
    return {'ok': True, 'item': output, 'emoji': RESOURCE_EMOJIS.get(output, '📦')}

# ── Market ────────────────────────────────────────────────────

MARKET_TAX_RATE = 0.05

def create_sell_order(world_id, seller_name, resource, amount, price_per_unit):
    if amount <= 0 or price_per_unit <= 0:
        return {'ok': False, 'error': 'Invalid amount or price'}
    if not remove_from_inventory(world_id, resource, amount):
        return {'ok': False, 'error': 'Not enough resources'}
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO market_orders (seller_id, seller_name, resource, amount, price_per_unit, created_at, status) VALUES (?,?,?,?,?,?,'active')",
        (world_id, seller_name, resource, amount, price_per_unit, now)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {'ok': True, 'order_id': order_id}

def get_market_orders(resource=None, limit=50):
    conn = get_conn()
    if resource:
        rows = conn.execute("SELECT * FROM market_orders WHERE status='active' AND resource=? ORDER BY price_per_unit ASC LIMIT ?", (resource, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM market_orders WHERE status='active' ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_my_orders(world_id, limit=20):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM market_orders WHERE seller_id=? AND status='active' ORDER BY created_at DESC LIMIT ?", (world_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def buy_market_order(buyer_world_id, order_id, buy_amount=None):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM market_orders WHERE id=? AND status='active'", (order_id,)).fetchone()
        if not row:
            conn.close()
            return {'ok': False, 'error': 'Order not found or already sold'}
        order = dict(row)
        if order['seller_id'] == buyer_world_id:
            conn.close()
            return {'ok': False, 'error': 'Cannot buy your own order'}
        amount = buy_amount if buy_amount and buy_amount <= order['amount'] else order['amount']
        total_cost = amount * order['price_per_unit']
        tax = int(total_cost * MARKET_TAX_RATE)
        seller_receives = total_cost - tax
        wallet = get_wallet(buyer_world_id)
        if wallet['coins'] < total_cost:
            conn.close()
            return {'ok': False, 'error': 'Not enough coins', 'need': total_cost, 'have': wallet['coins']}
        spend_result = spend_coins(buyer_world_id, total_cost, f'market_buy_{order["resource"]}')
        if not spend_result['ok']:
            conn.close()
            return spend_result
        earn_coins(order['seller_id'], seller_receives, f'market_sell_{order["resource"]}')
        add_to_inventory(buyer_world_id, order['resource'], amount)
        remaining = order['amount'] - amount
        if remaining <= 0:
            conn.execute("UPDATE market_orders SET status='sold', amount=0 WHERE id=?", (order_id,))
        else:
            conn.execute("UPDATE market_orders SET amount=? WHERE id=?", (remaining, order_id))
        conn.commit()
        conn.close()
        return {'ok': True, 'resource': order['resource'], 'amount': amount, 'cost': total_cost, 'tax': tax, 'seller_received': seller_receives}
    except Exception as e:
        conn.close()
        return {'ok': False, 'error': str(e)}

def cancel_market_order(world_id, order_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM market_orders WHERE id=? AND seller_id=? AND status='active'", (order_id, world_id)).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Order not found'}
    order = dict(row)
    conn.execute("UPDATE market_orders SET status='cancelled' WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    add_to_inventory(world_id, order['resource'], order['amount'])
    return {'ok': True, 'returned': order['resource'], 'amount': order['amount']}

# ── Price System ──────────────────────────────────────────────

BASE_PRICES = {
    'cabbage': 8, 'carrot': 12, 'pumpkin': 20, 'turnip': 15,
    'fish': 10, 'shrimp': 15, 'pearl': 50,
    'iron_ore': 12, 'gem': 60, 'stone': 8,
    'wood': 10, 'fruit': 8, 'mushroom': 12,
    'furniture': 40, 'tool': 35, 'bento': 30, 'jewelry': 100, 'premium_building': 80,
}

def get_daily_price(resource, day_str=None):
    if day_str is None:
        day_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    base = BASE_PRICES.get(resource, 10)
    seed = f"{resource}:{day_str}"
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    if resource == 'turnip':
        coeff = 0.5 + (h % 450) / 100.0
    else:
        coeff = 0.7 + (h % 80) / 100.0
    return max(1, int(base * coeff))

def get_all_prices(day_str=None):
    if day_str is None:
        day_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    from datetime import timedelta
    yesterday = (datetime.strptime(day_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    prices = {}
    for res in BASE_PRICES:
        today_p = get_daily_price(res, day_str)
        yest_p = get_daily_price(res, yesterday)
        trend = 'up' if today_p > yest_p else ('down' if today_p < yest_p else 'flat')
        prices[res] = {
            'base': BASE_PRICES[res], 'today': today_p, 'yesterday': yest_p,
            'trend': trend, 'emoji': RESOURCE_EMOJIS.get(res, '📦'),
        }
    return prices

def get_price_history(resource, days=7):
    from datetime import timedelta
    today = datetime.now(timezone.utc).date()
    history = []
    for i in range(days-1, -1, -1):
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        history.append({'date': d, 'price': get_daily_price(resource, d)})
    return history

# ── Defense System ────────────────────────────────────────────

def place_defense(world_id, defense_type):
    if not remove_from_inventory(world_id, defense_type, 1):
        return {'ok': False, 'error': 'Not in inventory'}
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    existing = conn.execute("SELECT id, uses_remaining FROM defense_items WHERE world_id=? AND defense_type=? AND active=1", (world_id, defense_type)).fetchone()
    if existing:
        conn.execute("UPDATE defense_items SET uses_remaining=uses_remaining+1 WHERE id=?", (existing['id'],))
    else:
        conn.execute("INSERT INTO defense_items (world_id, defense_type, placed_at, uses_remaining, active) VALUES (?,?,?,1,1)", (world_id, defense_type, now))
    conn.commit()
    conn.close()
    return {'ok': True, 'defense': defense_type}

def get_defenses(world_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM defense_items WHERE world_id=? AND active=1 AND uses_remaining>0", (world_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def use_defense(world_id, defense_type):
    conn = get_conn()
    row = conn.execute("SELECT id, uses_remaining FROM defense_items WHERE world_id=? AND defense_type=? AND active=1 AND uses_remaining>0", (world_id, defense_type)).fetchone()
    if not row:
        conn.close()
        return False
    new_uses = row['uses_remaining'] - 1
    if new_uses <= 0:
        conn.execute("UPDATE defense_items SET uses_remaining=0, active=0 WHERE id=?", (row['id'],))
    else:
        conn.execute("UPDATE defense_items SET uses_remaining=? WHERE id=?", (new_uses, row['id']))
    conn.commit()
    conn.close()
    return True

def check_attack_cooldown(attacker_world, target_world):
    now = datetime.now(timezone.utc).timestamp()
    cooldown = 24 * 3600
    conn = get_conn()
    row = conn.execute("SELECT MAX(ts) as last_attack FROM attacks WHERE attacker_world=? AND target_world=?", (attacker_world, target_world)).fetchone()
    conn.close()
    if row and row['last_attack']:
        elapsed = now - row['last_attack']
        if elapsed < cooldown:
            return False, cooldown - elapsed
    return True, 0

def check_newbie_protection(world_id):
    conn = get_conn()
    row = conn.execute("SELECT created_at FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    if not row or not row['created_at']:
        return False
    try:
        created = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (now - created).total_seconds() < 3600
    except:
        return False

# ── Servant System ─────────────────────────────────────────────

SERVANT_TYPES = {
    'gatherer': {
        'name': 'Gatherer Lobster 🦞',
        'emoji': '🦞',
        'description': 'Auto-harvests your gathering zones',
        'craft_cost': {'wood': 10, 'iron_ore': 5},
        'coin_cost': 500,
        'use_cost': 50,
        'durability': 20,
        'min_level': 2,
    },
    'thief': {
        'name': 'Thief Lobster 🦞',
        'emoji': '🦹',
        'description': 'Steals resources from random islands',
        'craft_cost': {'gem': 3, 'mushroom': 5},
        'coin_cost': 800,
        'use_cost': 80,
        'durability': 20,
        'min_level': 3,
        'catch_chance': 0.3,
    },
    'trader': {
        'name': 'Trader Lobster 🦞',
        'emoji': '🏪',
        'description': 'Auto buys low and sells high on market',
        'craft_cost': {'pearl': 2, 'furniture': 3},
        'coin_cost': 1000,
        'use_cost': 100,
        'durability': 20,
        'min_level': 3,
    },
}


def create_servant(world_id, servant_type):
    """Create a servant. Checks resources + coins, deducts, creates. Max 1 per type."""
    if servant_type not in SERVANT_TYPES:
        return {'ok': False, 'error': f'Unknown servant type: {servant_type}'}
    stype = SERVANT_TYPES[servant_type]

    # Check player level
    progress = get_progress(world_id)
    player_level = progress['level'] if progress else 1
    if player_level < stype['min_level']:
        return {'ok': False, 'error': f'Need level {stype["min_level"]} to create this servant'}

    # Check max 1 per type
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM servants WHERE world_id=? AND servant_type=?",
        (world_id, servant_type)
    ).fetchone()
    if existing:
        conn.close()
        return {'ok': False, 'error': f'You already have a {stype["name"]}! Max 1 per type.'}
    conn.close()

    # Check resources
    ok, missing = check_inventory(world_id, stype['craft_cost'])
    if not ok:
        return {'ok': False, 'error': 'Not enough resources', 'missing': missing}

    # Check coins
    wallet = get_wallet(world_id)
    if wallet['coins'] < stype['coin_cost']:
        return {'ok': False, 'error': f'Not enough coins. Need {stype["coin_cost"]}, have {wallet["coins"]}'}

    # Deduct resources
    if not deduct_inventory(world_id, stype['craft_cost']):
        return {'ok': False, 'error': 'Failed to deduct resources'}

    # Deduct coins
    spend_result = spend_coins(world_id, stype['coin_cost'], f'create_servant_{servant_type}')
    if not spend_result['ok']:
        # Refund resources
        for res, amt in stype['craft_cost'].items():
            add_to_inventory(world_id, res, amt)
        return {'ok': False, 'error': 'Failed to deduct coins'}

    # Create servant
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO servants (world_id, servant_type, durability, max_durability, created_at) VALUES (?,?,?,?,?)",
        (world_id, servant_type, stype['durability'], stype['durability'], now)
    )
    servant_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        'ok': True,
        'servant_id': servant_id,
        'servant_type': servant_type,
        'name': stype['name'],
        'durability': stype['durability'],
    }


def get_servants(world_id):
    """Get all servants for a world."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM servants WHERE world_id=?", (world_id,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        s = dict(r)
        stype = SERVANT_TYPES.get(s['servant_type'], {})
        s['name'] = stype.get('name', s['servant_type'])
        s['emoji'] = stype.get('emoji', '🦞')
        s['description'] = stype.get('description', '')
        s['use_cost'] = stype.get('use_cost', 0)
        result.append(s)
    return result


def use_servant(world_id, servant_id):
    """Use a servant once. Deducts use_cost coins and reduces durability by 1.
    Returns servant dict or error."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM servants WHERE id=? AND world_id=?",
        (servant_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Servant not found'}
    s = dict(row)
    conn.close()

    if s['durability'] <= 0:
        return {'ok': False, 'error': 'Servant is broken (durability 0). Repair or delete it.'}

    stype = SERVANT_TYPES.get(s['servant_type'], {})
    use_cost = stype.get('use_cost', 50)

    # Deduct use cost
    spend_result = spend_coins(world_id, use_cost, f'use_servant_{s["servant_type"]}')
    if not spend_result['ok']:
        return {'ok': False, 'error': f'Not enough coins. Need {use_cost}.'}

    # Reduce durability
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE servants SET durability=durability-1, last_used=?, total_uses=total_uses+1 WHERE id=?",
        (now, servant_id)
    )
    conn.commit()
    # Re-read
    row = conn.execute("SELECT * FROM servants WHERE id=?", (servant_id,)).fetchone()
    conn.close()
    result = dict(row)
    result['name'] = stype.get('name', '')
    result['emoji'] = stype.get('emoji', '🦞')
    return {'ok': True, 'servant': result}


def repair_servant(world_id, servant_id):
    """Repair a servant's durability to max. Costs half of craft_cost resources."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM servants WHERE id=? AND world_id=?",
        (servant_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Servant not found'}
    s = dict(row)
    conn.close()

    if s['durability'] >= s['max_durability']:
        return {'ok': False, 'error': 'Servant is already at full durability'}

    stype = SERVANT_TYPES.get(s['servant_type'], {})
    craft_cost = stype.get('craft_cost', {})

    # Half cost (round up)
    repair_cost = {}
    for res, amt in craft_cost.items():
        repair_cost[res] = max(1, (amt + 1) // 2)

    # Check and deduct resources
    ok, missing = check_inventory(world_id, repair_cost)
    if not ok:
        return {'ok': False, 'error': 'Not enough resources for repair', 'missing': missing, 'repair_cost': repair_cost}

    if not deduct_inventory(world_id, repair_cost):
        return {'ok': False, 'error': 'Failed to deduct repair resources'}

    # Restore durability
    conn = get_conn()
    conn.execute(
        "UPDATE servants SET durability=max_durability WHERE id=?",
        (servant_id,)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM servants WHERE id=?", (servant_id,)).fetchone()
    conn.close()
    result = dict(row)
    result['name'] = stype.get('name', '')
    result['emoji'] = stype.get('emoji', '🦞')

    return {'ok': True, 'servant': result, 'repair_cost': repair_cost}


def delete_servant(world_id, servant_id):
    """Delete a servant (only if durability is 0)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM servants WHERE id=? AND world_id=?",
        (servant_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Servant not found'}
    s = dict(row)
    if s['durability'] > 0:
        conn.close()
        return {'ok': False, 'error': 'Can only delete broken servants (durability 0). Repair it instead!'}
    conn.execute("DELETE FROM servants WHERE id=?", (servant_id,))
    conn.commit()
    conn.close()
    return {'ok': True, 'deleted': servant_id, 'type': s['servant_type']}


init_economy()

# ── Guestbook System ──────────────────────────────────────────

def init_guestbook():
    """Create guestbook table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS guestbook (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        author_name TEXT NOT NULL DEFAULT 'Visitor',
        author_avatar TEXT DEFAULT '🦞',
        message TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        ip_hash TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_gb_world ON guestbook(world_id, created_at DESC);
    """)
    conn.commit()
    conn.close()


def add_guestbook_entry(world_id, author_name, message, author_avatar='🦞', ip_hash=None):
    """INSERT a guestbook entry and return the new entry as a dict."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO guestbook (world_id, author_name, author_avatar, message, created_at, ip_hash) VALUES (?,?,?,?,?,?)",
        (world_id, author_name, author_avatar, message, now, ip_hash)
    )
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        'id': entry_id,
        'world_id': world_id,
        'author_name': author_name,
        'author_avatar': author_avatar,
        'message': message,
        'created_at': now,
    }


def get_guestbook(world_id, limit=50, offset=0):
    """SELECT guestbook entries ordered by created_at DESC."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, author_name, author_avatar, message, created_at FROM guestbook WHERE world_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (world_id, limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_guestbook_count(world_id):
    """COUNT entries for a world."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM guestbook WHERE world_id=?",
        (world_id,)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


init_guestbook()

# ── Island Favorites System ────────────────────────────────────

def init_favorites():
    """Create island_favorites table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        island_id TEXT NOT NULL,
        created_at TEXT,
        UNIQUE(user_id, island_id)
    );
    CREATE INDEX IF NOT EXISTS idx_fav_user ON island_favorites(user_id);
    CREATE INDEX IF NOT EXISTS idx_fav_island ON island_favorites(island_id);
    """)
    conn.commit()
    conn.close()


def toggle_favorite(user_id, island_id):
    """Toggle favorite: INSERT if not exists, DELETE if exists. Returns {'favorited': bool, 'count': int}."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM island_favorites WHERE user_id=? AND island_id=?",
        (user_id, island_id)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM island_favorites WHERE user_id=? AND island_id=?", (user_id, island_id))
        conn.commit()
        count = conn.execute("SELECT COUNT(*) as cnt FROM island_favorites WHERE island_id=?", (island_id,)).fetchone()['cnt']
        conn.close()
        return {'favorited': False, 'count': count}
    else:
        conn.execute(
            "INSERT INTO island_favorites (user_id, island_id, created_at) VALUES (?,?,?)",
            (user_id, island_id, now)
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) as cnt FROM island_favorites WHERE island_id=?", (island_id,)).fetchone()['cnt']
        conn.close()
        return {'favorited': True, 'count': count}


def get_favorites_for_user(user_id):
    """Return list of island_ids the user has favorited."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT island_id FROM island_favorites WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return [r['island_id'] for r in rows]


def get_favorite_count(island_id):
    """Return favorite count for a single island."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM island_favorites WHERE island_id=?", (island_id,)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


def get_favorite_counts_bulk(island_ids):
    """Return dict of {island_id: count} for a list of island IDs."""
    if not island_ids:
        return {}
    conn = get_conn()
    placeholders = ','.join('?' for _ in island_ids)
    rows = conn.execute(
        f"SELECT island_id, COUNT(*) as cnt FROM island_favorites WHERE island_id IN ({placeholders}) GROUP BY island_id",
        island_ids
    ).fetchall()
    conn.close()
    result = {r['island_id']: r['cnt'] for r in rows}
    # Fill in zeros for islands with no favorites
    for iid in island_ids:
        if iid not in result:
            result[iid] = 0
    return result


init_favorites()

# ── Favorite Aliases (world_id parameter variants) ─────────────
# These provide the API expected by the task spec, mapping world_id → island_id

def is_favorited(user_id, world_id):
    """Check if a user has favorited a world."""
    conn = get_conn()
    row = conn.execute('SELECT 1 FROM island_favorites WHERE user_id=? AND island_id=?', (user_id, world_id)).fetchone()
    conn.close()
    return row is not None

def get_user_favorites(user_id):
    """Return list of world_ids favorited by user, ordered by most recent."""
    return get_favorites_for_user(user_id)

# ── Island Rating System ──────────────────────────────────────

def init_ratings():
    """Create island_ratings table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        island_id TEXT NOT NULL,
        rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
        created_at TEXT,
        updated_at TEXT,
        UNIQUE(user_id, island_id)
    );
    CREATE INDEX IF NOT EXISTS idx_rating_island ON island_ratings(island_id);
    """)
    conn.commit()
    conn.close()


def rate_island(user_id, island_id, rating):
    """Rate an island 1-5 stars. INSERT OR REPLACE. Returns {'rating': int, 'avg': float, 'count': int}."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO island_ratings (user_id, island_id, rating, created_at, updated_at) "
        "VALUES (?, ?, ?, COALESCE((SELECT created_at FROM island_ratings WHERE user_id=? AND island_id=?), ?), ?)",
        (user_id, island_id, rating, user_id, island_id, now, now)
    )
    conn.commit()
    row = conn.execute(
        "SELECT AVG(rating) as avg_rating, COUNT(*) as cnt FROM island_ratings WHERE island_id=?",
        (island_id,)
    ).fetchone()
    conn.close()
    return {
        'rating': rating,
        'avg': round(row['avg_rating'], 1) if row['avg_rating'] else 0.0,
        'count': row['cnt'] if row else 0
    }


def get_island_rating(island_id):
    """Return {'avg': float, 'count': int} for an island."""
    conn = get_conn()
    row = conn.execute(
        "SELECT AVG(rating) as avg_rating, COUNT(*) as cnt FROM island_ratings WHERE island_id=?",
        (island_id,)
    ).fetchone()
    conn.close()
    return {
        'avg': round(row['avg_rating'], 1) if row['avg_rating'] else 0.0,
        'count': row['cnt'] if row else 0
    }


def get_user_rating(user_id, island_id):
    """Return the user's rating (int) for an island, or None if not rated."""
    conn = get_conn()
    row = conn.execute(
        "SELECT rating FROM island_ratings WHERE user_id=? AND island_id=?",
        (user_id, island_id)
    ).fetchone()
    conn.close()
    return row['rating'] if row else None


def get_rating_counts_bulk(island_ids):
    """Return {island_id: {'avg': float, 'count': int}} for a list of island IDs."""
    if not island_ids:
        return {}
    conn = get_conn()
    placeholders = ','.join('?' for _ in island_ids)
    rows = conn.execute(
        f"SELECT island_id, AVG(rating) as avg_rating, COUNT(*) as cnt "
        f"FROM island_ratings WHERE island_id IN ({placeholders}) GROUP BY island_id",
        island_ids
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        result[r['island_id']] = {
            'avg': round(r['avg_rating'], 1) if r['avg_rating'] else 0.0,
            'count': r['cnt']
        }
    return result


init_ratings()

# ── Login Streak System ────────────────────────────────────────

def init_login_streaks():
    """Create login_streaks table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS login_streaks (
        world_id TEXT PRIMARY KEY,
        current_streak INTEGER DEFAULT 0,
        last_login_date TEXT,
        longest_streak INTEGER DEFAULT 0,
        total_logins INTEGER DEFAULT 0
    );
    """)
    conn.commit()
    conn.close()


# Streak reward tiers (coins per day)
STREAK_REWARDS = {
    1: 10,
    2: 15,
    3: 20,
    4: 25,
    5: 35,
    6: 45,
}
STREAK_REWARD_MAX = 60  # Day 7+


def _streak_coins(streak_day):
    """Return coins for a given streak day."""
    if streak_day >= 7:
        return STREAK_REWARD_MAX
    return STREAK_REWARDS.get(streak_day, 10)


def get_login_streak(world_id):
    """Return current streak data for a world."""
    conn = get_conn()
    row = conn.execute('SELECT * FROM login_streaks WHERE world_id=?', (world_id,)).fetchone()
    conn.close()
    if not row:
        return {
            'world_id': world_id,
            'current_streak': 0,
            'last_login_date': None,
            'longest_streak': 0,
            'total_logins': 0,
        }
    return dict(row)


def claim_daily_login(world_id):
    """Claim daily login. Returns streak info + coins earned.
    
    Logic:
    - If already claimed today -> {ok: False, already_claimed: True}
    - If last login was yesterday -> increment streak
    - If last login was older or never -> reset streak to 1
    Returns streak info + coins earned.
    """
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    conn = get_conn()
    row = conn.execute('SELECT * FROM login_streaks WHERE world_id=?', (world_id,)).fetchone()
    
    if row:
        last_date = row['last_login_date']
        current_streak = row['current_streak']
        longest_streak = row['longest_streak']
        total_logins = row['total_logins']
        
        # Already claimed today
        if last_date == today:
            conn.close()
            return {
                'ok': False,
                'already_claimed': True,
                'current_streak': current_streak,
                'longest_streak': longest_streak,
                'total_logins': total_logins,
                'coins_earned': 0,
                'next_reward': _streak_coins(current_streak + 1),
            }
        
        # Check if yesterday
        from datetime import timedelta
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
        if last_date == yesterday:
            # Continue streak
            new_streak = current_streak + 1
        else:
            # Reset streak (missed a day or first time)
            new_streak = 1
    else:
        # First login ever
        new_streak = 1
        longest_streak = 0
        total_logins = 0
    
    coins = _streak_coins(new_streak)
    new_longest = max(longest_streak if row else 0, new_streak)
    new_total = (total_logins if row else 0) + 1
    
    conn.execute("""
        INSERT INTO login_streaks (world_id, current_streak, last_login_date, longest_streak, total_logins)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(world_id) DO UPDATE SET
            current_streak=?, last_login_date=?, longest_streak=?, total_logins=?
    """, (world_id, new_streak, today, new_longest, new_total,
          new_streak, today, new_longest, new_total))
    conn.commit()
    conn.close()
    
    # Award coins via earn_coins
    earn_coins(world_id, coins, f'daily_login_streak_day_{new_streak}')
    
    return {
        'ok': True,
        'already_claimed': False,
        'current_streak': new_streak,
        'longest_streak': new_longest,
        'total_logins': new_total,
        'coins_earned': coins,
        'streak_day': new_streak,
        'next_reward': _streak_coins(new_streak + 1),
        'is_weekly_bonus': new_streak >= 7,
    }


init_login_streaks()

# ── User Settings / API Key Management ─────────────────────────

import base64 as _b64

def get_user_api_key(user_id):
    """Return the user's API key (decoded) or None."""
    conn = get_conn()
    row = conn.execute("SELECT api_key FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row or not row['api_key']:
        return None
    try:
        return _b64.b64decode(row['api_key']).decode('utf-8')
    except Exception:
        return row['api_key']


def set_user_api_key(user_id, api_key, provider='genspark'):
    """Upsert user API key (stored base64-encoded)."""
    encoded = _b64.b64encode(api_key.encode('utf-8')).decode('utf-8') if api_key else ''
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT INTO user_settings (user_id, api_key, api_provider, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET api_key=?, api_provider=?, updated_at=?
    """, (user_id, encoded, provider, now, encoded, provider, now))
    conn.commit()
    conn.close()


def delete_user_api_key(user_id):
    """Remove the user's API key."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("""
        INSERT INTO user_settings (user_id, api_key, updated_at)
        VALUES (?, '', ?)
        ON CONFLICT(user_id) DO UPDATE SET api_key='', updated_at=?
    """, (user_id, now, now))
    conn.commit()
    conn.close()


def get_user_api_provider(user_id):
    """Return the user's API provider or 'genspark'."""
    conn = get_conn()
    row = conn.execute("SELECT api_provider FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row['api_provider'] if row and row['api_provider'] else 'genspark'


def increment_ai_usage(user_id):
    """Increment daily AI call count. Reset if new day (UTC)."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    row = conn.execute("SELECT last_reset_date, daily_ai_calls FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
    if row:
        if row['last_reset_date'] != today:
            # New day — reset counter
            conn.execute("""
                UPDATE user_settings SET daily_ai_calls=1, last_reset_date=?, updated_at=? WHERE user_id=?
            """, (today, now, user_id))
        else:
            conn.execute("""
                UPDATE user_settings SET daily_ai_calls=daily_ai_calls+1, updated_at=? WHERE user_id=?
            """, (now, user_id))
    else:
        # First time — create row
        conn.execute("""
            INSERT INTO user_settings (user_id, daily_ai_calls, last_reset_date, updated_at)
            VALUES (?, 1, ?, ?)
        """, (user_id, today, now))
    conn.commit()
    conn.close()


def get_ai_usage(user_id):
    """Return {calls_today, limit} for the user."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn = get_conn()
    row = conn.execute("SELECT daily_ai_calls, last_reset_date FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return {'calls_today': 0, 'limit': 50}
    calls = row['daily_ai_calls'] if row['last_reset_date'] == today else 0
    return {'calls_today': calls, 'limit': 50}


# --- Achievements System ---

ACHIEVEMENTS_V2 = {
    'first_gather': {'name': 'First Harvest', 'emoji': '🌾', 'desc': 'Gather your first resource', 'coins': 15},
    'gather_50': {'name': 'Master Gatherer', 'emoji': '⛏️', 'desc': 'Gather 50 resources', 'coins': 50},
    'first_craft': {'name': 'Apprentice Crafter', 'emoji': '🔨', 'desc': 'Craft your first item', 'coins': 15},
    'craft_20': {'name': 'Master Crafter', 'emoji': '🏗️', 'desc': 'Craft 20 items', 'coins': 50},
    'first_sale': {'name': 'Merchant', 'emoji': '💰', 'desc': 'Sell an item at market', 'coins': 15},
    'first_buy': {'name': 'Shopper', 'emoji': '🛒', 'desc': 'Buy an item from market', 'coins': 15},
    'visitor_10': {'name': 'Popular Island', 'emoji': '🌟', 'desc': 'Get 10 visitors', 'coins': 30},
    'visitor_100': {'name': 'Tourist Hotspot', 'emoji': '🏖️', 'desc': 'Get 100 visitors', 'coins': 100},
    'streak_7': {'name': 'Dedicated', 'emoji': '🔥', 'desc': '7-day login streak', 'coins': 50},
    'streak_30': {'name': 'Loyal Islander', 'emoji': '👑', 'desc': '30-day login streak', 'coins': 200},
    'build_10': {'name': 'Builder', 'emoji': '🏠', 'desc': 'Place 10 objects on your island', 'coins': 30},
    'build_50': {'name': 'Architect', 'emoji': '🏰', 'desc': 'Place 50 objects on your island', 'coins': 100},
    'guestbook_first': {'name': 'Social Butterfly', 'emoji': '📝', 'desc': 'Leave your first guestbook entry', 'coins': 10},
    'defense_setup': {'name': 'Fortified', 'emoji': '🛡️', 'desc': 'Set up island defenses', 'coins': 20},
    'level_5': {'name': 'Growing Island', 'emoji': '📈', 'desc': 'Reach island level 5', 'coins': 30},
    'level_10': {'name': 'Thriving Island', 'emoji': '🎯', 'desc': 'Reach island level 10', 'coins': 75},
}

def _init_achievements_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            world_id TEXT NOT NULL,
            achievement_id TEXT NOT NULL,
            unlocked_at TEXT NOT NULL,
            coins_awarded INTEGER DEFAULT 0,
            UNIQUE(world_id, achievement_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievement_progress (
            world_id TEXT NOT NULL,
            stat_key TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY(world_id, stat_key)
        )
    """)
    conn.commit()
    conn.close()

_init_achievements_table()


def increment_achievement_stat(world_id, stat_key, amount=1):
    """Increment a stat counter and return the new count."""
    conn = get_conn()
    conn.execute("""
        INSERT INTO achievement_progress (world_id, stat_key, count) VALUES (?, ?, ?)
        ON CONFLICT(world_id, stat_key) DO UPDATE SET count = count + ?
    """, (world_id, stat_key, amount, amount))
    conn.commit()
    row = conn.execute("SELECT count FROM achievement_progress WHERE world_id=? AND stat_key=?", (world_id, stat_key)).fetchone()
    conn.close()
    return row['count'] if row else amount


def get_achievement_stat(world_id, stat_key):
    conn = get_conn()
    row = conn.execute("SELECT count FROM achievement_progress WHERE world_id=? AND stat_key=?", (world_id, stat_key)).fetchone()
    conn.close()
    return row['count'] if row else 0


def unlock_achievement(world_id, achievement_id):
    """Try to unlock. Returns {'unlocked': True, 'achievement': {...}} if newly unlocked, or {'unlocked': False} if already had."""
    if achievement_id not in ACHIEVEMENTS_V2:
        return {'unlocked': False, 'error': 'unknown achievement'}
    ach = ACHIEVEMENTS_V2[achievement_id]
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    try:
        conn.execute("INSERT INTO achievements_v2 (world_id, achievement_id, unlocked_at, coins_awarded) VALUES (?, ?, ?, ?)",
                     (world_id, achievement_id, now, ach['coins']))
        conn.commit()
        conn.close()
        return {'unlocked': True, 'achievement': {**ach, 'id': achievement_id}, 'coins': ach['coins']}
    except Exception:
        conn.close()
        return {'unlocked': False}


def get_achievements_v2(world_id):
    """Return list of unlocked achievements for a world."""
    conn = get_conn()
    rows = conn.execute("SELECT achievement_id, unlocked_at, coins_awarded FROM achievements_v2 WHERE world_id=? ORDER BY unlocked_at DESC", (world_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        aid = r['achievement_id']
        ach = ACHIEVEMENTS_V2.get(aid, {})
        result.append({
            'id': aid,
            'name': ach.get('name', aid),
            'emoji': ach.get('emoji', '🏆'),
            'desc': ach.get('desc', ''),
            'unlocked_at': r['unlocked_at'],
            'coins_awarded': r['coins_awarded']
        })
    return result


def check_and_unlock_achievements(world_id):
    """Check all achievement conditions and unlock any that are met. Returns list of newly unlocked."""
    newly = []
    # Check stat-based achievements
    stat_thresholds = {
        'gather': [('first_gather', 1), ('gather_50', 50)],
        'craft': [('first_craft', 1), ('craft_20', 20)],
        'sell': [('first_sale', 1)],
        'buy': [('first_buy', 1)],
        'build': [('build_10', 10), ('build_50', 50)],
        'guestbook': [('guestbook_first', 1)],
        'defense': [('defense_setup', 1)],
    }
    for stat_key, thresholds in stat_thresholds.items():
        count = get_achievement_stat(world_id, stat_key)
        for ach_id, threshold in thresholds:
            if count >= threshold:
                result = unlock_achievement(world_id, ach_id)
                if result.get('unlocked'):
                    newly.append(result)
    return newly


# --- Daily Quests System ---
import random as _quest_rnd

QUEST_TYPES = {
    'visit_islands':   {'desc': 'Visit {n} islands',           'n_range': (2, 4),   'reward_range': (15, 25)},
    'harvest_crops':   {'desc': 'Harvest {n} crops',           'n_range': (2, 5),   'reward_range': (15, 30)},
    'craft_item':      {'desc': 'Craft {n} items',             'n_range': (1, 2),   'reward_range': (20, 30)},
    'sell_market':     {'desc': 'Sell {n} items on market',    'n_range': (1, 3),   'reward_range': (15, 25)},
    'leave_guestbook': {'desc': 'Leave {n} guestbook messages','n_range': (1, 2),   'reward_range': (10, 20)},
    'earn_xp':         {'desc': 'Earn {n} XP',                 'n_range': (50, 200),'reward_range': (20, 35)},
    'place_object':    {'desc': 'Place {n} objects on island', 'n_range': (2, 4),   'reward_range': (15, 25)},
}

def init_daily_quests():
    conn = get_conn()
    conn.execute('''CREATE TABLE IF NOT EXISTS daily_quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        quest_date TEXT NOT NULL,
        quest_type TEXT NOT NULL,
        target_count INTEGER NOT NULL,
        current_count INTEGER DEFAULT 0,
        reward_coins INTEGER NOT NULL,
        claimed INTEGER DEFAULT 0,
        UNIQUE(world_id, quest_date, quest_type)
    )''')
    conn.commit()
    conn.close()

init_daily_quests()


def get_daily_quests(world_id):
    """Get today's quests for a player. Generate if not exist."""
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, quest_type, target_count, current_count, reward_coins, claimed FROM daily_quests WHERE world_id=? AND quest_date=?",
        (world_id, today_str)
    ).fetchall()

    if rows:
        conn.close()
        return [dict(r) for r in rows]

    # Generate 3 random quests deterministically
    _quest_rnd.seed(f"{world_id}_{today_str}")
    chosen_types = _quest_rnd.sample(list(QUEST_TYPES.keys()), 3)
    quests = []
    for qt in chosen_types:
        info = QUEST_TYPES[qt]
        n = _quest_rnd.randint(info['n_range'][0], info['n_range'][1])
        reward = _quest_rnd.randint(info['reward_range'][0], info['reward_range'][1])
        conn.execute(
            "INSERT OR IGNORE INTO daily_quests (world_id, quest_date, quest_type, target_count, current_count, reward_coins, claimed) VALUES (?,?,?,?,0,?,0)",
            (world_id, today_str, qt, n, reward)
        )
    conn.commit()
    rows = conn.execute(
        "SELECT id, quest_type, target_count, current_count, reward_coins, claimed FROM daily_quests WHERE world_id=? AND quest_date=?",
        (world_id, today_str)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def advance_quest(world_id, quest_type, amount=1):
    """Increment progress for today's quest of the given type."""
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn = get_conn()
    conn.execute(
        "UPDATE daily_quests SET current_count = MIN(current_count + ?, target_count) WHERE world_id=? AND quest_date=? AND quest_type=? AND claimed=0",
        (amount, world_id, today_str, quest_type)
    )
    conn.commit()
    conn.close()


def claim_quest_reward(world_id, quest_id):
    """Claim a completed quest reward. Returns result dict."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id, quest_type, target_count, current_count, reward_coins, claimed FROM daily_quests WHERE id=? AND world_id=?",
        (quest_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Quest not found'}
    if row['claimed']:
        conn.close()
        return {'ok': False, 'error': 'Already claimed'}
    if row['current_count'] < row['target_count']:
        conn.close()
        return {'ok': False, 'error': 'Quest not complete'}
    conn.execute("UPDATE daily_quests SET claimed=1 WHERE id=?", (quest_id,))
    conn.commit()
    conn.close()
    earn_coins(world_id, row['reward_coins'], f"daily_quest_{row['quest_type']}")
    return {'ok': True, 'reward': row['reward_coins']}

# ── Notification System ────────────────────────────────────────

def init_notifications():
    """Create notifications table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        type TEXT NOT NULL,
        message TEXT NOT NULL,
        island_id TEXT,
        from_user TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_notif_user_read_time
        ON notifications(user_id, is_read, created_at DESC);
    """)
    conn.commit()
    conn.close()


def create_notification(user_id, ntype, message, island_id=None, from_user=None):
    """Insert a notification for a user."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO notifications (user_id, type, message, island_id, from_user, is_read, created_at) VALUES (?,?,?,?,?,0,?)",
        (user_id, ntype, message, island_id, from_user, now)
    )
    conn.commit()
    conn.close()


def get_notifications(user_id, limit=20, offset=0):
    """Get user's notifications, ordered by created_at DESC."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, user_id, type, message, island_id, from_user, is_read, created_at "
        "FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unread_count(user_id):
    """Count of unread notifications for a user."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM notifications WHERE user_id=? AND is_read=0",
        (user_id,)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


def mark_notifications_read(user_id, notification_ids=None):
    """Mark notifications as read. If notification_ids is None, mark all as read."""
    conn = get_conn()
    if notification_ids is None:
        conn.execute(
            "UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0",
            (user_id,)
        )
    else:
        if not notification_ids:
            conn.close()
            return
        placeholders = ','.join('?' for _ in notification_ids)
        conn.execute(
            f"UPDATE notifications SET is_read=1 WHERE user_id=? AND id IN ({placeholders})",
            [user_id] + list(notification_ids)
        )
    conn.commit()
    conn.close()


init_notifications()


# ── Island Random Events ──────────────────────────────────────
import random as _evt_rnd
from datetime import timedelta as _evt_td

ISLAND_EVENTS = [
    {'type': 'treasure', 'emoji': '🏴‍☠️', 'title': 'Treasure Washed Ashore!', 'desc': 'A mysterious chest appeared on your beach!', 'coins': (15, 40)},
    {'type': 'mermaid', 'emoji': '🧜‍♀️', 'title': 'Mermaid Sighting!', 'desc': 'A mermaid left a gift of pearls on your shore!', 'coins': (10, 25)},
    {'type': 'rainbow', 'emoji': '🌈', 'title': 'Rainbow Blessing!', 'desc': 'A rainbow arched over your island — good fortune!', 'coins': (5, 15)},
    {'type': 'whale', 'emoji': '🐋', 'title': 'Whale Visit!', 'desc': 'A friendly whale surfaced near your island!', 'coins': (8, 20)},
    {'type': 'shooting_star', 'emoji': '🌠', 'title': 'Shooting Star!', 'desc': 'A shooting star fell near your island — make a wish!', 'coins': (10, 30)},
    {'type': 'bottle', 'emoji': '🍾', 'title': 'Message in a Bottle!', 'desc': 'A bottle washed up with a mysterious note and some coins!', 'coins': (5, 20)},
    {'type': 'dolphin', 'emoji': '🐬', 'title': 'Dolphin Pod!', 'desc': 'Dolphins are playing in your island waters!', 'coins': (5, 15)},
    {'type': 'golden_crab', 'emoji': '🦀', 'title': 'Golden Crab!', 'desc': 'A rare golden crab was spotted on your beach!', 'coins': (20, 50)},
]


def init_island_events():
    """Create island_events table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        emoji TEXT NOT NULL,
        coin_reward INTEGER DEFAULT 0,
        collected INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_events_world ON island_events(world_id, collected, expires_at);
    """)
    conn.commit()
    conn.close()


def generate_island_event(world_id):
    """Create a random island event. Returns the event dict or None."""
    evt = _evt_rnd.choice(ISLAND_EVENTS)
    coins = _evt_rnd.randint(evt['coins'][0], evt['coins'][1])
    now = datetime.now(timezone.utc)
    expires = now + _evt_td(hours=24)
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO island_events (world_id, event_type, title, description, emoji, coin_reward, collected, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)",
        (world_id, evt['type'], evt['title'], evt['desc'], evt['emoji'], coins, now.isoformat(), expires.isoformat())
    )
    event_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {
        'id': event_id,
        'world_id': world_id,
        'event_type': evt['type'],
        'title': evt['title'],
        'description': evt['desc'],
        'emoji': evt['emoji'],
        'coin_reward': coins,
        'created_at': now.isoformat(),
        'expires_at': expires.isoformat(),
    }


def get_active_event(world_id):
    """Return the current uncollected, non-expired event for a world, or None."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT id, world_id, event_type, title, description, emoji, coin_reward, created_at, expires_at "
        "FROM island_events WHERE world_id=? AND collected=0 AND expires_at>? "
        "ORDER BY created_at DESC LIMIT 1",
        (world_id, now)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def collect_event(event_id, world_id):
    """Mark an event as collected and award coins. Returns coin reward or None."""
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute(
        "SELECT id, coin_reward, collected, world_id, expires_at FROM island_events WHERE id=? AND world_id=?",
        (event_id, world_id)
    ).fetchone()
    if not row or row['collected'] == 1:
        conn.close()
        return None
    # Check not expired
    if row['expires_at'] <= now:
        conn.close()
        return None
    coins = row['coin_reward']
    conn.execute("UPDATE island_events SET collected=1 WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    # Award coins via existing wallet system
    earn_coins(world_id, coins, reason='island_event')
    return coins


def maybe_spawn_event(world_id):
    """Maybe spawn a random event on island visit. ~10% chance if no active event and last event >2h ago."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    conn = get_conn()
    # Check for active (uncollected, non-expired) event
    active = conn.execute(
        "SELECT id FROM island_events WHERE world_id=? AND collected=0 AND expires_at>? LIMIT 1",
        (world_id, now_iso)
    ).fetchone()
    if active:
        conn.close()
        return None  # Already has an active event
    # Check last event time (any event, collected or not)
    last = conn.execute(
        "SELECT created_at FROM island_events WHERE world_id=? ORDER BY created_at DESC LIMIT 1",
        (world_id,)
    ).fetchone()
    conn.close()
    if last:
        try:
            last_time = datetime.fromisoformat(last['created_at'])
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            if (now - last_time).total_seconds() < 7200:  # 2 hours
                return None
        except (ValueError, TypeError):
            pass
    # 10% chance
    if _evt_rnd.random() > 0.10:
        return None
    return generate_island_event(world_id)


init_island_events()

# ── Island Reactions System ────────────────────────────────────

def init_island_reactions():
    """Create island_reactions table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        emoji TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(world_id, user_id, emoji)
    );
    CREATE INDEX IF NOT EXISTS idx_reactions_world ON island_reactions(world_id);
    """)
    conn.commit()
    conn.close()


ALLOWED_REACTION_EMOJIS = ["❤️", "🔥", "⭐", "😍", "🎉", "👏"]


def add_island_reaction(world_id, user_id, emoji):
    """INSERT OR IGNORE a reaction. Returns True if newly inserted."""
    if emoji not in ALLOWED_REACTION_EMOJIS:
        return False
    conn = get_conn()
    cursor = conn.execute(
        "INSERT OR IGNORE INTO island_reactions (world_id, user_id, emoji) VALUES (?, ?, ?)",
        (world_id, user_id, emoji)
    )
    inserted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return inserted


def remove_island_reaction(world_id, user_id, emoji):
    """DELETE a reaction. Returns True if a row was deleted."""
    conn = get_conn()
    cursor = conn.execute(
        "DELETE FROM island_reactions WHERE world_id=? AND user_id=? AND emoji=?",
        (world_id, user_id, emoji)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_island_reactions(world_id, user_id=None):
    """Get reaction counts for an island.
    Returns list of {emoji, count, reacted} where reacted=True if user_id reacted with that emoji.
    Always returns all 6 emojis, even if count is 0."""
    conn = get_conn()
    # Get counts per emoji
    rows = conn.execute(
        "SELECT emoji, COUNT(*) as cnt FROM island_reactions WHERE world_id=? GROUP BY emoji",
        (world_id,)
    ).fetchall()
    counts = {r['emoji']: r['cnt'] for r in rows}

    # Get user's own reactions
    user_reacted = set()
    if user_id:
        user_rows = conn.execute(
            "SELECT emoji FROM island_reactions WHERE world_id=? AND user_id=?",
            (world_id, user_id)
        ).fetchall()
        user_reacted = {r['emoji'] for r in user_rows}

    conn.close()

    result = []
    for emoji in ALLOWED_REACTION_EMOJIS:
        result.append({
            'emoji': emoji,
            'count': counts.get(emoji, 0),
            'reacted': emoji in user_reacted,
        })
    return result


init_island_reactions()

# ── Daily Challenges System ────────────────────────────────────

DAILY_CHALLENGE_TYPES = {
    'harvest_crops':    {'desc': 'Harvest {n} crops',           'emoji': '🌾', 'target': 5,  'reward': 30},
    'place_objects':    {'desc': 'Place {n} objects',           'emoji': '🏗️', 'target': 3,  'reward': 25},
    'visit_islands':    {'desc': 'Visit {n} other islands',    'emoji': '🧭', 'target': 2,  'reward': 40},
    'earn_coins':       {'desc': 'Earn {n} coins',             'emoji': '💎', 'target': 100,'reward': 50},
    'catch_fish':       {'desc': 'Catch {n} fish',             'emoji': '🐟', 'target': 3,  'reward': 35},
    'leave_guestbook':  {'desc': 'Leave a guestbook message',  'emoji': '📝', 'target': 1,  'reward': 20},
    'upgrade_building': {'desc': 'Upgrade a building',         'emoji': '🔨', 'target': 1,  'reward': 45},
    'collect_event':    {'desc': 'Collect an island event',    'emoji': '🏴‍☠️', 'target': 1,  'reward': 30},
}


def init_daily_challenges():
    """Create daily_challenges table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS daily_challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        challenge_type TEXT NOT NULL,
        target_count INTEGER DEFAULT 1,
        current_count INTEGER DEFAULT 0,
        reward_coins INTEGER DEFAULT 50,
        completed INTEGER DEFAULT 0,
        date_key TEXT NOT NULL,
        created_at TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_challenge_unique
        ON daily_challenges(world_id, challenge_type, date_key);
    """)
    conn.commit()
    conn.close()


def get_daily_challenges(world_id):
    """Return today's 3 challenges for the player. Generate if not yet created."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, challenge_type, target_count, current_count, reward_coins, completed, date_key "
        "FROM daily_challenges WHERE world_id=? AND date_key=?",
        (world_id, today)
    ).fetchall()
    if rows:
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            info = DAILY_CHALLENGE_TYPES.get(d['challenge_type'], {})
            d['emoji'] = info.get('emoji', '📋')
            d['description'] = info.get('desc', d['challenge_type']).replace('{n}', str(d['target_count']))
            result.append(d)
        return result

    # Generate 3 challenges deterministically based on date hash
    seed = hashlib.md5(f"challenges:{today}".encode()).hexdigest()
    h = int(seed[:8], 16)
    all_types = list(DAILY_CHALLENGE_TYPES.keys())
    # Pick 3 unique types using hash-based index selection
    picked = []
    used = set()
    for i in range(3):
        idx = (h >> (i * 8)) % len(all_types)
        # If collision, shift until we find unused
        while all_types[idx % len(all_types)] in used:
            idx += 1
        ctype = all_types[idx % len(all_types)]
        used.add(ctype)
        picked.append(ctype)

    now = datetime.now(timezone.utc).isoformat()
    for ctype in picked:
        info = DAILY_CHALLENGE_TYPES[ctype]
        conn.execute(
            "INSERT OR IGNORE INTO daily_challenges "
            "(world_id, challenge_type, target_count, current_count, reward_coins, completed, date_key, created_at) "
            "VALUES (?,?,?,0,?,0,?,?)",
            (world_id, ctype, info['target'], info['reward'], today, now)
        )
    conn.commit()

    # Re-fetch
    rows = conn.execute(
        "SELECT id, challenge_type, target_count, current_count, reward_coins, completed, date_key "
        "FROM daily_challenges WHERE world_id=? AND date_key=?",
        (world_id, today)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        info = DAILY_CHALLENGE_TYPES.get(d['challenge_type'], {})
        d['emoji'] = info.get('emoji', '📋')
        d['description'] = info.get('desc', d['challenge_type']).replace('{n}', str(d['target_count']))
        result.append(d)
    return result


def update_challenge_progress(world_id, challenge_type, increment=1):
    """Increment progress on today's challenge. Auto-complete and award coins if target reached."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn = get_conn()
    row = conn.execute(
        "SELECT id, target_count, current_count, reward_coins, completed "
        "FROM daily_challenges WHERE world_id=? AND challenge_type=? AND date_key=? AND completed=0",
        (world_id, challenge_type, today)
    ).fetchone()
    if not row:
        conn.close()
        return None
    new_count = min(row['current_count'] + increment, row['target_count'])
    completed = 1 if new_count >= row['target_count'] else 0
    conn.execute(
        "UPDATE daily_challenges SET current_count=?, completed=? WHERE id=?",
        (new_count, completed, row['id'])
    )
    conn.commit()
    conn.close()
    # Auto-award coins on completion
    if completed and not row['completed']:
        earn_coins(world_id, row['reward_coins'], f'daily_challenge_{challenge_type}')
    return {'id': row['id'], 'challenge_type': challenge_type,
            'current_count': new_count, 'completed': bool(completed),
            'coins_awarded': row['reward_coins'] if completed else 0}


init_daily_challenges()


# ── Collection Book ────────────────────────────────────────────

def init_collection_book():
    conn = get_conn()
    conn.execute('''CREATE TABLE IF NOT EXISTS collection_book (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        object_id TEXT NOT NULL,
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(world_id, object_id)
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_collection_world ON collection_book(world_id)')
    conn.commit()

def discover_object(world_id, object_id):
    """Record that a world discovered/placed this object type. Returns True if newly discovered."""
    conn = get_conn()
    try:
        conn.execute("INSERT OR IGNORE INTO collection_book (world_id, object_id) VALUES (?, ?)", (world_id, object_id))
        conn.commit()
        return conn.total_changes > 0
    except:
        return False

def get_collection(world_id):
    """Get all discovered object IDs for a world."""
    conn = get_conn()
    rows = conn.execute("SELECT object_id, discovered_at FROM collection_book WHERE world_id=? ORDER BY discovered_at", (world_id,)).fetchall()
    return [{'object_id': r['object_id'], 'discovered_at': r['discovered_at']} for r in rows]

def get_collection_count(world_id):
    conn = get_conn()
    r = conn.execute("SELECT COUNT(*) as cnt FROM collection_book WHERE world_id=?", (world_id,)).fetchone()
    return r['cnt'] if r else 0

init_collection_book()

# ── Fishing System ─────────────────────────────────────────────

FISH_POOL = [
    # Common (60%)
    {'type': 'Sardine',        'emoji': '🐟', 'rarity': 'common',    'coins': 5},
    {'type': 'Clownfish',      'emoji': '🐠', 'rarity': 'common',    'coins': 8},
    {'type': 'Shrimp',         'emoji': '🦐', 'rarity': 'common',    'coins': 4},
    {'type': 'Pufferfish',     'emoji': '🐡', 'rarity': 'common',    'coins': 6},
    # Uncommon (25%)
    {'type': 'Crab',           'emoji': '🦀', 'rarity': 'uncommon',  'coins': 15},
    {'type': 'Squid',          'emoji': '🦑', 'rarity': 'uncommon',  'coins': 12},
    {'type': 'Octopus',        'emoji': '🐙', 'rarity': 'uncommon',  'coins': 18},
    # Rare (12%)
    {'type': 'Dolphin',        'emoji': '🐬', 'rarity': 'rare',      'coins': 35},
    {'type': 'Whale',          'emoji': '🐋', 'rarity': 'rare',      'coins': 50},
    {'type': 'Shark',          'emoji': '🦈', 'rarity': 'rare',      'coins': 40},
    # Legendary (3%)
    {'type': 'Golden Lobster',  'emoji': '🦞', 'rarity': 'legendary', 'coins': 100},
    {'type': 'Sea Dragon',      'emoji': '🐉', 'rarity': 'legendary', 'coins': 150},
]

RARITY_WEIGHTS = {'common': 60, 'uncommon': 25, 'rare': 12, 'legendary': 3}

# Snowy weather unique ice fish (added to pool only during snow)
ICE_FISH = [
    {'type': 'Frost Koi',      'emoji': '🐟', 'rarity': 'rare',      'coins': 45, 'ice': True},
    {'type': 'Ice Crystal Crab','emoji': '🦀', 'rarity': 'rare',      'coins': 55, 'ice': True},
    {'type': 'Glacial Jellyfish','emoji': '🪼', 'rarity': 'legendary', 'coins': 120, 'ice': True},
]

def pick_random_fish(weather=None):
    """Pick a random fish based on rarity weights. Weather affects probabilities:
    - rainy: +20% rare fish chance
    - stormy: +50% rare fish chance
    - snowy: chance for unique ice fish
    """
    import random as _frnd

    # Base thresholds: legendary <= 3, rare <= 15, uncommon <= 40, else common
    legendary_thresh = 3
    rare_thresh = 15
    uncommon_thresh = 40

    # Snowy: 25% chance to get ice fish instead of normal pool
    if weather == 'snowy' and _frnd.random() < 0.25:
        return _frnd.choice(ICE_FISH)

    # Adjust rare thresholds based on weather
    if weather == 'rainy':
        # +20% rare chance: shift rare band up
        legendary_thresh = 4   # slight legendary boost
        rare_thresh = 20       # rare goes from 15 → 20
        uncommon_thresh = 45
    elif weather == 'stormy':
        # +50% rare chance: bigger rare band
        legendary_thresh = 5
        rare_thresh = 25       # rare goes from 15 → 25
        uncommon_thresh = 48

    roll = _frnd.randint(1, 100)
    if roll <= legendary_thresh:
        rarity = 'legendary'
    elif roll <= rare_thresh:
        rarity = 'rare'
    elif roll <= uncommon_thresh:
        rarity = 'uncommon'
    else:
        rarity = 'common'
    pool = [f for f in FISH_POOL if f['rarity'] == rarity]
    return _frnd.choice(pool)


def init_fishing():
    """Create fishing_catches table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS fishing_catches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        user_id TEXT,
        user_name TEXT DEFAULT 'Anonymous',
        fish_type TEXT NOT NULL,
        fish_emoji TEXT NOT NULL,
        rarity TEXT NOT NULL,
        coins_earned INTEGER NOT NULL,
        caught_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_fishing_world ON fishing_catches(world_id, caught_at DESC);
    """)
    conn.commit()
    conn.close()


def record_catch(world_id, user_id, user_name, fish_type, fish_emoji, rarity, coins):
    """Insert a fishing catch record."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO fishing_catches (world_id, user_id, user_name, fish_type, fish_emoji, rarity, coins_earned, caught_at) VALUES (?,?,?,?,?,?,?,?)",
        (world_id, user_id, user_name, fish_type, fish_emoji, rarity, coins, now)
    )
    conn.commit()
    conn.close()


def get_fish_collection(world_id):
    """Get distinct fish types caught by this island with first-catch date and count."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT fish_type, fish_emoji, rarity, MIN(caught_at) as first_caught, COUNT(*) as catch_count FROM fishing_catches WHERE world_id=? GROUP BY fish_type",
        (world_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_catches(world_id, limit=20):
    """Get recent fishing catches for a world."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, world_id, user_id, user_name, fish_type, fish_emoji, rarity, coins_earned, caught_at FROM fishing_catches WHERE world_id=? ORDER BY caught_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


init_fishing()

# ── Treasure Hunt System ────────────────────────────────────────

def init_treasure_hunt():
    """Create treasure_finds table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS treasure_finds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        treasure_id TEXT NOT NULL,
        visitor_id TEXT,
        visitor_ip TEXT,
        reward_type TEXT,
        reward_amount INTEGER DEFAULT 0,
        found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(world_id, treasure_id)
    );
    CREATE INDEX IF NOT EXISTS idx_treasure_world ON treasure_finds(world_id);
    """)
    conn.commit()
    conn.close()


def get_treasure_finds(world_id):
    """Return all treasure finds for a world as a dict keyed by treasure_id."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT treasure_id, visitor_id, reward_type, reward_amount, found_at FROM treasure_finds WHERE world_id=?",
        (world_id,)
    ).fetchall()
    conn.close()
    return {r['treasure_id']: dict(r) for r in rows}


def record_treasure_find(world_id, treasure_id, visitor_id, visitor_ip, reward_type, reward_amount):
    """Mark a treasure as found. Returns True on success, False if already found."""
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO treasure_finds (world_id, treasure_id, visitor_id, visitor_ip, reward_type, reward_amount) VALUES (?,?,?,?,?,?)",
            (world_id, treasure_id, visitor_id, visitor_ip, reward_type, reward_amount)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False  # UNIQUE constraint → already found


def get_treasure_collect_count_by_ip(visitor_ip, window_seconds=3600):
    """Count how many treasures this IP has collected in the last window_seconds."""
    import time as _t
    cutoff = _t.time() - window_seconds
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM treasure_finds WHERE visitor_ip=? AND found_at >= datetime(?, 'unixepoch')",
        (visitor_ip, cutoff)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


init_treasure_hunt()

# ── Island Daily Quests (per-island, per-visitor) ─────────────

def init_island_quests():
    """Create tables for the per-island, per-visitor daily quest system."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_daily_quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        quest_date TEXT NOT NULL,
        quest_type TEXT NOT NULL,
        quest_desc TEXT NOT NULL,
        target_count INTEGER DEFAULT 1,
        reward_coins INTEGER DEFAULT 10,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_iq_world_date_type
        ON island_daily_quests(world_id, quest_date, quest_type);

    CREATE TABLE IF NOT EXISTS island_quest_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        quest_date TEXT NOT NULL,
        quest_type TEXT NOT NULL,
        user_ip TEXT NOT NULL,
        progress INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        claimed INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT (datetime('now'))
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_iqp_world_date_type_ip
        ON island_quest_progress(world_id, quest_date, quest_type, user_ip);
    """)
    conn.commit()
    conn.close()


def generate_island_quests(world_id, date_str):
    """Generate 3 daily quests for an island using deterministic seeding."""
    import random as _iq_rnd
    seed = hashlib.md5((world_id + date_str).encode()).hexdigest()
    rng = _iq_rnd.Random(seed)

    quest_pool = {
        'fish':      lambda r: _iq_quest_fish(r),
        'treasure':  lambda r: _iq_quest_treasure(r),
        'visit':     lambda r: _iq_quest_visit(r),
        'guestbook': lambda r: _iq_quest_guestbook(r),
        'gift':      lambda r: _iq_quest_gift(r),
    }
    all_types = list(quest_pool.keys())
    chosen = rng.sample(all_types, 3)

    conn = get_conn()
    for qtype in chosen:
        desc, target, reward = quest_pool[qtype](rng)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO island_daily_quests "
                "(world_id, quest_date, quest_type, quest_desc, target_count, reward_coins) "
                "VALUES (?,?,?,?,?,?)",
                (world_id, date_str, qtype, desc, target, reward)
            )
        except Exception:
            pass
    conn.commit()
    conn.close()


def _iq_quest_fish(rng):
    n = rng.randint(1, 3)
    return (f"Catch {n} fish", n, 15 * n)

def _iq_quest_treasure(rng):
    n = rng.randint(1, 2)
    return (f"Find {n} treasures", n, 20 * n)

def _iq_quest_visit(rng):
    n = rng.randint(2, 5)
    return (f"This island needs {n} visitors", n, 10 * n)

def _iq_quest_guestbook(rng):
    return ("Leave a guestbook message", 1, 25)

def _iq_quest_gift(rng):
    return ("Send a gift to this island", 1, 20)


def get_island_quests(world_id, date_str):
    """Get today's island quests, generating if needed."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT quest_type, quest_desc, target_count, reward_coins "
        "FROM island_daily_quests WHERE world_id=? AND quest_date=?",
        (world_id, date_str)
    ).fetchall()
    conn.close()

    if not rows:
        generate_island_quests(world_id, date_str)
        conn = get_conn()
        rows = conn.execute(
            "SELECT quest_type, quest_desc, target_count, reward_coins "
            "FROM island_daily_quests WHERE world_id=? AND quest_date=?",
            (world_id, date_str)
        ).fetchall()
        conn.close()

    return [dict(r) for r in rows]


def get_island_quest_progress(world_id, date_str, user_ip):
    """Get progress dict keyed by quest_type for a specific visitor."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT quest_type, progress, completed, claimed "
        "FROM island_quest_progress WHERE world_id=? AND quest_date=? AND user_ip=?",
        (world_id, date_str, user_ip)
    ).fetchall()
    conn.close()
    return {r['quest_type']: {'progress': r['progress'], 'completed': r['completed'], 'claimed': r['claimed']} for r in rows}


def increment_island_quest_progress(world_id, date_str, quest_type, user_ip):
    """Increment progress by 1. Auto-set completed=1 if progress >= target."""
    conn = get_conn()
    # Ensure progress row exists
    conn.execute(
        "INSERT OR IGNORE INTO island_quest_progress "
        "(world_id, quest_date, quest_type, user_ip, progress, completed, claimed) "
        "VALUES (?,?,?,?,0,0,0)",
        (world_id, date_str, quest_type, user_ip)
    )
    # Increment progress
    conn.execute(
        "UPDATE island_quest_progress SET progress=progress+1, updated_at=datetime('now') "
        "WHERE world_id=? AND quest_date=? AND quest_type=? AND user_ip=?",
        (world_id, date_str, quest_type, user_ip)
    )
    # Check if completed
    row = conn.execute(
        "SELECT p.progress, q.target_count FROM island_quest_progress p "
        "JOIN island_daily_quests q ON q.world_id=p.world_id AND q.quest_date=p.quest_date AND q.quest_type=p.quest_type "
        "WHERE p.world_id=? AND p.quest_date=? AND p.quest_type=? AND p.user_ip=?",
        (world_id, date_str, quest_type, user_ip)
    ).fetchone()
    if row and row['progress'] >= row['target_count']:
        conn.execute(
            "UPDATE island_quest_progress SET completed=1 "
            "WHERE world_id=? AND quest_date=? AND quest_type=? AND user_ip=?",
            (world_id, date_str, quest_type, user_ip)
        )
    conn.commit()
    conn.close()


def claim_island_quest_reward(world_id, date_str, quest_type, user_ip):
    """Mark claimed, return reward_coins (or None if not completed or already claimed)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT p.completed, p.claimed, q.reward_coins "
        "FROM island_quest_progress p "
        "JOIN island_daily_quests q ON q.world_id=p.world_id AND q.quest_date=p.quest_date AND q.quest_type=p.quest_type "
        "WHERE p.world_id=? AND p.quest_date=? AND p.quest_type=? AND p.user_ip=?",
        (world_id, date_str, quest_type, user_ip)
    ).fetchone()
    if not row or not row['completed'] or row['claimed']:
        conn.close()
        return None
    conn.execute(
        "UPDATE island_quest_progress SET claimed=1, updated_at=datetime('now') "
        "WHERE world_id=? AND quest_date=? AND quest_type=? AND user_ip=?",
        (world_id, date_str, quest_type, user_ip)
    )
    conn.commit()
    conn.close()
    return row['reward_coins']


init_island_quests()

# ── Visitor Achievements System ────────────────────────────────

def init_visitor_achievements():
    """Create visitor achievement tables if not exist."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS visitor_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        achievement_id TEXT NOT NULL,
        unlocked_at TEXT NOT NULL,
        UNIQUE(user_id, achievement_id)
    );
    CREATE TABLE IF NOT EXISTS visitor_stats (
        user_id TEXT PRIMARY KEY,
        islands_visited INTEGER DEFAULT 0,
        guestbook_posts INTEGER DEFAULT 0,
        fish_caught INTEGER DEFAULT 0,
        treasures_found INTEGER DEFAULT 0,
        quests_completed INTEGER DEFAULT 0,
        reactions_given INTEGER DEFAULT 0,
        gifts_sent INTEGER DEFAULT 0,
        coins_earned INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS visitor_island_visits (
        user_id TEXT NOT NULL,
        island_id TEXT NOT NULL,
        visited_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, island_id)
    );
    """)
    conn.commit()
    # Migration: add visited_at column if it doesn't exist
    try:
        conn.execute("ALTER TABLE visitor_island_visits ADD COLUMN visited_at TEXT DEFAULT (datetime('now'))")
        conn.commit()
    except Exception:
        pass  # Column already exists
    conn.close()


def increment_visitor_stat(user_id, stat_name, amount=1):
    """Upsert into visitor_stats, incrementing the specified stat. Return the new value."""
    allowed = ('islands_visited', 'guestbook_posts', 'fish_caught', 'treasures_found',
               'quests_completed', 'reactions_given', 'gifts_sent', 'coins_earned', 'bottles_sent')
    if stat_name not in allowed:
        return 0
    conn = get_conn()
    conn.execute(f"""
        INSERT INTO visitor_stats (user_id, {stat_name}) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET {stat_name} = {stat_name} + ?
    """, (user_id, amount, amount))
    conn.commit()
    row = conn.execute(f"SELECT {stat_name} FROM visitor_stats WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[stat_name] if row else amount


def get_visitor_stats(user_id):
    """Get all visitor stats for a user."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM visitor_stats WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return {
            'islands_visited': 0, 'guestbook_posts': 0, 'fish_caught': 0,
            'treasures_found': 0, 'quests_completed': 0, 'reactions_given': 0,
            'gifts_sent': 0, 'coins_earned': 0
        }
    return dict(row)


def check_visitor_achievements(user_id, achievements_list):
    """Check each achievement threshold and unlock any newly earned.
    Returns list of newly unlocked achievement dicts."""
    stats = get_visitor_stats(user_id)
    now = datetime.now(timezone.utc).isoformat()
    newly_unlocked = []
    conn = get_conn()
    for ach in achievements_list:
        stat_val = stats.get(ach['stat'], 0)
        if stat_val >= ach['threshold']:
            try:
                conn.execute(
                    "INSERT INTO visitor_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)",
                    (user_id, ach['id'], now)
                )
                newly_unlocked.append(ach)
            except Exception:
                pass  # UNIQUE constraint → already unlocked
    conn.commit()
    conn.close()
    return newly_unlocked


def get_visitor_achievements(user_id):
    """Get all unlocked visitor achievements for a user as dict keyed by achievement_id."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT achievement_id, unlocked_at FROM visitor_achievements WHERE user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()
    return {r['achievement_id']: r['unlocked_at'] for r in rows}


def track_visitor_island_visit(user_id, island_id):
    """Track an island visit. Updates visited_at on repeat visits.
    Returns True if this is a new visit, False if repeat."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    # Check if visit already exists
    existing = conn.execute(
        "SELECT 1 FROM visitor_island_visits WHERE user_id=? AND island_id=?",
        (user_id, island_id)
    ).fetchone()
    if existing:
        # Repeat visit — just update timestamp
        conn.execute(
            "UPDATE visitor_island_visits SET visited_at=? WHERE user_id=? AND island_id=?",
            (now, user_id, island_id)
        )
        conn.commit()
        conn.close()
        return False
    else:
        # New visit — insert
        conn.execute(
            "INSERT INTO visitor_island_visits (user_id, island_id, visited_at) VALUES (?, ?, ?)",
            (user_id, island_id, now)
        )
        conn.commit()
        conn.close()
        return True


def get_recently_visited(user_id, limit=10):
    """Return island_ids ordered by visited_at DESC (most recent first)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT island_id FROM visitor_island_visits WHERE user_id=? ORDER BY visited_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [r['island_id'] for r in rows]


init_visitor_achievements()


# ── Tide Bottles ─────────────────────────────────────────────
def init_tide_bottles():
    """Create tide_bottles table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS tide_bottles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_name TEXT NOT NULL DEFAULT 'Anonymous',
        sender_id TEXT,
        message TEXT NOT NULL,
        origin_island TEXT NOT NULL,
        current_island TEXT,
        created_at TEXT NOT NULL,
        found_at TEXT,
        found_by TEXT,
        emoji TEXT DEFAULT '🍾'
    );
    CREATE INDEX IF NOT EXISTS idx_tb_current ON tide_bottles(current_island, found_at);
    CREATE INDEX IF NOT EXISTS idx_tb_sender ON tide_bottles(sender_id);
    """)
    conn.commit()
    conn.close()

    # Add bottles_sent to visitor_stats if not exists
    conn = get_conn()
    try:
        conn.execute("ALTER TABLE visitor_stats ADD COLUMN bottles_sent INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.close()


# In-memory rate limit trackers for bottles
_bottle_send_cooldown = {}   # ip_hash -> last_send_time
_bottle_deliver_cooldown = {}  # world_id -> last_deliver_time


def create_bottle(sender_name, sender_id, message, origin_island, emoji):
    """Insert a new bottle (at sea). Returns bottle dict."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO tide_bottles (sender_name, sender_id, message, origin_island, emoji, created_at) VALUES (?,?,?,?,?,?)",
        (sender_name, sender_id, message[:140], origin_island, emoji, now)
    )
    bottle_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        'id': bottle_id, 'sender_name': sender_name, 'sender_id': sender_id,
        'message': message[:140], 'origin_island': origin_island,
        'current_island': None, 'created_at': now,
        'found_at': None, 'found_by': None, 'emoji': emoji,
    }


def get_beach_bottles(world_id, limit=5):
    """Get bottles that have washed up on this island (most recent first)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tide_bottles WHERE current_island=? ORDER BY created_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def maybe_deliver_bottle(world_id):
    """10% chance to assign a random undelivered bottle to this island.
    Rate limit: max 1 delivery per island per 5 minutes.
    Won't deliver a bottle back to its origin island."""
    import random
    import time as _time

    now = _time.time()
    last = _bottle_deliver_cooldown.get(world_id, 0)
    if now - last < 300:  # 5 min cooldown
        return None

    if random.random() > 0.10:  # 10% chance
        return None

    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM tide_bottles WHERE current_island IS NULL AND origin_island != ? ORDER BY RANDOM() LIMIT 1",
        (world_id,)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE tide_bottles SET current_island=? WHERE id=?",
            (world_id, row['id'])
        )
        conn.commit()
        _bottle_deliver_cooldown[world_id] = now
        conn.close()
        return row['id']
    conn.close()
    return None


def find_bottle(bottle_id, finder_name):
    """Mark a bottle as found. Returns the bottle dict or None."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE tide_bottles SET found_at=?, found_by=? WHERE id=? AND found_at IS NULL",
        (now, finder_name, bottle_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tide_bottles WHERE id=?", (bottle_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_sent_bottles(sender_id):
    """Get all bottles sent by a user, ordered by newest first."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM tide_bottles WHERE sender_id=? ORDER BY created_at DESC",
        (sender_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unfound_bottle_count(world_id):
    """Count unfound bottles on an island's beach."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM tide_bottles WHERE current_island=? AND found_at IS NULL",
        (world_id,)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


init_tide_bottles()


# ── Time Capsules System ──────────────────────────────────────

def init_time_capsules():
    """Create time_capsules table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS time_capsules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        author_name TEXT NOT NULL DEFAULT 'Visitor',
        author_id TEXT,
        message TEXT NOT NULL,
        buried_at REAL NOT NULL,
        unlock_at REAL NOT NULL,
        opened INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_capsules_world ON time_capsules(world_id, buried_at DESC);
    """)
    conn.commit()
    conn.close()


def add_time_capsule(world_id, author_name, author_id, message, buried_at, unlock_at):
    """Insert a time capsule. Returns the capsule dict."""
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO time_capsules (world_id, author_name, author_id, message, buried_at, unlock_at, opened) "
        "VALUES (?,?,?,?,?,?,0)",
        (world_id, author_name, author_id, message, buried_at, unlock_at)
    )
    capsule_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        'id': capsule_id, 'world_id': world_id, 'author_name': author_name,
        'author_id': author_id, 'message': message, 'buried_at': buried_at,
        'unlock_at': unlock_at, 'opened': 0,
    }


def get_time_capsules(world_id, limit=20):
    """Get capsules for an island ordered by buried_at DESC.
    Returns raw rows — caller decides whether to redact locked messages."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, world_id, author_name, author_id, message, buried_at, unlock_at, opened "
        "FROM time_capsules WHERE world_id=? ORDER BY buried_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_time_capsule_counts(world_id):
    """Return {total, locked, unlocked} counts."""
    now = _time.time()
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) as cnt FROM time_capsules WHERE world_id=?", (world_id,)
    ).fetchone()['cnt']
    locked = conn.execute(
        "SELECT COUNT(*) as cnt FROM time_capsules WHERE world_id=? AND unlock_at > ?",
        (world_id, now)
    ).fetchone()['cnt']
    conn.close()
    return {'total': total, 'locked': locked, 'unlocked': total - locked}


def check_capsule_rate_limit(world_id, author_id):
    """Check if this author already buried a capsule on this island in the last 24h.
    Returns True if rate-limited (should block)."""
    cutoff = _time.time() - 86400  # 24 hours
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM time_capsules WHERE world_id=? AND author_id=? AND buried_at > ?",
        (world_id, author_id, cutoff)
    ).fetchone()
    conn.close()
    return row is not None


init_time_capsules()


# ── Timed Island Events System (bonus multiplier events) ──────

TIMED_EVENT_TYPES = [
    {'type': 'fishing_frenzy',    'emoji': '🎣', 'name': 'Fishing Frenzy',    'bonus': '2x fish catch & rare chance doubled', 'duration_min': 10, 'multiplier': 2.0},
    {'type': 'treasure_rain',     'emoji': '💎', 'name': 'Treasure Rain',     'bonus': 'Extra treasures spawn (+3)',          'duration_min': 8,  'multiplier': 2.0},
    {'type': 'golden_hour',       'emoji': '✨', 'name': 'Golden Hour',       'bonus': 'All coin rewards doubled',            'duration_min': 15, 'multiplier': 2.0},
    {'type': 'visitor_festival',  'emoji': '🎉', 'name': 'Visitor Festival',  'bonus': 'Guestbook posts give +2 coins each',  'duration_min': 12, 'multiplier': 2.0},
    {'type': 'mystery_fog',       'emoji': '🌫️', 'name': 'Mystery Fog',      'bonus': 'Hidden bonus items, 1.5x all rewards','duration_min': 10, 'multiplier': 1.5},
]


def init_timed_events_table():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS timed_island_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        started_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        bonus_multiplier REAL DEFAULT 2.0,
        participants INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_timed_events_world ON timed_island_events(world_id, expires_at);
    """)
    conn.commit()
    conn.close()


def check_and_spawn_timed_event(conn, world_id):
    """Deterministic: check if a timed event should fire this hour. ~30% chance via hash."""
    import hashlib as _te_hl
    import time as _te_time
    now = _te_time.time()
    hour_slot = int(now // 3600)
    seed = _te_hl.sha256(f"{world_id}:{hour_slot}:events".encode()).hexdigest()
    seed_int = int(seed[:8], 16)
    if (seed_int % 100) >= 30:
        return None
    slot_start = hour_slot * 3600
    existing = conn.execute(
        "SELECT id FROM timed_island_events WHERE world_id=? AND started_at>=? AND started_at<?",
        (world_id, float(slot_start), float(slot_start + 3600))
    ).fetchone()
    if existing:
        return None
    evt = TIMED_EVENT_TYPES[seed_int % 5]
    started_at = now
    expires_at = now + evt['duration_min'] * 60
    cur = conn.execute(
        "INSERT INTO timed_island_events (world_id, event_type, started_at, expires_at, bonus_multiplier) VALUES (?,?,?,?,?)",
        (world_id, evt['type'], started_at, expires_at, evt['multiplier'])
    )
    conn.commit()
    return {
        'id': cur.lastrowid, 'world_id': world_id, 'event_type': evt['type'],
        'emoji': evt['emoji'], 'name': evt['name'], 'bonus': evt['bonus'],
        'started_at': started_at, 'expires_at': expires_at,
        'bonus_multiplier': evt['multiplier'], 'participants': 0,
    }


def get_active_timed_event(conn, world_id):
    """Get the current non-expired timed event, or None."""
    import time as _te_time
    now = _te_time.time()
    row = conn.execute(
        "SELECT * FROM timed_island_events WHERE world_id=? AND expires_at>? ORDER BY started_at DESC LIMIT 1",
        (world_id, now)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    meta = next((e for e in TIMED_EVENT_TYPES if e['type'] == d['event_type']), None)
    if meta:
        d['emoji'] = meta['emoji']
        d['name'] = meta['name']
        d['bonus'] = meta['bonus']
    return d


def get_timed_event_history(conn, world_id, limit=10):
    """Get recent timed events for this island."""
    rows = conn.execute(
        "SELECT * FROM timed_island_events WHERE world_id=? ORDER BY started_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        meta = next((e for e in TIMED_EVENT_TYPES if e['type'] == d['event_type']), None)
        if meta:
            d['emoji'] = meta['emoji']
            d['name'] = meta['name']
            d['bonus'] = meta['bonus']
        result.append(d)
    return result


def increment_timed_event_participants(conn, event_id):
    """Bump participant count for a timed event."""
    conn.execute("UPDATE timed_island_events SET participants=participants+1 WHERE id=?", (event_id,))
    conn.commit()


init_timed_events_table()


# ── Island Reviews System (ratings + text reviews) ────────────

def init_reviews():
    """Create island_reviews table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        author_name TEXT NOT NULL DEFAULT 'Visitor',
        author_id TEXT NOT NULL,
        rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
        review TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_reviews_world ON island_reviews(world_id, created_at DESC);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_author_world ON island_reviews(author_id, world_id);
    """)
    conn.commit()
    conn.close()


def add_review(world_id, author_name, author_id, rating, review=''):
    """Insert or update a review (upsert — max 1 per author per island). Returns the review row."""
    now = datetime.now(timezone.utc).isoformat()
    review = (review or '')[:200]
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM island_reviews WHERE author_id=? AND world_id=?",
        (author_id, world_id)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE island_reviews SET author_name=?, rating=?, review=?, created_at=? WHERE id=?",
            (author_name, rating, review, now, existing['id'])
        )
        review_id = existing['id']
    else:
        cursor = conn.execute(
            "INSERT INTO island_reviews (world_id, author_name, author_id, rating, review, created_at) VALUES (?,?,?,?,?,?)",
            (world_id, author_name, author_id, rating, review, now)
        )
        review_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        'id': review_id, 'world_id': world_id, 'author_name': author_name,
        'author_id': author_id, 'rating': rating, 'review': review, 'created_at': now,
    }


def get_reviews(world_id, limit=20):
    """Get reviews for an island, newest first."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, world_id, author_name, rating, review, created_at "
        "FROM island_reviews WHERE world_id=? ORDER BY created_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_average_review_rating(world_id):
    """Return avg rating and count from reviews for an island."""
    conn = get_conn()
    row = conn.execute(
        "SELECT AVG(rating) as avg_rating, COUNT(*) as cnt FROM island_reviews WHERE world_id=?",
        (world_id,)
    ).fetchone()
    conn.close()
    return {
        'avg': round(row['avg_rating'], 1) if row['avg_rating'] else 0.0,
        'count': row['cnt'] if row else 0,
    }


def get_average_review_ratings_bulk(world_ids):
    """Return dict of world_id -> {avg, count} for multiple islands (single query)."""
    if not world_ids:
        return {}
    conn = get_conn()
    placeholders = ','.join('?' for _ in world_ids)
    rows = conn.execute(
        f"SELECT world_id, AVG(rating) as avg_rating, COUNT(*) as cnt "
        f"FROM island_reviews WHERE world_id IN ({placeholders}) GROUP BY world_id",
        world_ids
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        result[r['world_id']] = {
            'avg': round(r['avg_rating'], 1) if r['avg_rating'] else 0.0,
            'count': r['cnt'],
        }
    return result


def check_review_rate_limit(world_id, author_id):
    """Check if this author already submitted a review on this island in the last 24h.
    Returns True if rate-limited (should block)."""
    from datetime import timedelta as _rl_td
    cutoff = (datetime.now(timezone.utc) - _rl_td(hours=24)).isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM island_reviews WHERE world_id=? AND author_id=? AND created_at > ?",
        (world_id, author_id, cutoff)
    ).fetchone()
    conn.close()
    return row is not None


init_reviews()


# ── Island Portals ────────────────────────────────────────────

def init_portals():
    """Create island_portals table for portal links between islands."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_portals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        target_island_id TEXT NOT NULL,
        target_island_name TEXT DEFAULT '',
        label TEXT DEFAULT 'Portal',
        col INTEGER DEFAULT 16,
        row INTEGER DEFAULT 16,
        created_at REAL DEFAULT (strftime('%s','now'))
    );
    CREATE INDEX IF NOT EXISTS idx_portals_world ON island_portals(world_id);
    """)
    conn.close()


def add_portal(world_id, target_island_id, target_island_name, label, col, row):
    """Add a portal to an island. Max 3 portals per island."""
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM island_portals WHERE world_id=?",
        (world_id,)
    ).fetchone()['cnt']
    if count >= 3:
        conn.close()
        return {'ok': False, 'error': 'Maximum 3 portals per island'}
    conn.execute(
        "INSERT INTO island_portals (world_id, target_island_id, target_island_name, label, col, row) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (world_id, target_island_id, target_island_name or '', label or 'Portal', col, row)
    )
    conn.commit()
    portal_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()['id']
    conn.close()
    return {'ok': True, 'id': portal_id}


def get_portals(world_id):
    """Return list of portals for an island as dicts."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, world_id, target_island_id, target_island_name, label, col, row, created_at "
        "FROM island_portals WHERE world_id=? ORDER BY created_at ASC",
        (world_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_portal(portal_id, world_id):
    """Delete a portal (owner only, verify world_id matches)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM island_portals WHERE id=? AND world_id=?",
        (portal_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Portal not found'}
    conn.execute("DELETE FROM island_portals WHERE id=?", (portal_id,))
    conn.commit()
    conn.close()
    return {'ok': True}


init_portals()

# ── Island Treasures (Treasure Hunt Mini-Game) ─────────────────

import random as _treasure_rnd
from datetime import timedelta as _time_module_td

TREASURE_TYPE_CONFIG = {
    'shell':    {'coins_reward': 5,  'emoji': '🐚', 'name': 'Shell'},
    'gem':      {'coins_reward': 15, 'emoji': '💎', 'name': 'Gem'},
    'chest':    {'coins_reward': 20, 'emoji': '🏴\u200d☠️', 'name': 'Treasure Chest'},
    'coin_bag': {'coins_reward': 25, 'emoji': '💰', 'name': 'Coin Bag'},
    'star':     {'coins_reward': 30, 'emoji': '⭐', 'name': 'Golden Star'},
}

# Weighted selection: shell 35%, gem 25%, chest 20%, coin_bag 15%, star 5%
_TREASURE_WEIGHTS = [
    ('shell', 35), ('gem', 25), ('chest', 20), ('coin_bag', 15), ('star', 5),
]


def init_island_treasures():
    """Create island_treasures table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_treasures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        x REAL NOT NULL,
        y REAL NOT NULL,
        treasure_type TEXT NOT NULL,
        coins_reward INTEGER DEFAULT 10,
        found_by TEXT,
        found_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_it_world ON island_treasures(world_id, found_by, expires_at);
    """)
    conn.commit()
    conn.close()


def _pick_weighted_treasure_type():
    """Pick a treasure type using weighted random selection."""
    roll = _treasure_rnd.randint(1, 100)
    cumulative = 0
    for ttype, weight in _TREASURE_WEIGHTS:
        cumulative += weight
        if roll <= cumulative:
            return ttype
    return 'shell'


def _ensure_island_treasures(world_id):
    """Auto-spawn treasures for an island if fewer than 2 active unfound treasures exist."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_conn()

    # Count active unfound treasures (not expired, not found)
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM island_treasures WHERE world_id=? AND found_by IS NULL AND expires_at > ?",
        (world_id, now_iso)
    ).fetchone()
    active_count = row['cnt'] if row else 0

    if active_count >= 2:
        conn.close()
        return

    # Spawn enough to reach 2-4 total
    target = _treasure_rnd.randint(2, 4)
    to_spawn = max(0, target - active_count)

    now = datetime.now(timezone.utc)
    expires = (now + _time_module_td(hours=24)).isoformat()

    for _ in range(to_spawn):
        ttype = _pick_weighted_treasure_type()
        config = TREASURE_TYPE_CONFIG[ttype]
        x = round(_treasure_rnd.uniform(0.15, 0.85), 4)
        y = round(_treasure_rnd.uniform(0.15, 0.85), 4)
        conn.execute(
            "INSERT INTO island_treasures (world_id, x, y, treasure_type, coins_reward, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (world_id, x, y, ttype, config['coins_reward'], now.isoformat(), expires)
        )
    conn.commit()
    conn.close()


def get_active_island_treasures(world_id):
    """Return active unfound treasures (not expired). Only returns x, y, type — NOT reward."""
    _ensure_island_treasures(world_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, x, y, treasure_type FROM island_treasures "
        "WHERE world_id=? AND found_by IS NULL AND expires_at > ? "
        "ORDER BY created_at ASC",
        (world_id, now_iso)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def collect_island_treasure(world_id, treasure_id, click_x, click_y, visitor_id):
    """Try to collect a treasure. Returns treasure info on success, None on failure."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT id, x, y, treasure_type, coins_reward FROM island_treasures "
        "WHERE id=? AND world_id=? AND found_by IS NULL AND expires_at > ?",
        (treasure_id, world_id, now_iso)
    ).fetchone()
    if not row:
        conn.close()
        return None

    # Check distance (0.05 threshold on normalized coords)
    dx = abs(row['x'] - click_x)
    dy = abs(row['y'] - click_y)
    dist = (dx * dx + dy * dy) ** 0.5
    if dist > 0.05:
        conn.close()
        return None

    # Mark as found
    conn.execute(
        "UPDATE island_treasures SET found_by=?, found_at=? WHERE id=?",
        (visitor_id, now_iso, treasure_id)
    )
    conn.commit()
    conn.close()

    ttype = row['treasure_type']
    config = TREASURE_TYPE_CONFIG.get(ttype, {'emoji': '🐚', 'name': ttype, 'coins_reward': 5})
    return {
        'id': row['id'],
        'treasure_type': ttype,
        'coins_reward': row['coins_reward'],
        'emoji': config['emoji'],
        'name': config['name'],
        'x': row['x'],
        'y': row['y'],
    }


def get_treasure_hunt_stats(world_id):
    """Return total treasures found and total coins earned on this island."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as found, COALESCE(SUM(coins_reward), 0) as coins "
        "FROM island_treasures WHERE world_id=? AND found_by IS NOT NULL",
        (world_id,)
    ).fetchone()
    conn.close()
    return {'total_found': row['found'] if row else 0, 'total_coins': row['coins'] if row else 0}


def count_treasure_collections_by_ip(world_id, visitor_ip, window_seconds=3600):
    """Count treasures collected by this IP on this island in the last window."""
    cutoff = (datetime.now(timezone.utc) - _time_module_td(seconds=window_seconds)).isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM island_treasures "
        "WHERE world_id=? AND found_by=? AND found_at >= ?",
        (world_id, visitor_ip, cutoff)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


init_island_treasures()


# ── Island Live Chat ──────────────────────────────────────────

def init_island_chat():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_chat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        display_name TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_island_chat_world_expires
        ON island_chat(world_id, expires_at);
    """)
    conn.close()

def post_chat_message(world_id, user_id, display_name, message):
    now = datetime.now(timezone.utc)
    expires = now + _time_module_td(minutes=10)
    conn = get_conn()
    conn.execute(
        "INSERT INTO island_chat (world_id, user_id, display_name, message, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (world_id, user_id, display_name, message[:100], now.isoformat(), expires.isoformat())
    )
    conn.commit()
    conn.close()

def get_chat_messages(world_id, limit=30):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, user_id, display_name, message, created_at FROM island_chat "
        "WHERE world_id=? AND expires_at > ? ORDER BY created_at DESC LIMIT ?",
        (world_id, now, limit)
    ).fetchall()
    conn.close()
    # Return in chronological order (oldest first)
    return [dict(r) for r in reversed(rows)]

def cleanup_expired_chat():
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute("DELETE FROM island_chat WHERE expires_at <= ?", (now,))
    conn.commit()
    conn.close()

init_island_chat()

# ── Island Follow System ──────────────────────────────────────

def init_follows_table():
    """Create island_follows table if not exists."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS island_follows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        island_id TEXT NOT NULL,
        created_at TEXT,
        UNIQUE(user_id, island_id)
    );
    CREATE INDEX IF NOT EXISTS idx_follow_user ON island_follows(user_id);
    CREATE INDEX IF NOT EXISTS idx_follow_island ON island_follows(island_id);
    """)
    conn.commit()
    conn.close()


def toggle_follow(user_id, island_id):
    """Toggle follow: INSERT if not exists, DELETE if exists. Returns {'following': bool, 'follower_count': int}."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM island_follows WHERE user_id=? AND island_id=?",
        (user_id, island_id)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM island_follows WHERE user_id=? AND island_id=?", (user_id, island_id))
        conn.commit()
        count = conn.execute("SELECT COUNT(*) as cnt FROM island_follows WHERE island_id=?", (island_id,)).fetchone()['cnt']
        conn.close()
        return {'following': False, 'follower_count': count}
    else:
        conn.execute(
            "INSERT INTO island_follows (user_id, island_id, created_at) VALUES (?,?,?)",
            (user_id, island_id, now)
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) as cnt FROM island_follows WHERE island_id=?", (island_id,)).fetchone()['cnt']
        conn.close()
        return {'following': True, 'follower_count': count}


def get_user_follows(user_id):
    """Return list of island_ids the user follows."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT island_id FROM island_follows WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return [r['island_id'] for r in rows]


def get_follower_count(island_id):
    """Return follower count for a single island."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM island_follows WHERE island_id=?", (island_id,)
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


init_follows_table()


# ── Similar Islands ────────────────────────────────────────────

def get_similar_islands(world_id, limit=4):
    """Find other islands of the same island_type, excluding the given world.
    Sorted by visit_count DESC. Returns list of dicts."""
    conn = get_conn()
    # Get the current island's type
    row = conn.execute("SELECT island_type FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not row or not row['island_type']:
        conn.close()
        return []
    island_type = row['island_type']
    rows = conn.execute("""
        SELECT w.id, w.name, w.island_type, w.owner,
               COALESCE(pv.cnt, 0) + COALESCE(v.cnt, 0) as visit_count,
               COALESCE(p.level, 1) as level,
               COALESCE(rv.avg_rating, 0) as rating_avg
        FROM worlds w
        LEFT JOIN (SELECT world_id, COUNT(*) as cnt FROM page_views GROUP BY world_id) pv ON pv.world_id = w.id
        LEFT JOIN (SELECT world_id, COUNT(*) as cnt FROM visits GROUP BY world_id) v ON v.world_id = w.id
        LEFT JOIN user_progress p ON p.world_id = w.id
        LEFT JOIN (SELECT world_id, AVG(rating) as avg_rating FROM island_reviews GROUP BY world_id) rv ON rv.world_id = w.id
        WHERE w.island_type = ? AND w.id != ?
        ORDER BY visit_count DESC
        LIMIT ?
    """, (island_type, world_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Captain's Log (Owner Journal) ─────────────────────────────

def init_captains_log():
    """Create captains_log table for island owner journals."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS captains_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        message TEXT NOT NULL,
        emoji TEXT DEFAULT '📝',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (world_id) REFERENCES worlds(id)
    );
    CREATE INDEX IF NOT EXISTS idx_captains_log_world ON captains_log(world_id);
    """)
    conn.close()


def get_captains_log(world_id, limit=20):
    """Get recent captain's log entries, newest first."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, world_id, message, emoji, created_at FROM captains_log "
        "WHERE world_id=? ORDER BY created_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_captains_log(world_id, message, emoji='📝'):
    """Add a captain's log entry. Auto-deletes oldest if over 50 entries."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO captains_log (world_id, message, emoji) VALUES (?, ?, ?)",
        (world_id, message[:280], emoji or '📝')
    )
    conn.commit()
    entry_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()['id']
    # Cap at 50 entries: delete oldest if over limit
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM captains_log WHERE world_id=?",
        (world_id,)
    ).fetchone()['cnt']
    if count > 50:
        conn.execute(
            "DELETE FROM captains_log WHERE id IN "
            "(SELECT id FROM captains_log WHERE world_id=? ORDER BY created_at ASC LIMIT ?)",
            (world_id, count - 50)
        )
        conn.commit()
    conn.close()
    return {'ok': True, 'id': entry_id}


def delete_captains_log(log_id, world_id):
    """Delete a captain's log entry (owner only, verify world_id matches)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM captains_log WHERE id=? AND world_id=?",
        (log_id, world_id)
    ).fetchone()
    if not row:
        conn.close()
        return {'ok': False, 'error': 'Entry not found'}
    conn.execute("DELETE FROM captains_log WHERE id=?", (log_id,))
    conn.commit()
    conn.close()
    return {'ok': True}


def count_captains_log(world_id):
    """Count captain's log entries for an island."""
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM captains_log WHERE world_id=?",
        (world_id,)
    ).fetchone()['cnt']
    conn.close()
    return count


init_captains_log()


# ── Island Passport ──────────────────────────────────────────
def stamp_passport(user_id, island_id, island_name='', island_avatar='🦞', island_level=1):
    """Add a stamp to user's passport. Returns dict with new=True if first visit."""
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            """INSERT INTO island_passport (user_id, island_id, island_name, island_avatar, island_level, stamped_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, island_id, island_name, island_avatar, island_level, now)
        )
        conn.commit()
        total = conn.execute("SELECT COUNT(*) as cnt FROM island_passport WHERE user_id=?", (user_id,)).fetchone()['cnt']
        conn.close()
        return {'ok': True, 'new': True, 'total_stamps': total, 'island_name': island_name}
    except Exception:
        # Already stamped (UNIQUE constraint)
        total = conn.execute("SELECT COUNT(*) as cnt FROM island_passport WHERE user_id=?", (user_id,)).fetchone()['cnt']
        conn.close()
        return {'ok': True, 'new': False, 'total_stamps': total}


def get_passport(user_id, limit=50):
    """Get all passport stamps for a user, newest first."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT island_id, island_name, island_avatar, island_level, stamped_at FROM island_passport WHERE user_id=? ORDER BY stamped_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_passport_count(user_id):
    """Get total stamp count for a user."""
    conn = get_conn()
    cnt = conn.execute("SELECT COUNT(*) as cnt FROM island_passport WHERE user_id=?", (user_id,)).fetchone()['cnt']
    conn.close()
    return cnt


# ── Bottle Messages System ──────────────────────────────────────

def init_bottles():
    """Create bottles table for cross-island message-in-a-bottle."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS bottles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_world_id TEXT NOT NULL,
        from_name TEXT NOT NULL DEFAULT 'Anonymous',
        message TEXT NOT NULL,
        created_at REAL NOT NULL,
        landed_world_id TEXT,
        found_by TEXT,
        found_at REAL,
        status TEXT NOT NULL DEFAULT 'floating'
    );
    CREATE INDEX IF NOT EXISTS idx_bottles_landed ON bottles(landed_world_id, status);
    CREATE INDEX IF NOT EXISTS idx_bottles_from ON bottles(from_world_id, created_at);
    """)
    conn.commit()
    conn.close()


def toss_bottle(from_world_id, from_name, message):
    """Toss a bottle into the sea. Lands on a random different island."""
    import time, random
    now = time.time()
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO bottles (from_world_id, from_name, message, created_at, status) VALUES (?,?,?,?,'floating')",
        (from_world_id, from_name[:30], message[:140], now)
    )
    bottle_id = cursor.lastrowid
    # Pick a random different world to land on
    row = conn.execute(
        "SELECT id FROM worlds WHERE id != ? ORDER BY RANDOM() LIMIT 1",
        (from_world_id,)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE bottles SET landed_world_id=?, status='landed' WHERE id=?",
            (row['id'], bottle_id)
        )
    conn.commit()
    bottle = conn.execute("SELECT * FROM bottles WHERE id=?", (bottle_id,)).fetchone()
    conn.close()
    return dict(bottle) if bottle else None


def get_landed_bottles(world_id, limit=3):
    """Get unfound bottles that washed up on this island."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM bottles WHERE landed_world_id=? AND status='landed' ORDER BY created_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_msg_bottle(bottle_id, finder_name):
    """Mark a bottle as found. Returns the bottle dict."""
    import time
    now = time.time()
    conn = get_conn()
    conn.execute(
        "UPDATE bottles SET status='found', found_by=?, found_at=? WHERE id=? AND status='landed'",
        (finder_name[:30], now, bottle_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM bottles WHERE id=?", (bottle_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_bottle_stats():
    """Global bottle statistics."""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM bottles").fetchone()['c']
    found = conn.execute("SELECT COUNT(*) as c FROM bottles WHERE status='found'").fetchone()['c']
    floating = conn.execute("SELECT COUNT(*) as c FROM bottles WHERE status IN ('floating','landed')").fetchone()['c']
    conn.close()
    return {'total_tossed': total, 'total_found': found, 'total_floating': floating}


def check_bottle_rate_limit(from_world_id):
    """True if a bottle was tossed from this world in the last 10 minutes."""
    import time
    cutoff = time.time() - 600
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM bottles WHERE from_world_id=? AND created_at>? LIMIT 1",
        (from_world_id, cutoff)
    ).fetchone()
    conn.close()
    return row is not None


init_bottles()



# ── Island Expeditions System ──────────────────────────────────
import random as _exp_random

def init_expeditions():
    """Create expeditions table for island expedition system."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS expeditions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id TEXT NOT NULL,
        destination TEXT NOT NULL,
        started_at REAL NOT NULL,
        duration_minutes INTEGER NOT NULL,
        completed_at REAL,
        loot_json TEXT,
        status TEXT DEFAULT 'active'
    );
    CREATE INDEX IF NOT EXISTS idx_expeditions_world ON expeditions(world_id);
    CREATE INDEX IF NOT EXISTS idx_expeditions_status ON expeditions(world_id, status);
    """)
    conn.close()


_EXPEDITION_DURATIONS = {
    'reef': (5, 15),
    'deep_sea': (15, 30),
    'shipwreck': (30, 45),
    'volcano': (45, 60),
}

_EXPEDITION_LOOT_POOLS = {
    'reef': {
        'items': [
            ('🐚', 'Pink Shell'), ('🐚', 'Spiral Shell'), ('🪸', 'Coral Fragment'),
            ('🫧', 'Sea Glass'), ('🐟', 'Small Fish'), ('🦀', 'Tiny Crab'),
            ('🌿', 'Seaweed'), ('💧', 'Sea Pearl Drop'),
        ],
        'count': (1, 3),
        'tier': 'Common',
    },
    'deep_sea': {
        'items': [
            ('🦪', 'Pearl'), ('🐠', 'Rare Fish'), ('🪙', 'Ancient Coin'),
            ('🌊', 'Deep Kelp'), ('🐙', 'Octopus Ink'), ('🔱', 'Trident Shard'),
            ('💎', 'Sea Diamond'), ('🧿', 'Abyssal Eye'),
        ],
        'count': (2, 4),
        'tier': 'Uncommon',
    },
    'shipwreck': {
        'items': [
            ('🪙', 'Gold Bar'), ('🗺️', 'Treasure Map'), ('🎩', "Captain's Hat"),
            ('💎', 'Ruby Gem'), ('⚓', 'Ancient Anchor'), ('🏴‍☠️', 'Pirate Flag'),
            ('📜', 'Old Scroll'), ('🔑', 'Rusty Key'),
        ],
        'count': (2, 5),
        'tier': 'Rare',
    },
    'volcano': {
        'items': [
            ('🪨', 'Obsidian'), ('🔥', 'Fire Crystal'), ('🐉', 'Dragon Scale'),
            ('🟣', 'Lava Pearl'), ('⚡', 'Thunder Stone'), ('🌋', 'Magma Core'),
            ('💀', 'Ash Fossil'), ('✨', 'Phoenix Feather'),
        ],
        'count': (3, 5),
        'tier': 'Legendary',
    },
}


def _generate_expedition_loot(destination):
    """Generate random loot based on destination."""
    pool = _EXPEDITION_LOOT_POOLS.get(destination, _EXPEDITION_LOOT_POOLS['reef'])
    count = _exp_random.randint(*pool['count'])
    chosen = _exp_random.sample(pool['items'], min(count, len(pool['items'])))
    return [{'emoji': emoji, 'name': name} for emoji, name in chosen]


def start_expedition(world_id, destination):
    """Start a new expedition. Only 1 active per island."""
    import time
    if destination not in _EXPEDITION_DURATIONS:
        return None, 'Invalid destination'

    conn = get_conn()
    # Check for active expedition
    active = conn.execute(
        "SELECT id FROM expeditions WHERE world_id=? AND status='active' LIMIT 1",
        (world_id,)
    ).fetchone()
    if active:
        conn.close()
        return None, 'An expedition is already active'

    dur_range = _EXPEDITION_DURATIONS[destination]
    duration = _exp_random.randint(dur_range[0], dur_range[1])
    now = time.time()
    conn.execute(
        "INSERT INTO expeditions (world_id, destination, started_at, duration_minutes, status) VALUES (?,?,?,?,?)",
        (world_id, destination, now, duration, 'active')
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM expeditions WHERE world_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (world_id,)
    ).fetchone()
    conn.close()
    exp = dict(row) if row else None
    if exp:
        exp['time_remaining'] = max(0, (exp['started_at'] + exp['duration_minutes'] * 60) - now)
    return exp, None


def check_expedition(world_id):
    """Check current expedition. Auto-completes if timer done."""
    import time
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM expeditions WHERE world_id=? AND status='active' ORDER BY id DESC LIMIT 1",
        (world_id,)
    ).fetchone()
    if not row:
        # Check for completed-unclaimed
        claimed = conn.execute(
            "SELECT * FROM expeditions WHERE world_id=? AND status='completed' ORDER BY completed_at DESC LIMIT 1",
            (world_id,)
        ).fetchone()
        conn.close()
        if claimed:
            exp = dict(claimed)
            import json
            exp['loot'] = json.loads(exp['loot_json']) if exp.get('loot_json') else []
            exp['time_remaining'] = 0
            return exp
        return None

    exp = dict(row)
    now = time.time()
    elapsed = now - exp['started_at']
    duration_secs = exp['duration_minutes'] * 60

    if elapsed >= duration_secs:
        # Auto-complete
        loot = _generate_expedition_loot(exp['destination'])
        import json
        loot_json = json.dumps(loot)
        conn.execute(
            "UPDATE expeditions SET status='completed', completed_at=?, loot_json=? WHERE id=?",
            (now, loot_json, exp['id'])
        )
        conn.commit()
        exp['status'] = 'completed'
        exp['completed_at'] = now
        exp['loot_json'] = loot_json
        exp['loot'] = loot
        exp['time_remaining'] = 0
    else:
        exp['time_remaining'] = duration_secs - elapsed
        exp['loot'] = []

    conn.close()
    return exp


def complete_expedition(expedition_id):
    """Claim loot — mark expedition as claimed."""
    conn = get_conn()
    conn.execute(
        "UPDATE expeditions SET status='claimed' WHERE id=? AND status='completed'",
        (expedition_id,)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM expeditions WHERE id=?", (expedition_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_expedition_history(world_id, limit=10):
    """Get recent completed/claimed expeditions."""
    import json
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM expeditions WHERE world_id=? AND status IN ('completed','claimed') ORDER BY completed_at DESC LIMIT ?",
        (world_id, limit)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d['loot'] = json.loads(d['loot_json']) if d.get('loot_json') else []
        result.append(d)
    return result


init_expeditions()
# ── End Island Expeditions System ──
