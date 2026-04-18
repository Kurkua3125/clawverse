#!/usr/bin/env python3
"""Clawverse v1 Backend — port 19003"""
from flask import Flask, jsonify, request, send_from_directory, send_file, Response, stream_with_context, make_response, redirect
import json, os, subprocess, re, shlex, threading, time, queue, hashlib, math
import html as html_module
from datetime import datetime, timezone
import db  # SQLite persistence layer
import auth  # Email-based authentication
import notifications  # Web Push + Email notification system

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET') or os.urandom(32).hex()
if not os.environ.get('FLASK_SECRET'):
    print("⚠️  WARNING: FLASK_SECRET not set, using random key (sessions won't persist across restarts)")

# ── CSRF Protection ──────────────────────────────────────────
@app.before_request
def csrf_protect():
    """Block cross-origin state-changing requests (CSRF protection)."""
    if request.method in ('POST', 'PUT', 'DELETE'):
        origin = request.headers.get('Origin', '')
        allowed_origins = [
            'https://genclawverse.ai',
            'http://127.0.0.1:19003',
            'http://localhost:19003',
        ]
        # Allow if no Origin header (same-origin/non-browser), or if Origin matches whitelist
        if origin and not any(origin.startswith(o) for o in allowed_origins):
            return jsonify({'error': 'CSRF check failed'}), 403

# ── CORS + Security Headers ──────────────────────────────────
@app.after_request
def add_security_headers(response):
    """Add CORS headers and security hardening headers."""
    allowed = ['https://genclawverse.ai']
    origin = request.headers.get('Origin', '')
    if origin in allowed or origin.startswith('http://localhost') or origin.startswith('http://127.0.0.1'):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    # Security hardening headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# ── Gzip Response Compression ────────────────────────────────
import gzip as _gzip_mod
import io as _io_mod

@app.after_request
def gzip_response(response):
    """Compress responses with gzip when client supports it."""
    if (response.status_code < 200 or response.status_code >= 300 or
        response.direct_passthrough or
        'Content-Encoding' in response.headers or
        len(response.get_data()) < 500):
        return response

    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding.lower():
        return response

    content_type = response.content_type or ''
    compressible = any(ct in content_type for ct in [
        'text/', 'application/json', 'application/javascript', 'image/svg'
    ])
    if not compressible:
        return response

    data = response.get_data()
    buf = _io_mod.BytesIO()
    with _gzip_mod.GzipFile(fileobj=buf, mode='wb', compresslevel=6) as f:
        f.write(data)
    compressed = buf.getvalue()

    # Only use compressed if it's actually smaller
    if len(compressed) < len(data):
        response.set_data(compressed)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(compressed)
        response.headers['Vary'] = 'Accept-Encoding'

    return response

# ── Visitor Achievements Definitions ──────────────────────────
VISITOR_ACHIEVEMENTS = [
    {'id': 'explorer_1', 'name': '🧭 Explorer', 'desc': 'Visit 5 different islands', 'stat': 'islands_visited', 'threshold': 5},
    {'id': 'explorer_2', 'name': '🗺️ Wayfarer', 'desc': 'Visit 15 different islands', 'stat': 'islands_visited', 'threshold': 15},
    {'id': 'explorer_3', 'name': '🌍 Globetrotter', 'desc': 'Visit 30 different islands', 'stat': 'islands_visited', 'threshold': 30},
    {'id': 'social_1', 'name': '💬 Friendly', 'desc': 'Leave 5 guestbook messages', 'stat': 'guestbook_posts', 'threshold': 5},
    {'id': 'social_2', 'name': '🦋 Social Butterfly', 'desc': 'Leave 20 guestbook messages', 'stat': 'guestbook_posts', 'threshold': 20},
    {'id': 'angler_1', 'name': '🎣 Novice Angler', 'desc': 'Catch 5 fish', 'stat': 'fish_caught', 'threshold': 5},
    {'id': 'angler_2', 'name': '🐟 Master Angler', 'desc': 'Catch 25 fish', 'stat': 'fish_caught', 'threshold': 25},
    {'id': 'treasure_1', 'name': '💎 Treasure Seeker', 'desc': 'Find 5 treasures', 'stat': 'treasures_found', 'threshold': 5},
    {'id': 'treasure_2', 'name': '🏴\u200d☠️ Treasure Hunter', 'desc': 'Find 20 treasures', 'stat': 'treasures_found', 'threshold': 20},
    {'id': 'quest_1', 'name': '📜 Quest Rookie', 'desc': 'Complete 5 quests', 'stat': 'quests_completed', 'threshold': 5},
    {'id': 'quest_2', 'name': '⚔️ Quest Champion', 'desc': 'Complete 20 quests', 'stat': 'quests_completed', 'threshold': 20},
    {'id': 'react_1', 'name': '❤️ Cheerful', 'desc': 'React to 10 islands', 'stat': 'reactions_given', 'threshold': 10},
    {'id': 'generous_1', 'name': '🎁 Generous', 'desc': 'Send 5 gifts', 'stat': 'gifts_sent', 'threshold': 5},
    {'id': 'rich_1', 'name': '💰 Moneybags', 'desc': 'Earn 500 coins total', 'stat': 'coins_earned', 'threshold': 500},
]


def _check_visitor_achievements(user_id):
    """Helper: check and return newly unlocked visitor achievements."""
    try:
        return db.check_visitor_achievements(user_id, VISITOR_ACHIEVEMENTS)
    except Exception:
        return []


# ── Custom 404 Page ───────────────────────────────────────────
PAGE_404 = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🏝️ Island Not Found — Clawverse</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
  *{margin:0;padding:0;box-sizing:border-box}
  body{
    background:#0a0e1a;
    color:#c8d6e5;
    font-family:'Press Start 2P',monospace;
    min-height:100vh;
    display:flex;flex-direction:column;align-items:center;justify-content:center;
    overflow:hidden;position:relative;
  }
  /* Stars */
  .stars{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0}
  .star{position:absolute;background:#fff;border-radius:50%;animation:twinkle 2s ease-in-out infinite alternate}
  @keyframes twinkle{0%{opacity:.2;transform:scale(.8)}100%{opacity:1;transform:scale(1.2)}}
  /* Ocean waves */
  .ocean{position:fixed;bottom:0;left:0;width:100%;height:180px;z-index:1;overflow:hidden}
  .wave{position:absolute;width:200%;height:100%;left:-50%;
    background:repeating-linear-gradient(90deg,
      transparent 0,transparent 40px,
      rgba(30,60,120,.3) 40px,rgba(30,60,120,.3) 80px);
    border-top:3px solid rgba(100,180,255,.25);
  }
  .wave:nth-child(1){bottom:0;background:rgba(10,25,60,.6);animation:drift 8s linear infinite;height:60px;border-top-color:rgba(100,180,255,.15)}
  .wave:nth-child(2){bottom:20px;background:rgba(15,35,80,.4);animation:drift 11s linear infinite reverse;height:50px}
  .wave:nth-child(3){bottom:50px;background:rgba(20,45,100,.25);animation:drift 14s linear infinite;height:40px}
  .wave:nth-child(4){bottom:70px;background:rgba(25,55,120,.15);animation:drift 18s linear infinite reverse;height:35px}
  @keyframes drift{0%{transform:translateX(0)}100%{transform:translateX(50%)}}
  /* Pixel crab */
  .crab-track{position:fixed;bottom:100px;left:0;width:100%;height:40px;z-index:2;pointer-events:none}
  .crab{position:absolute;bottom:0;animation:walk 12s linear infinite;font-size:28px;filter:drop-shadow(0 0 6px rgba(255,100,50,.4))}
  @keyframes walk{
    0%{left:-40px;transform:scaleX(1)}
    49%{left:calc(100% + 10px);transform:scaleX(1)}
    50%{left:calc(100% + 10px);transform:scaleX(-1)}
    99%{left:-40px;transform:scaleX(-1)}
    100%{left:-40px;transform:scaleX(1)}
  }
  .crab-body{animation:scuttle .3s steps(2) infinite}
  @keyframes scuttle{0%{transform:translateY(0)}50%{transform:translateY(-3px)}}
  /* Content */
  .content{position:relative;z-index:3;text-align:center;padding:20px;max-width:600px}
  .code{font-size:72px;color:#ff6b6b;text-shadow:0 0 30px rgba(255,107,107,.4);margin-bottom:12px;
    animation:glow 3s ease-in-out infinite alternate}
  @keyframes glow{0%{text-shadow:0 0 20px rgba(255,107,107,.3)}100%{text-shadow:0 0 40px rgba(255,107,107,.6),0 0 80px rgba(255,107,107,.2)}}
  .title{font-size:18px;color:#ffd93d;margin-bottom:16px;line-height:1.6}
  .subtitle{font-size:10px;color:#8899aa;margin-bottom:40px;line-height:2}
  .island-scene{font-size:48px;margin-bottom:24px;animation:bob 3s ease-in-out infinite}
  @keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
  /* Buttons */
  .actions{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}
  .btn{
    display:inline-flex;align-items:center;gap:8px;
    padding:14px 24px;font-family:'Press Start 2P',monospace;font-size:11px;
    text-decoration:none;border:3px solid;cursor:pointer;
    transition:all .15s;image-rendering:pixelated;
    position:relative;
  }
  .btn:hover{transform:translateY(-3px)}
  .btn:active{transform:translateY(1px)}
  .btn-primary{
    background:#1a5276;color:#ffd93d;border-color:#ffd93d;
    box-shadow:4px 4px 0 #0d2f44, 0 0 20px rgba(255,217,61,.15);
  }
  .btn-primary:hover{background:#1f6f9f;box-shadow:4px 4px 0 #0d2f44, 0 0 30px rgba(255,217,61,.3)}
  .btn-secondary{
    background:transparent;color:#6bb5ff;border-color:#2a4a6a;
    box-shadow:3px 3px 0 #0a1a2a;
  }
  .btn-secondary:hover{border-color:#6bb5ff;box-shadow:3px 3px 0 #0a1a2a, 0 0 15px rgba(107,181,255,.2)}
  /* Pixel divider */
  .divider{margin:24px auto;width:200px;height:4px;
    background:repeating-linear-gradient(90deg,#2a3a5a 0,#2a3a5a 8px,transparent 8px,transparent 16px)}
  /* Responsive */
  @media(max-width:480px){
    .code{font-size:48px}
    .title{font-size:13px}
    .subtitle{font-size:8px}
    .btn{padding:12px 16px;font-size:9px}
    .actions{flex-direction:column;align-items:center}
    .island-scene{font-size:36px}
  }
</style>
</head>
<body>
  <div class="stars" id="stars"></div>
  <div class="ocean">
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
  </div>
  <div class="crab-track"><div class="crab"><span class="crab-body">🦀</span></div></div>
  <div class="content">
    <div class="island-scene">🏝️</div>
    <div class="code">404</div>
    <div class="title">Island Not Found</div>
    <div class="divider"></div>
    <div class="subtitle">This island seems to have drifted away...<br>Maybe it sailed off beyond the horizon.</div>
    <div class="actions">
      <a href="/lobby" class="btn btn-primary">← Back to Lobby</a>
      <a href="/" class="btn btn-secondary">🔍 Explore Islands</a>
    </div>
  </div>
  <script>
    // Generate stars
    (function(){
      var c=document.getElementById('stars');
      for(var i=0;i<60;i++){
        var s=document.createElement('div');
        s.className='star';
        var sz=Math.random()*2+1;
        s.style.cssText='width:'+sz+'px;height:'+sz+'px;top:'+Math.random()*70+'%;left:'+Math.random()*100+'%;animation-delay:'+Math.random()*3+'s;animation-duration:'+(2+Math.random()*3)+'s';
        c.appendChild(s);
      }
    })();
  </script>
</body>
</html>'''

# ── Coin Economy: Tile Costs ──────────────────────────────────
TILE_COSTS = {
    'grass_plain': 2, 'sand_plain': 2, 'dirt_path': 3, 'stone_plain': 5,
    'water_deep': 3, 'tree_oak': 15, 'tree_pine': 15, 'tree_palm': 20,
    'flower_patch': 8, 'rock_big': 10, 'fence_wood': 5, 'sign_wood': 8,
    'bench': 12, 'well': 25, 'campfire': 20, 'lantern': 10, 'mailbox': 15,
    'lighthouse': 40, 'barrel': 8, 'house_cottage': 50,
    'garden_large': 40, 'bridge_wood': 15, 'bridge_wood_large': 30,
    'pond': 35, 'stone_bridge': 30,
    # Previously missing prices
    'chest': 20, 'table_wood': 12, 'gate': 15, 'flower_gate': 18,
    'fountain': 35, 'statue': 30, 'swing': 15, 'treasure_map': 25,
    'dock_plank': 8,
    # Castle theme
    'castle_floor': 5, 'castle_wall': 5, 'castle_carpet': 5,
    'throne': 30, 'torch_wall': 15, 'armor_stand': 25, 'banner_red': 15, 'castle_gate': 30,
    # Indoor theme
    'wood_floor': 3, 'tile_floor': 3, 'carpet_blue': 3,
    'sofa': 20, 'tv': 25, 'bookcase': 15, 'dining_table': 20, 'lamp_floor': 10,
    'window_curtains': 15, 'door_interior': 10,
    # Japanese theme
    'zen_sand': 4, 'moss_stone': 4, 'bamboo_floor': 4,
    'torii_gate': 35, 'stone_lantern': 20, 'bonsai': 15, 'koi_pond': 30, 'bamboo_cluster': 15,
    # Space theme
    'metal_floor': 6, 'space_glass': 6,
    'control_panel': 30, 'antenna': 25, 'space_plant': 20, 'robot': 40,
}

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND= os.path.join(BASE, 'frontend')
CATALOG = os.path.join(BASE, 'catalog')

# ── Crafting Recipes ──────────────────────────────────────────
CRAFTING_RECIPES = [
    {'id': 'golden_tree', 'name': '🌟 Golden Tree', 'ingredients': ['tree_oak', 'lantern'], 'result': 'golden_tree', 'result_name': 'Golden Tree', 'coins_cost': 25},
    {'id': 'enchanted_well', 'name': '✨ Enchanted Well', 'ingredients': ['well', 'flower_patch'], 'result': 'enchanted_well', 'result_name': 'Enchanted Well', 'coins_cost': 30},
    {'id': 'lighthouse_deluxe', 'name': '🏰 Grand Lighthouse', 'ingredients': ['lighthouse', 'campfire'], 'result': 'lighthouse_deluxe', 'result_name': 'Grand Lighthouse', 'coins_cost': 50},
    {'id': 'zen_garden', 'name': '🎋 Zen Garden', 'ingredients': ['bonsai', 'stone_lantern'], 'result': 'zen_garden', 'result_name': 'Zen Garden', 'coins_cost': 35},
    {'id': 'robot_workshop', 'name': '🤖 Robot Workshop', 'ingredients': ['robot', 'control_panel'], 'result': 'robot_workshop', 'result_name': 'Robot Workshop', 'coins_cost': 45},
    {'id': 'fairy_cottage', 'name': '🧚 Fairy Cottage', 'ingredients': ['house_cottage', 'flower_patch'], 'result': 'fairy_cottage', 'result_name': 'Fairy Cottage', 'coins_cost': 40},
    {'id': 'crystal_fountain', 'name': '💎 Crystal Fountain', 'ingredients': ['fountain', 'lantern'], 'result': 'crystal_fountain', 'result_name': 'Crystal Fountain', 'coins_cost': 35},
    {'id': 'pirate_dock', 'name': '🏴\u200d☠️ Pirate Dock', 'ingredients': ['dock_plank', 'barrel'], 'result': 'pirate_dock', 'result_name': 'Pirate Dock', 'coins_cost': 30},
]
WORLDS  = os.path.join(BASE, 'backend', 'worlds')
STATE_F = '/opt/clawverse/state.json'
VISITS_F= os.path.join(BASE, 'backend', 'visits.json')
WORLD_F = os.path.join(WORLDS, 'default.json')

def load_json(path, default=None):
    try:
        with open(path) as f: return json.load(f)
    except: return default if default is not None else {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f: json.dump(data, f, indent=2, ensure_ascii=False)

def no_cache(resp):
    resp.headers['Cache-Control'] = 'no-store, no-cache'
    resp.headers['Pragma'] = 'no-cache'
    return resp

# ── Startup: Load world from SQLite (persistence fix) ─────────
def _init_world_from_db():
    """On startup, load world from SQLite first. Fallback to JSON file, then persist to SQLite."""
    db_world = db.load_world('default')
    if db_world:
        # SQLite has world data — write it to JSON file so all routes see it
        save_json(WORLD_F, db_world)
    else:
        # No world in SQLite yet — load from JSON file and persist to SQLite
        world = load_json(WORLD_F, {})
        if world:
            db.save_world('default', world)

_init_world_from_db()

# ── Eric's admin user ID (his island = 'default') ────────────
ERIC_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@genclawverse.ai')
ERIC_USER_ID = auth.generate_user_id(ERIC_EMAIL)

# ── Owner/Visitor Auth ────────────────────────────────────────
def _get_current_user():
    """Get the currently logged-in user from session cookie. Returns user dict or None."""
    token = request.cookies.get('clawverse_session')
    if not token:
        return None
    return auth.get_session_user(token)

def _get_current_world_id():
    """Get the world ID for the current request context.
    Checks ?world= param first, then falls back to user's own world or 'default'."""
    world_param = request.args.get('world')
    if world_param:
        return world_param
    user = _get_current_user()
    if user:
        # Check if user has their own world
        user_world = db.get_user_world_id(user['id'])
        if user_world:
            return user_world
    return 'default'

def is_owner_request():
    """Return True if the logged-in user owns the current world.
    
    Pure session-based: must be logged in AND own the world being accessed.
    No localhost backdoor — all users must authenticate.
    """
    user = _get_current_user()
    if not user:
        return False
    
    world_id = _req_world_id()
    
    # Check if this user owns the requested world
    owner_id = db.get_world_owner(world_id)
    if owner_id == user['id']:
        return True
    
    return False

def _is_internal_request():
    """Return True if request comes from localhost (for internal API calls only, not user auth)."""
    remote = request.remote_addr or ''
    if remote in ('127.0.0.1', '::1', 'localhost'):
        # But only if NOT proxied from outside (check X-Forwarded-For)
        forwarded = request.headers.get('X-Forwarded-For', '')
        if not forwarded:
            return True
    return False

@app.before_request
def guard_owner_routes():
    """Block write operations from non-owner (visitor) requests."""
    OWNER_ONLY_PATHS = (
        '/api/world/place',
        '/api/world/remove',
        '/api/world/save',
        '/api/world/reset',
        '/api/world/rename',
        '/api/world/theme',  # POST only
        '/api/world/save-as',
        '/api/world/snapshot',
        '/api/ai/generate',
        '/api/island/mood',
    )
    if request.path in OWNER_ONLY_PATHS and request.method == 'POST':
        if not is_owner_request():
            return jsonify({'ok': False, 'error': 'Visitor access denied — read-only mode'}), 403

# ── Auth API Routes ──────────────────────────────────────────
@app.route('/api/auth/request-code', methods=['POST'])
def api_auth_request_code():
    """Send a verification code to the given email."""
    body = request.get_json(silent=True) or {}
    email = (body.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'ok': False, 'error': 'Invalid email'}), 400

    # ── Anti-bot checks ──────────────────────────
    client_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or ''

    # 1. Honeypot: bots fill hidden fields, humans don't
    if not auth.check_honeypot(body):
        # Silent reject — look like success to confuse bots
        return jsonify({'ok': True, 'message': 'Verification code sent!'})

    # 2. Request timing: reject if form submitted in < 2 seconds
    if not auth.check_request_timing(body.get('form_opened_at')):
        return jsonify({'ok': False, 'error': 'Please wait a moment before submitting.'}), 429

    # 3. Cloudflare Turnstile verification
    turnstile_token = body.get('cf_turnstile_response', '')
    if not auth.verify_turnstile(turnstile_token, remote_ip=client_ip):
        return jsonify({'ok': False, 'error': 'Security verification failed. Please try again.'}), 403

    # 4. Per-IP rate limit (10 requests/hour)
    if not auth.check_ip_rate_limit(client_ip):
        return jsonify({'ok': False, 'error': 'Too many requests from this network. Please try later.'}), 429

    # ── Existing checks ──────────────────────────
    # Block fake/test emails
    if not auth.check_email_allowed(email):
        return jsonify({'ok': False, 'error': 'Please use a valid email address.'}), 400
    
    # Per-email rate limit
    if not auth.check_rate_limit(email):
        return jsonify({'ok': False, 'error': 'Too many requests. Please wait a few minutes.'}), 429

    # Record IP request for rate limiting
    auth.record_ip_request(client_ip)
    
    code = auth.generate_code()
    auth.store_verification_code(email, code)
    
    # Send email
    ok, msg = auth.send_verification_email(email, code)
    if not ok:
        return jsonify({'ok': False, 'error': 'Failed to send email. Please try again.'}), 500
    
    return jsonify({'ok': True, 'message': 'Verification code sent!'})

@app.route('/api/auth/verify-code', methods=['POST'])
def api_auth_verify_code():
    """Verify the code and create a session."""
    body = request.get_json(silent=True) or {}
    email = (body.get('email') or '').strip().lower()
    code = (body.get('code') or '').strip()
    
    if not email or not code:
        return jsonify({'ok': False, 'error': 'Email and code required'}), 400
    
    if not auth.verify_code(email, code):
        return jsonify({'ok': False, 'error': 'Invalid or expired code'}), 401
    
    # Get or create user
    user = auth.get_or_create_user(email)
    is_new = user.pop('is_new', False)
    
    # Create session
    token = auth.create_session(user['id'])
    
    # If new user, create their island world
    world_id = user['id']  # use user_id as world_id
    if is_new:
        # Migrate: if this is Eric, link to 'default' world instead of creating new
        if email == ERIC_EMAIL:
            world_id = 'default'
            # Update default world owner
            conn = db.get_conn()
            conn.execute("UPDATE worlds SET owner=? WHERE id='default'", (user['id'],))
            conn.commit()
            conn.close()
        else:
            # Create a fresh island for this user
            _create_new_island(world_id, user['name'], user['id'])
    else:
        # Existing user — find their world
        existing_world = db.get_user_world_id(user['id'])
        if existing_world:
            world_id = existing_world
        elif email == ERIC_EMAIL:
            world_id = 'default'
        else:
            # User exists but has no world (edge case: previous failed registration)
            _create_new_island(world_id, user['name'], user['id'])
    
    resp = make_response(jsonify({
        'ok': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'avatar': user['avatar'],
            'island_name': user.get('island_name', ''),
        },
        'world_id': world_id,
        'is_new': is_new,
    }))
    resp.set_cookie('clawverse_session', token, 
                     max_age=86400*30, httponly=True, samesite='Lax', secure=True)
    return resp

@app.route('/api/auth/me')
def api_auth_me():
    """Get current user info from session cookie."""
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'ok': False, 'logged_in': False}))
    
    world_id = db.get_user_world_id(user['id'])
    if not world_id and user['email'] == ERIC_EMAIL:
        world_id = 'default'
    
    return no_cache(jsonify({
        'ok': True,
        'logged_in': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'avatar': user['avatar'],
            'island_name': user.get('island_name', ''),
        },
        'world_id': world_id or user['id'],
    }))

@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    """Clear session."""
    token = request.cookies.get('clawverse_session')
    if token:
        auth.delete_session(token)
    resp = make_response(jsonify({'ok': True}))
    resp.delete_cookie('clawverse_session')
    return resp

@app.route('/api/auth/update-profile', methods=['POST'])
def api_auth_update_profile():
    """Update user profile (name, avatar, island_name)."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    body = request.get_json(silent=True) or {}
    auth.update_user(user['id'], 
                     name=body.get('name'),
                     avatar=body.get('avatar'),
                     island_name=body.get('island_name'))
    return jsonify({'ok': True})

# ── API Key / Token Settings ─────────────────────────────────
@app.route('/api/settings/apikey', methods=['GET'])
def api_settings_apikey_get():
    """Get API key status (never returns the actual key)."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in', 'has_key': False}), 401
    key = db.get_user_api_key(user['id'])
    provider = db.get_user_api_provider(user['id'])
    usage = db.get_ai_usage(user['id'])
    return no_cache(jsonify({
        'ok': True,
        'has_key': bool(key),
        'provider': provider,
        'usage': usage,
    }))

@app.route('/api/settings/apikey', methods=['POST'])
def api_settings_apikey_set():
    """Store user's API key."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    body = request.get_json(silent=True) or {}
    api_key = (body.get('api_key') or '').strip()
    provider = (body.get('provider') or 'genspark').strip().lower()
    if not api_key:
        return jsonify({'ok': False, 'error': 'api_key is required'}), 400
    if provider not in ('genspark', 'openai'):
        provider = 'genspark'
    db.set_user_api_key(user['id'], api_key, provider)
    return jsonify({'ok': True})

@app.route('/api/settings/apikey', methods=['DELETE'])
def api_settings_apikey_delete():
    """Remove user's API key."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    db.delete_user_api_key(user['id'])
    return jsonify({'ok': True})

@app.route('/api/ai/check', methods=['POST'])
def api_ai_check():
    """Check if user is allowed to make an AI call."""
    user = _get_current_user()
    if not user:
        return jsonify({'allowed': False, 'reason': 'not_logged_in'})
    key = db.get_user_api_key(user['id'])
    if not key:
        return jsonify({'allowed': False, 'reason': 'no_api_key'})
    usage = db.get_ai_usage(user['id'])
    if usage['calls_today'] >= usage['limit']:
        return jsonify({'allowed': False, 'reason': 'rate_limited', 'usage': usage})
    return jsonify({'allowed': True, 'reason': 'ok', 'usage': usage})

@app.route('/api/auth/mode')
def api_auth_mode():
    """Return owner or visitor mode based on session + world context."""
    user = _get_current_user()
    owner = is_owner_request()
    world_id = request.args.get('world', 'default')
    
    result = {
        'mode': 'owner' if owner else 'visitor',
        'is_owner': owner,
        'logged_in': user is not None,
    }
    if user:
        result['user'] = {
            'id': user['id'],
            'name': user['name'],
            'avatar': user['avatar'],
        }
        result['my_world'] = db.get_user_world_id(user['id']) or ('default' if user['email'] == ERIC_EMAIL else None)
    return no_cache(jsonify(result))

def _auto_bio(w):
    """Generate a varied fallback bio from island stats."""
    itype = w.get('island_type', 'farm')
    obj = w.get('objects_placed', 0)
    lvl = w.get('level', 1)
    name = w.get('name', '')
    type_adj = {'farm': 'farm', 'fish': 'ocean', 'mine': 'mountain', 'forest': 'forest'}.get(itype, 'mysterious')

    if obj == 0 and lvl <= 1:
        templates = [
            f"A fresh {type_adj} island waiting to be explored!",
            f"A brand new {type_adj} island. Be the first to visit!",
            f"A blank canvas — this {type_adj} island is just getting started.",
        ]
    elif obj < 10:
        templates = [
            f"A young {type_adj} island with {obj} items placed so far.",
            f"Still early days on this {type_adj} island. {obj} items and growing!",
            f"This {type_adj} island is taking shape — {obj} items and counting.",
        ]
    elif obj < 50:
        templates = [
            f"A cozy {type_adj} island with {obj} items to discover.",
            f"A growing {type_adj} island — {obj} items placed and more to come.",
            f"Explore this {type_adj} island! {obj} items await.",
        ]
    else:
        templates = [
            f"A thriving {type_adj} island with {obj} items. Worth a visit!",
            f"A well-developed {type_adj} island — {obj} items to explore.",
            f"This {type_adj} island is bustling with {obj} items!",
        ]

    # Deterministic pick based on island name hash
    idx = hash(name) % len(templates)
    return templates[idx]

# ── Island Directory API ──────────────────────────────────────
@app.route('/api/islands')
def api_islands_list():
    """List all islands (for the directory/lobby)."""
    sort = request.args.get('sort', 'popular')
    if sort not in ('popular', 'recent', 'rated', 'level', 'trending'):
        sort = 'popular'
    search = request.args.get('search', '').strip()
    island_type = request.args.get('type', '').strip()
    # Allow more results when search/filter is active
    limit = 100 if (search or island_type) else 50
    worlds = db.list_worlds(limit=limit, sort=sort, search=search, island_type=island_type)
    users = {u['id']: u for u in auth.list_users()}
    
    # Bulk-fetch favorite counts and ratings for all islands
    world_ids = [w['id'] for w in worlds]
    fav_counts = db.get_favorite_counts_bulk(world_ids) if world_ids else {}
    rating_data = db.get_rating_counts_bulk(world_ids) if world_ids else {}
    review_data = db.get_average_review_ratings_bulk(world_ids) if world_ids else {}
    
    # If user is authenticated, fetch their favorites for the `favorited` flag
    user = _get_current_user()
    user_favorites = set()
    if user:
        user_favorites = set(db.get_favorites_for_user(user['id']))
    
    # Compute per-island active visitor counts
    _cleanup_stale_sessions()
    _now_presence = time.time()
    _island_visitor_counts = {}
    with _presence_lock:
        for _sid, _sess in _active_sessions.items():
            _wid = _sess.get('world_id', '')
            if _wid and (_now_presence - _sess['ts']) <= 60:
                _island_visitor_counts[_wid] = _island_visitor_counts.get(_wid, 0) + 1

    islands = []
    for w in worlds:
        owner_info = users.get(w['owner'], {})
        rd = rating_data.get(w['id'], {})
        rvd = review_data.get(w['id'], {})
        island_data = {
            'world_id': w['id'],
            'name': w['name'],
            'owner_id': w['owner'],
            'owner_name': owner_info.get('name', 'Anonymous'),
            'owner_avatar': owner_info.get('avatar', '🦞'),
            'visit_count': w.get('visit_count', 0),
            'island_type': w.get('island_type', 'farm'),
            'updated_at': w['updated_at'],
            'created_at': w.get('created_at', ''),
            'level': w.get('level', 1),
            'objects_placed': w.get('objects_placed', 0),
            'bio': (w.get('bio') or _auto_bio(w))[:120],
            'favorite_count': fav_counts.get(w['id'], 0),
            'rating_avg': rd.get('avg', 0.0),
            'rating_count': rd.get('count', 0),
            'review_avg': rvd.get('avg', 0.0),
            'review_count': rvd.get('count', 0),
            'mood': w.get('island_mood') or None,
            'mood_emoji': w.get('island_mood_emoji') or None,
            'welcome_message': w.get('welcome_message') or None,
            'accent_color': w.get('accent_color') or None,
            'announcement': w.get('announcement') or None,
            'unlisted': bool(w.get('unlisted', 0)),
            'active_visitors': _island_visitor_counts.get(w['id'], 0),
            'tags': [t.strip() for t in (w.get('island_tags') or '').split(',') if t.strip()],
        }
        if user:
            island_data['favorited'] = w['id'] in user_favorites
        islands.append(island_data)
    return no_cache(jsonify({'islands': islands, 'total_count': len(islands)}))

# ── Island of the Day ─────────────────────────────────────────
_iotd_cache = {'data': None, 'date': None, 'ts': 0}

@app.route('/api/island-of-the-day')
def api_island_of_the_day():
    """Return the featured Island of the Day — deterministic per UTC date, cached 1 hour."""
    global _iotd_cache
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    now_ts = time.time()
    # Serve from cache if same day and within 1 hour
    if _iotd_cache['data'] and _iotd_cache['date'] == today_str and (now_ts - _iotd_cache['ts']) < 3600:
        return no_cache(jsonify(_iotd_cache['data']))

    # Fetch all worlds
    all_worlds = db.list_worlds(limit=1000, sort='popular')
    users = {u['id']: u for u in auth.list_users()}

    # Eligible: level >= 2 AND visit_count >= 3
    eligible = [w for w in all_worlds if w.get('level', 1) >= 2 and w.get('visit_count', 0) >= 3]

    # Fall back to most-visited if no eligible islands
    if not eligible:
        eligible = sorted(all_worlds, key=lambda w: w.get('visit_count', 0), reverse=True)
    if not eligible:
        return no_cache(jsonify({'ok': False, 'error': 'No islands available'})), 404

    # Deterministic pick via MD5 hash of today's date
    hash_hex = hashlib.md5(today_str.encode()).hexdigest()
    idx = int(hash_hex, 16) % len(eligible)
    w = eligible[idx]

    # Build island data (same shape as /api/islands items)
    owner_info = users.get(w['owner'], {})
    world_ids = [w['id']]
    fav_counts = db.get_favorite_counts_bulk(world_ids)
    rating_data = db.get_rating_counts_bulk(world_ids)
    review_data = db.get_average_review_ratings_bulk(world_ids)
    rd = rating_data.get(w['id'], {})
    rvd = review_data.get(w['id'], {})
    type_emoji_map = {'farm': '🌾', 'fish': '🐟', 'mine': '⛏️', 'forest': '🌲'}
    type_name_map = {'farm': 'Farm', 'fish': 'Fish', 'mine': 'Mine', 'forest': 'Forest'}
    itype = w.get('island_type', 'farm')
    island = {
        'id': w['id'],
        'world_id': w['id'],
        'name': w['name'],
        'owner_id': w['owner'],
        'owner_name': owner_info.get('name', 'Anonymous'),
        'owner_avatar': owner_info.get('avatar', '🦞'),
        'visits': w.get('visit_count', 0),
        'visit_count': w.get('visit_count', 0),
        'island_type': itype,
        'type': itype,
        'type_emoji': type_emoji_map.get(itype, '🏝️'),
        'type_name': type_name_map.get(itype, itype.capitalize()),
        'updated_at': w['updated_at'],
        'created_at': w.get('created_at', ''),
        'level': w.get('level', 1),
        'objects_placed': w.get('objects_placed', 0),
        'bio': (w.get('bio') or _auto_bio(w))[:200],
        'emoji': owner_info.get('avatar', '🏝️'),
        'favorite_count': fav_counts.get(w['id'], 0),
        'rating_avg': rd.get('avg', 0.0),
        'rating_count': rd.get('count', 0),
        'review_avg': rvd.get('avg', 0.0),
        'review_count': rvd.get('count', 0),
        'featured_date': today_str,
        'welcome_message': w.get('welcome_message') or None,
        'accent_color': w.get('accent_color') or None,
        'announcement': w.get('announcement') or None,
        'tags': [t.strip() for t in (w.get('island_tags') or '').split(',') if t.strip()],
    }

    result = {'ok': True, 'island': island}
    _iotd_cache = {'data': result, 'date': today_str, 'ts': now_ts}
    return no_cache(jsonify(result))


@app.route('/api/islands/random')
def api_islands_random():
    """Return a random populated island for the Surprise Me feature."""
    import random
    all_worlds = db.list_worlds(limit=1000, sort='popular')
    eligible = [w for w in all_worlds if w.get('objects_placed', 0) > 0 and not w.get('unlisted', 0)]
    if not eligible:
        return jsonify({'ok': False, 'error': 'No islands available'}), 404
    pick = random.choice(eligible)
    return jsonify({'ok': True, 'island': {'world_id': pick['id'], 'name': pick['name']}})


@app.route('/api/random-island')
def api_random_island():
    """Return a random populated island (at least 1 object, not unlisted)."""
    conn = db.get_conn()
    row = conn.execute(
        "SELECT id, name FROM worlds WHERE COALESCE(unlisted, 0) = 0 AND json_array_length(json_extract(data_json, '$.objects')) > 0 ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'ok': False, 'error': 'No islands available'}), 404
    return jsonify({'ok': True, 'island_id': row['id'], 'url': '/island/' + row['id'], 'name': row['name']})


@app.route('/api/island/<world_id>')
def api_island_world(world_id):
    """Get a specific island's world data."""
    # Resolve name/slug to actual ID
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    world = db.load_world(world_id)
    if not world:
        return jsonify({'ok': False, 'error': 'Island not found'}), 404

    # Consolidated DB fetch for world metadata
    try:
        _meta_conn = db.get_conn()
        _meta_row = _meta_conn.execute(
            "SELECT name, accent_color, announcement, unlisted FROM worlds WHERE id=?",
            (world_id,)
        ).fetchone()
        _meta_conn.close()
    except Exception:
        _meta_row = None

    # Notify island owner about visit (dedup per IP, 10 min cooldown)
    try:
        visitor = _get_current_user()
        visitor_id = visitor['id'] if visitor else None
        owner_id = db.get_world_owner(world_id)
        ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
        if owner_id and owner_id != visitor_id and _should_notify_visit(world_id, ip):
            visitor_name = visitor['name'] if visitor else 'A visitor'
            island_name = _meta_row['name'] if _meta_row and _meta_row['name'] else 'your island'
            db.create_notification(
                owner_id, 'visit',
                f'👀 {visitor_name} visited {island_name}',
                island_id=world_id,
                from_user=visitor_id
            )
    except Exception:
        pass
    # Trigger random island event spawning on visit
    try:
        db.maybe_spawn_event(world_id)
    except Exception:
        pass
    # Track island daily quest progress (visit)
    try:
        from datetime import datetime as _dt, timezone as _tz
        _today = _dt.now(_tz.utc).strftime('%Y-%m-%d')
        _vip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '0.0.0.0'
        db.increment_island_quest_progress(world_id, _today, 'visit', _vip)
    except Exception:
        pass
    # Track visitor achievement: unique island visits
    try:
        _va_user = _get_current_user()
        if _va_user:
            _is_new = db.track_visitor_island_visit(_va_user['id'], world_id)
            if _is_new:
                db.increment_visitor_stat(_va_user['id'], 'islands_visited')
                _check_visitor_achievements(_va_user['id'])
    except Exception:
        pass

    # Inject accent_color from DB column into world data for visitors
    try:
        if _meta_row and _meta_row['accent_color']:
            world['accent_color'] = _meta_row['accent_color']
    except Exception:
        pass

    # Inject announcement from DB column into world data for visitors
    if not is_owner_request():
        try:
            if _meta_row and _meta_row['announcement']:
                world['announcement'] = _meta_row['announcement']
        except Exception:
            pass

    # Inject unlisted flag
    try:
        if _meta_row:
            world['unlisted'] = bool(_meta_row['unlisted'])
    except Exception:
        pass

    # ETag caching for world data
    world_json = json.dumps(world, separators=(',', ':'), sort_keys=True)
    etag = hashlib.md5(world_json.encode()).hexdigest()
    if_none_match = request.headers.get('If-None-Match', '').strip('" ')
    if if_none_match == etag:
        return Response(status=304, headers={'ETag': f'"{etag}"'})

    resp = make_response(world_json)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['ETag'] = f'"{etag}"'
    resp.headers['Cache-Control'] = 'private, must-revalidate'
    return resp

# ── Island Thumbnails ─────────────────────────────────────────
THUMB_DIR = os.path.join(BASE, 'backend', 'thumbnails')
THUMB_CACHE_DIR = os.path.join(BASE, 'backend', 'thumb_cache')
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
THUMB_CACHE_TTL = 86400  # 24 hours — thumbnails regenerated on save

def _invalidate_thumb_cache(world_id):
    """Delete cached thumbnail for a world."""
    for ext in ('png', 'jpg'):
        p = os.path.join(THUMB_CACHE_DIR, f'{world_id}.{ext}')
        if os.path.exists(p):
            try: os.remove(p)
            except OSError: pass

def _regenerate_thumbnail(world_id, world_data=None):
    """Generate and cache thumbnail for a world."""
    try:
        if world_data is None:
            world_data = db.load_world(world_id)
        if not world_data:
            return
        import thumbnail as thumb
        thumb.generate_and_save(world_id, world_data, THUMB_DIR)
        # Copy to cache
        import shutil
        png_path = os.path.join(THUMB_DIR, f'{world_id}.png')
        if os.path.exists(png_path):
            cached = os.path.join(THUMB_CACHE_DIR, f'{world_id}.png')
            shutil.copy2(png_path, cached)
    except Exception as e:
        app.logger.warning(f'Thumbnail regen failed for {world_id}: {e}')

@app.route('/api/island/<world_id>/thumbnail')
def api_island_thumbnail(world_id):
    """Get thumbnail image for an island. Uses server-side cache with 1-hour TTL."""
    # Sanitize world_id
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)

    def _thumb_response(file_path, mimetype):
        """Wrap send_file with Cache-Control and ETag headers."""
        etag = hashlib.md5(f'{world_id}:{os.path.getmtime(file_path)}'.encode()).hexdigest()[:16]
        # Check If-None-Match for 304 Not Modified
        if_none_match = request.headers.get('If-None-Match', '').strip('"')
        if if_none_match and if_none_match == etag:
            return '', 304
        response = send_file(file_path, mimetype=mimetype, max_age=THUMB_CACHE_TTL)
        response.headers['Cache-Control'] = f'public, max-age={THUMB_CACHE_TTL}'
        response.headers['ETag'] = f'"{etag}"'
        return response

    # Check cache first (any format)
    for ext, mime in (('jpg', 'image/jpeg'), ('png', 'image/png')):
        cached = os.path.join(THUMB_CACHE_DIR, f'{world_id}.{ext}')
        if os.path.exists(cached):
            age = time.time() - os.path.getmtime(cached)
            if age < THUMB_CACHE_TTL:
                return _thumb_response(cached, mime)

    # Prefer real screenshot (JPG)
    jpg_path = os.path.join(THUMB_DIR, f'{world_id}.jpg')
    if os.path.exists(jpg_path):
        # Copy to cache
        import shutil
        cached_jpg = os.path.join(THUMB_CACHE_DIR, f'{world_id}.jpg')
        shutil.copy2(jpg_path, cached_jpg)
        return _thumb_response(cached_jpg, 'image/jpeg')

    # Fall back to generated PNG in thumbnails dir
    png_path = os.path.join(THUMB_DIR, f'{world_id}.png')
    if os.path.exists(png_path):
        import shutil
        cached_png = os.path.join(THUMB_CACHE_DIR, f'{world_id}.png')
        shutil.copy2(png_path, cached_png)
        return _thumb_response(cached_png, 'image/png')

    # Generate on-the-fly if nothing exists
    import thumbnail as thumb
    world_data = db.load_world(world_id)
    if not world_data:
        return 'Not found', 404
    thumb.generate_and_save(world_id, world_data, THUMB_DIR)
    # Cache the generated thumbnail
    cached_png = os.path.join(THUMB_CACHE_DIR, f'{world_id}.png')
    import shutil
    shutil.copy2(png_path, cached_png)
    return _thumb_response(cached_png, 'image/png')

@app.route('/api/island/<world_id>/thumbnail/invalidate', methods=['POST'])
def api_island_thumbnail_invalidate(world_id):
    """Invalidate cached thumbnail for a world."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    _invalidate_thumb_cache(world_id)
    return jsonify({'ok': True})

# ── Island Stats API ───────────────────────────────────────────

@app.route('/api/island/<world_id>/stats')
def api_island_stats(world_id):
    """Get aggregated stats for an island (public, no auth)."""
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved

    conn = db.get_conn()

    # Core world + progress data
    row = conn.execute("""
        SELECT w.id, w.name, w.created_at, w.island_type,
               COALESCE(p.level, 1) as level,
               COALESCE(p.xp, 0) as xp,
               COALESCE(p.objects_placed, 0) as objects_placed,
               COALESCE(p.tiles_placed, 0) as tiles_placed,
               COALESCE(p.total_earned, 0) as total_earned
        FROM worlds w
        LEFT JOIN user_progress p ON p.world_id = w.id
        WHERE w.id = ?
    """, (world_id,)).fetchone()

    if not row:
        conn.close()
        return jsonify({'ok': False, 'error': 'Island not found'}), 404

    stats = {
        'visit_count': 0,
        'guestbook_count': 0,
        'level': row['level'],
        'xp': row['xp'],
        'objects_placed': row['objects_placed'],
        'terrain_tiles': row['tiles_placed'],
        'favorite_count': 0,
        'created_at': row['created_at'] or '',
        'age_days': 0,
        'island_type': row['island_type'] or 'farm',
        'events_total': 0,
        'coins_earned': row['total_earned'],
        'achievements_count': 0,
    }

    # Age in days
    try:
        if row['created_at']:
            from datetime import datetime as _dt
            created = _dt.fromisoformat(row['created_at'].replace('Z', '+00:00'))
            now = _dt.now(timezone.utc)
            stats['age_days'] = max(0, (now - created).days)
    except Exception:
        pass

    # Visit count (page_views + visits)
    try:
        pv = conn.execute("SELECT COUNT(*) as cnt FROM page_views WHERE world_id=?", (world_id,)).fetchone()
        v = conn.execute("SELECT COUNT(*) as cnt FROM visits WHERE world_id=?", (world_id,)).fetchone()
        stats['visit_count'] = (pv['cnt'] if pv else 0) + (v['cnt'] if v else 0)
    except Exception:
        pass

    # Guestbook count
    try:
        gb = conn.execute("SELECT COUNT(*) as cnt FROM guestbook WHERE world_id=?", (world_id,)).fetchone()
        stats['guestbook_count'] = gb['cnt'] if gb else 0
    except Exception:
        pass

    # Favorites count
    try:
        fav = conn.execute("SELECT COUNT(*) as cnt FROM island_favorites WHERE island_id=?", (world_id,)).fetchone()
        stats['favorite_count'] = fav['cnt'] if fav else 0
    except Exception:
        pass

    # Island events total
    try:
        ev = conn.execute("SELECT COUNT(*) as cnt FROM island_events WHERE world_id=?", (world_id,)).fetchone()
        stats['events_total'] = ev['cnt'] if ev else 0
    except Exception:
        pass

    # Achievements count (from achievements_v2 table)
    try:
        ach = conn.execute("SELECT COUNT(*) as cnt FROM achievements_v2 WHERE world_id=?", (world_id,)).fetchone()
        stats['achievements_count'] = ach['cnt'] if ach else 0
    except Exception:
        # Fallback: count from JSON in user_progress
        try:
            aj = conn.execute("SELECT achievements_json FROM user_progress WHERE world_id=?", (world_id,)).fetchone()
            if aj and aj['achievements_json']:
                import json as _json
                stats['achievements_count'] = len(_json.loads(aj['achievements_json'] or '[]'))
        except Exception:
            pass

    conn.close()
    return no_cache(jsonify({'ok': True, 'stats': stats}))

# ── Similar Islands API ─────────────────────────────────────────

@app.route('/api/island/<world_id>/similar')
def api_island_similar(world_id):
    """Get islands of the same type as the given island, for recommendations."""
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    islands = db.get_similar_islands(world_id, limit=4)
    return no_cache(jsonify({'ok': True, 'islands': islands}))


# ── Recent Visitors API ────────────────────────────────────────

@app.route('/api/island/<world_id>/recent-visitors')
def api_island_recent_visitors(world_id):
    """Get the last 8 unique visitors (deduplicated by from_name) for an island."""
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved

    conn = db.get_conn()
    try:
        # Get recent visits, ordered by most recent first
        # Use a subquery to get the latest visit per unique from_name
        rows = conn.execute("""
            SELECT v.emoji, v.from_name, v.ts
            FROM visits v
            INNER JOIN (
                SELECT from_name, MAX(ts) as max_ts
                FROM visits
                WHERE world_id = ? AND from_name != '' AND from_name != 'Anonymous'
                GROUP BY from_name
            ) latest ON v.from_name = latest.from_name AND v.ts = latest.max_ts
            WHERE v.world_id = ?
            ORDER BY v.ts DESC
            LIMIT 8
        """, (world_id, world_id)).fetchall()

        # Also get total visitor count
        count_row = conn.execute(
            "SELECT COUNT(DISTINCT from_name) as cnt FROM visits WHERE world_id = ? AND from_name != '' AND from_name != 'Anonymous'",
            (world_id,)
        ).fetchone()
        visitor_count = count_row['cnt'] if count_row else 0
    except Exception:
        rows = []
        visitor_count = 0
    finally:
        conn.close()

    now = time.time()
    visitors = []
    for r in rows:
        ts = r['ts'] or 0
        diff = now - ts
        if diff < 60:
            relative_time = 'just now'
        elif diff < 3600:
            mins = int(diff / 60)
            relative_time = f'{mins}m ago'
        elif diff < 86400:
            hours = int(diff / 3600)
            relative_time = f'{hours}h ago'
        elif diff < 604800:
            days = int(diff / 86400)
            relative_time = f'{days}d ago'
        else:
            relative_time = 'long ago'

        visitors.append({
            'emoji': html_module.escape(str(r['emoji'] or '🦞')),
            'from_name': html_module.escape(str(r['from_name'] or 'Visitor')),
            'relative_time': relative_time,
            'ts': ts,
        })

    return no_cache(jsonify({
        'ok': True,
        'visitors': visitors,
        'visitor_count': visitor_count,
    }))

# ── Island Activity Feed API ──────────────────────────────────

_island_feed_cache = {}  # world_id -> {'data': [...], 'ts': float}

@app.route('/api/island/<world_id>/activity-feed')
def api_island_activity_feed(world_id):
    """Public activity feed for an island — interesting events only."""
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved

    now = time.time()
    cached = _island_feed_cache.get(world_id)
    if cached and now - cached['ts'] < 30:
        return no_cache(jsonify({'ok': True, 'events': cached['data']}))

    INTERESTING = {'harvest', 'level_up', 'ranch_collect', 'steal', 'guestbook', 'gift', 'mass_steal', 'ranch_place'}
    all_events = db.get_feed_events(world_id, 80)
    events = [e for e in all_events if e.get('event_type') in INTERESTING][:15]

    # Add relative time
    for e in events:
        ts = e.get('ts') or 0
        diff = now - ts
        if diff < 60:
            e['relative_time'] = 'just now'
        elif diff < 3600:
            e['relative_time'] = f'{int(diff/60)}m ago'
        elif diff < 86400:
            e['relative_time'] = f'{int(diff/3600)}h ago'
        elif diff < 604800:
            e['relative_time'] = f'{int(diff/86400)}d ago'
        else:
            e['relative_time'] = 'long ago'

    _island_feed_cache[world_id] = {'data': events, 'ts': now}
    return no_cache(jsonify({'ok': True, 'events': events}))

# ── Guestbook API ─────────────────────────────────────────────

@app.route('/api/island/<world_id>/guestbook', methods=['GET'])
def api_island_guestbook_get(world_id):
    """Get guestbook entries for an island (public, no auth)."""
    limit = min(int(request.args.get('limit', 20)), 50)
    offset = max(int(request.args.get('offset', 0)), 0)
    entries = db.get_guestbook(world_id, limit=limit, offset=offset)
    total = db.get_guestbook_count(world_id)
    return no_cache(jsonify({'entries': entries, 'total': total}))

@app.route('/api/island/<world_id>/guestbook', methods=['POST'])
def api_island_guestbook_post(world_id):
    """Post a guestbook message on an island (no auth, rate-limited by IP)."""
    body = request.get_json(silent=True) or {}
    name = (body.get('name') or 'Visitor').strip()
    message = (body.get('message') or '').strip()
    avatar = (body.get('avatar') or '🦞').strip()

    # Validate name
    if not name or len(name) > 30:
        return jsonify({'ok': False, 'error': 'Name must be 1-30 characters'}), 400
    # Validate message
    if not message or len(message) < 1 or len(message) > 200:
        return jsonify({'ok': False, 'error': 'Message must be 1-200 characters'}), 400

    # Rate limit: 1 message per IP per island per 5 minutes
    ip_raw = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]

    conn = db.get_conn()
    recent = conn.execute(
        "SELECT id FROM guestbook WHERE world_id=? AND ip_hash=? AND created_at > datetime('now', '-5 minutes')",
        (world_id, ip_hash)
    ).fetchone()
    conn.close()
    if recent:
        return jsonify({'ok': False, 'error': 'Please wait a few minutes before posting again'}), 429

    entry = db.add_guestbook_entry(world_id, name, message, author_avatar=avatar, ip_hash=ip_hash)
    # Timed event: visitor_festival gives +2 coins per guestbook post
    _gb_event_bonus = 0
    try:
        _gb_conn = db.get_conn()
        _gb_evt = db.get_active_timed_event(_gb_conn, world_id)
        if _gb_evt and _gb_evt['event_type'] == 'visitor_festival':
            db.earn_coins(world_id, 2, 'visitor_festival_guestbook')
            db.increment_timed_event_participants(_gb_conn, _gb_evt['id'])
            _gb_event_bonus = 2
        _gb_conn.close()
    except Exception:
        pass
    # Daily quest: credit the poster if authenticated
    try:
        poster_wid = _req_world_id()
        if poster_wid:
            db.advance_quest(poster_wid, 'leave_guestbook')
    except Exception:
        pass
    # Track island daily quest progress (guestbook)
    try:
        from datetime import datetime as _dt, timezone as _tz
        _today = _dt.now(_tz.utc).strftime('%Y-%m-%d')
        _gip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '0.0.0.0'
        db.increment_island_quest_progress(world_id, _today, 'guestbook', _gip)
    except Exception:
        pass
    # Notify island owner about new guestbook message
    try:
        owner_id = db.get_world_owner(world_id)
        poster = _get_current_user()
        poster_id = poster['id'] if poster else None
        # Don't notify yourself
        if owner_id and owner_id != poster_id:
            conn_tmp = db.get_conn()
            wname = conn_tmp.execute("SELECT name FROM worlds WHERE id=?", (world_id,)).fetchone()
            conn_tmp.close()
            island_name = wname['name'] if wname else 'your island'
            db.create_notification(
                owner_id, 'guestbook',
                f'📝 {name} left a guestbook message on {island_name}',
                island_id=world_id,
                from_user=poster_id
            )
            _notify_owner(owner_id, 'guestbook', '📝 New guestbook message!', f'{name} wrote on {island_name}: "{message[:60]}"', world_id)
    except Exception:
        pass
    # Visitor achievement: guestbook_posts
    _va_new_achievements = []
    try:
        _va_poster = _get_current_user()
        if _va_poster:
            db.increment_visitor_stat(_va_poster['id'], 'guestbook_posts')
            _va_new_achievements = _check_visitor_achievements(_va_poster['id'])
    except Exception:
        pass
    # Strip ip_hash from response
    resp = {'ok': True, 'entry': {
        'id': entry['id'],
        'author_name': entry['author_name'],
        'author_avatar': entry['author_avatar'],
        'message': entry['message'],
        'created_at': entry['created_at'],
    }}
    if _va_new_achievements:
        resp['new_achievements'] = _va_new_achievements
    return jsonify(resp)

# ── World creation helper ─────────────────────────────────────
def _create_new_island(world_id, owner_name, owner_id):
    """Create a fresh world for a new user. Style is randomly picked based on their ID."""
    import random as rnd
    rnd.seed(hash(world_id))

    SIZE = 32
    CX, CY = 15, 15

    # Pick a random world style based on user ID hash
    STYLES = [
        {'name': 'Island',     'ground': 'grass_plain',  'accent': 'flowers_wild',  'border': 'water_deep',  'shore': 'sand_plain',    'trees': ['tree_oak','tree_pine'],   'extra': ['flower_patch','bench','well']},
        {'name': 'Zen Garden', 'ground': 'grass_cherry', 'accent': 'zen_sand',      'border': 'water_deep',  'shore': 'sand_plain',    'trees': ['tree_pine','bamboo_cluster'], 'extra': ['bonsai','stone_lantern','torii_gate','koi_pond']},
        {'name': 'Castle',     'ground': 'stone_plain',  'accent': 'castle_carpet',  'border': 'water_deep', 'shore': 'castle_wall',   'trees': ['tree_oak'],              'extra': ['throne','torch_wall','banner_red','armor_stand']},
        {'name': 'Space Base', 'ground': 'metal_floor',  'accent': 'space_glass',    'border': 'water_deep', 'shore': 'tile_floor',    'trees': ['space_plant'],           'extra': ['robot','control_panel','antenna','lamp_floor']},
        {'name': 'Beach',      'ground': 'sand_plain',   'accent': 'sand_shells',    'border': 'water_deep', 'shore': 'water_shallow', 'trees': ['tree_palm'],             'extra': ['campfire','barrel','lighthouse','bench']},
        {'name': 'Forest',     'ground': 'grass_dark',   'accent': 'moss_stone',     'border': 'water_deep', 'shore': 'grass_plain',   'trees': ['tree_oak','tree_pine'],  'extra': ['campfire','rock_big','well','flower_patch']},
        {'name': 'Autumn Park','ground': 'grass_autumn',  'accent': 'dirt_path',     'border': 'water_deep', 'shore': 'sand_plain',    'trees': ['tree_oak'],              'extra': ['bench','lantern','fountain','sign_wood']},
    ]
    style = rnd.choice(STYLES)

    def island_dist(col, row):
        base = math.sqrt((col - CX)**2 + (row - CY)**2)
        angle = math.atan2(row - CY, col - CX)
        wobble = 1.8 * math.sin(3 * angle + 0.3 + hash(world_id) % 10 * 0.3)
        wobble += 0.9 * math.sin(5 * angle + 1.2 + hash(world_id) % 7 * 0.2)
        wobble += 0.5 * math.sin(7 * angle + 2.1)
        return base - wobble * 0.55

    terrain = []
    for row in range(SIZE):
        for col in range(SIZE):
            d = island_dist(col, row)
            r = rnd.random()
            if d > 13:
                t = style['border']
            elif d > 11.5:
                t = style['shore']
            elif d > 10:
                t = style['ground'] if r > 0.2 else style['accent']
            else:
                if r < 0.12: t = style['accent']
                elif r < 0.2: t = 'dirt_path'
                else: t = style['ground']
            terrain.append([col, row, 0, t])

    # Starter objects based on style
    objects = [
        {'id': 'starter_house', 'type': 'house_cottage', 'col': 14, 'row': 13, 'z': 1},
    ]
    # Add trees
    tree_positions = [(10,11),(18,10),(11,16),(19,14),(10,14)]
    for i, (c, r) in enumerate(tree_positions[:3]):
        objects.append({'id': f'starter_tree{i}', 'type': rnd.choice(style['trees']), 'col': c, 'row': r, 'z': 1})
    # Add style-specific extras
    extra_positions = [(16,16),(12,12),(18,17),(13,18),(17,12)]
    for i, obj_type in enumerate(style['extra'][:4]):
        c, r = extra_positions[i]
        objects.append({'id': f'starter_extra{i}', 'type': obj_type, 'col': c, 'row': r, 'z': 1})
    # Always add a sign and campfire
    objects.append({'id': 'starter_sign', 'type': 'sign_wood', 'col': 15, 'row': 18, 'z': 1})
    objects.append({'id': 'starter_fire', 'type': 'campfire', 'col': 15, 'row': 15, 'z': 1})

    # Generate a fun random world name
    _adjectives = [
        'Cozy','Tiny','Misty','Sunny','Starlit','Hidden','Dreamy','Crystal',
        'Golden','Mossy','Whispering','Floating','Enchanted','Twilight','Coral',
        'Cosmic','Wandering','Sleepy','Jolly','Wild','Luminous','Frosty',
        'Ancient','Mystic','Electric','Peaceful','Bubbly','Crimson','Velvet',
        'Midnight','Amber','Silver','Rustic','Neon','Phantom','Lucky',
    ]
    _nouns = {
        'Island': ['Cove','Bay','Reef','Atoll','Lagoon','Shore','Harbor','Tide Pool'],
        'Zen Garden': ['Temple','Shrine','Teahouse','Bamboo Grove','Koi Pond','Pagoda'],
        'Castle': ['Fortress','Citadel','Keep','Stronghold','Tower','Kingdom','Dungeon'],
        'Space Base': ['Station','Outpost','Colony','Nebula','Orbit','Galaxy','Starport'],
        'Beach': ['Paradise','Oasis','Sandbar','Pier','Driftwood Bay','Surf Spot','Tiki Bar'],
        'Forest': ['Hollow','Glade','Thicket','Canopy','Treehouse','Grove','Wildwood'],
        'Autumn Park': ['Garden','Meadow','Courtyard','Terrace','Promenade','Gazebo'],
    }
    adj = rnd.choice(_adjectives)
    noun = rnd.choice(_nouns.get(style['name'], ['World']))
    world_name = f"{adj} {noun}"
    world = {
        'meta': {'name': world_name, 'size': [SIZE, SIZE]},
        'terrain': terrain,
        'objects': objects,
        'agent': {'col': 14, 'row': 15, 'direction': 'front', 'action': 'idle'},
    }

    # Save to JSON file and DB
    world_file = os.path.join(WORLDS, f'{world_id}.json')
    save_json(world_file, world)
    db.save_world(world_id, world, owner_id=owner_id)

    # Initialize progress for this world
    db.ensure_progress(world_id)

    # Welcome gift: 2 attack tokens + 2 raid tokens + 1 shield
    db.add_token(world_id, 'attack', 2)
    db.add_token(world_id, 'raid', 2)
    db.add_shield(world_id, 1)

    return world

@app.route('/api/presence', methods=['GET'])
def api_presence():
    """Return current active visitor count."""
    _cleanup_stale_sessions()
    with _presence_lock:
        total = len(_active_sessions)
        visitors = sum(1 for v in _active_sessions.values() if not v.get('is_owner'))
        owners = sum(1 for v in _active_sessions.values() if v.get('is_owner'))
    return no_cache(jsonify({'total': total, 'visitors': visitors, 'owners': owners}))

@app.route('/api/presence/ping', methods=['POST'])
def api_presence_ping():
    """Heartbeat to keep presence alive."""
    body = request.get_json(silent=True) or {}
    session_id = body.get('session_id', request.remote_addr)
    world_id = body.get('world_id', '')
    owner = is_owner_request()
    user = _get_current_user()
    name = user['name'] if user else 'Visitor'
    avatar = user['avatar'] if user else '🦞'
    with _presence_lock:
        _active_sessions[session_id] = {
            'ts': time.time(), 'is_owner': owner,
            'world_id': world_id, 'name': name, 'avatar': avatar,
        }
    _cleanup_stale_sessions()
    with _presence_lock:
        visitors = sum(1 for v in _active_sessions.values() if not v.get('is_owner'))
    return jsonify({'ok': True, 'visitors': visitors})

@app.route('/api/island/<world_id>/presence')
def api_island_presence(world_id):
    """Get per-island presence: who's currently viewing this island."""
    _cleanup_stale_sessions()
    now = time.time()
    with _presence_lock:
        visitors = []
        for sid, sess in _active_sessions.items():
            if sess.get('world_id') == world_id and (now - sess['ts']) <= 60:
                visitors.append({
                    'name': sess.get('name', 'Visitor'),
                    'avatar': sess.get('avatar', '🦞'),
                    'session_id_short': sid[:6],
                })
    return no_cache(jsonify({
        'visitors': visitors[:20],
        'count': len(visitors),
    }))

@app.route('/api/events')
def api_events():
    """SSE stream for real-time world updates."""
    q = queue.Queue(maxsize=50)
    with _world_event_queues_lock:
        _world_event_queues.append(q)

    def generate():
        # Send initial connected event
        yield f"data: {json.dumps({'type': 'connected', 'ts': time.time()})}\n\n"
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    # Send keepalive
                    yield f": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            with _world_event_queues_lock:
                if q in _world_event_queues:
                    _world_event_queues.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'}
    )

# ── Real-time Presence & SSE ─────────────────────────────────
# Simple in-memory presence tracking
_presence_lock = threading.Lock()
_active_sessions = {}  # session_id → {ts, is_owner, name, avatar, from_island}
_world_event_queues = []  # list of queues for SSE subscribers
_world_event_queues_lock = threading.Lock()

# ── Travel Sessions (cross-island ghost visitors) ──────────────
_traveler_sessions = {}  # session_id → {ts, name, avatar, from_island, col, row}
_traveler_lock = threading.Lock()

def _cleanup_stale_travelers():
    now = time.time()
    with _traveler_lock:
        stale = [k for k, v in _traveler_sessions.items() if now - v['ts'] > 120]  # 2min timeout
        for k in stale:
            del _traveler_sessions[k]

def _cleanup_stale_sessions():
    now = time.time()
    with _presence_lock:
        stale = [k for k, v in _active_sessions.items() if now - v['ts'] > 60]
        for k in stale:
            del _active_sessions[k]

def _broadcast_world_event(event_type, data):
    """Broadcast a world change event to all SSE subscribers."""
    msg = json.dumps({'type': event_type, 'data': data, 'ts': time.time()})
    with _world_event_queues_lock:
        dead = []
        for q in _world_event_queues:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            _world_event_queues.remove(q)

# ── Serve frontend ────────────────────────────────────────────
@app.route('/')
def index():
    """Root: show the universe lobby (all islands)."""
    return send_file(os.path.join(FRONTEND, 'lobby.html'))

@app.route('/island/<world_id>')
def island_view(world_id):
    """Serve the island page for any world (including other users' islands)."""
    import html as html_mod

    # Resolve slug/name to actual world ID
    resolved = db.resolve_world_id(world_id)
    if resolved and resolved != world_id:
        # Redirect to canonical URL with the real world ID
        return redirect(f'/island/{resolved}', code=301)

    # Check if world exists at all
    if not resolved:
        # World not found — show 404 page
        return PAGE_404, 404

    html_path = os.path.join(FRONTEND, 'index.html')
    html_content = open(html_path, 'r').read()

    try:
        conn = db.get_conn()
        row = conn.execute('''
            SELECT w.name, w.owner, w.island_type,
                   COALESCE(up.level, 1) as level,
                   COALESCE(up.objects_placed, 0) as objects,
                   COALESCE(s.bio, '') as bio,
                   COALESCE(i.avatar, '🦞') as avatar
            FROM worlds w
            LEFT JOIN user_progress up ON w.id = up.world_id
            LEFT JOIN island_story s ON w.id = s.world_id
            LEFT JOIN islands i ON w.id = i.id
            WHERE w.id = ?
        ''', (world_id,)).fetchone()

        if row:
            name = row[0] or 'Unnamed Island'
            owner = row[1] or 'Anonymous'
            itype = row[2] or 'farm'
            level = row[3]
            objects = row[4]
            bio = row[5]

            # Try to get a better owner name from users table
            owner_row = conn.execute('SELECT name FROM users WHERE id = ?', (owner,)).fetchone()
            if owner_row and owner_row[0]:
                owner = owner_row[0]

            if not bio:
                bio = f"A {itype} island by {owner} \u2022 Level {level} \u2022 {objects} objects \u2022 Come explore!"

            name_esc = html_mod.escape(name)
            bio_esc = html_mod.escape(bio)
            base = "https://ysnlpjle.gensparkclaw.com"

            og_tags = (
                f'<meta property="og:title" content="{name_esc} \u2014 Clawverse">\n'
                f'<meta property="og:description" content="{bio_esc}">\n'
                f'<meta property="og:image" content="{base}/api/island/{world_id}/thumbnail">\n'
                f'<meta property="og:url" content="{base}/island/{world_id}">\n'
                f'<meta property="og:type" content="website">\n'
                f'<meta property="og:site_name" content="Clawverse">\n'
                f'<meta name="twitter:card" content="summary_large_image">\n'
                f'<meta name="twitter:title" content="{name_esc} \u2014 Clawverse">\n'
                f'<meta name="twitter:description" content="{bio_esc}">\n'
                f'<meta name="twitter:image" content="{base}/api/island/{world_id}/thumbnail">'
            )

            html_content = html_content.replace(
                '<title>🦞 Clawverse</title>',
                f'<title>🦞 {name_esc} \u2014 Clawverse</title>'
            )
            html_content = html_content.replace(
                '<meta charset="UTF-8">',
                f'<meta charset="UTF-8">\n{og_tags}'
            )
    except Exception:
        pass  # Serve without OG tags on error

    resp = make_response(html_content)
    resp.headers['Content-Type'] = 'text/html'
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp

@app.route('/lobby')
def lobby_view():
    """Alias for root — the universe lobby."""
    return send_file(os.path.join(FRONTEND, 'lobby.html'))

@app.route('/catalog/<path:f>')
def serve_catalog(f):
    return send_from_directory(CATALOG, f)

@app.route('/assets/<path:f>')
def serve_assets(f):
    return send_from_directory(os.path.join(FRONTEND, 'assets'), f)

@app.route('/lobster_<direction>.png')
def serve_lobster_sprite(direction):
    if direction in ('front', 'back', 'left', 'right'):
        return send_from_directory(FRONTEND, f'lobster_{direction}.png')
    return 'Not found', 404

@app.route('/manifest.json')
def manifest():
    return send_file(os.path.join(FRONTEND, 'manifest.json'))

@app.route('/i18n.js')
def i18n_js():
    return send_file(os.path.join(FRONTEND, 'i18n.js'))


@app.route('/favicon.ico')
def favicon():
    """Serve favicon — return 204 since HTML already has inline SVG favicon."""
    return '', 204

# ── robots.txt & sitemap.xml ─────────────────────────────────
_BASE_URL = 'https://ysnlpjle.gensparkclaw.com'
_sitemap_cache = {'xml': None, 'ts': 0}

@app.route('/robots.txt')
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {_BASE_URL}/sitemap.xml\n"
    )
    return Response(body, mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    now = time.time()
    if _sitemap_cache['xml'] and now - _sitemap_cache['ts'] < 3600:
        return Response(_sitemap_cache['xml'], mimetype='application/xml')

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '  <url>',
        f'    <loc>{_BASE_URL}/</loc>',
        '    <changefreq>daily</changefreq>',
        '    <priority>1.0</priority>',
        '  </url>',
        '  <url>',
        f'    <loc>{_BASE_URL}/map</loc>',
        '    <changefreq>daily</changefreq>',
        '    <priority>0.7</priority>',
        '  </url>',
    ]

    try:
        conn = db.get_conn()
        rows = conn.execute('SELECT id, updated_at FROM worlds').fetchall()
        for row in rows:
            world_id = row[0] if isinstance(row, (list, tuple)) else row['id']
            updated_at = row[1] if isinstance(row, (list, tuple)) else row['updated_at']
            lastmod = ''
            if updated_at:
                if isinstance(updated_at, str):
                    lastmod = updated_at[:10]
                else:
                    lastmod = str(updated_at)[:10]
            lines.append('  <url>')
            lines.append(f'    <loc>{_BASE_URL}/island/{world_id}</loc>')
            if lastmod:
                lines.append(f'    <lastmod>{lastmod}</lastmod>')
            lines.append('    <changefreq>weekly</changefreq>')
            lines.append('    <priority>0.8</priority>')
            lines.append('  </url>')
    except Exception:
        pass

    lines.append('</urlset>')
    xml = '\n'.join(lines)
    _sitemap_cache['xml'] = xml
    _sitemap_cache['ts'] = now
    return Response(xml, mimetype='application/xml')

# ── RSS Feed ─────────────────────────────────────────────────
_rss_cache = {'xml': None, 'ts': 0}

@app.route('/rss.xml')
def rss_xml():
    """RSS 2.0 feed of recent Clawverse islands."""
    from email.utils import formatdate
    from calendar import timegm

    now = time.time()
    if _rss_cache['xml'] and now - _rss_cache['ts'] < 300:
        return Response(_rss_cache['xml'],
                        content_type='application/rss+xml; charset=utf-8')

    items_xml = []
    try:
        worlds = db.list_worlds(sort='recent', limit=20)
        for w in worlds:
            wid = w.get('id', '')
            name = html_module.escape(w.get('name', 'Unnamed Island'))
            bio = html_module.escape(w.get('bio', '') or '')
            itype = html_module.escape(w.get('island_type', '') or '')
            level = w.get('level', 1)
            owner = html_module.escape(w.get('owner_name', '') or '')
            link = f'{_BASE_URL}/island/{wid}'

            desc_parts = []
            if bio:
                desc_parts.append(bio)
            if itype:
                desc_parts.append(f'Type: {itype}')
            desc_parts.append(f'Level: {level}')
            if owner:
                desc_parts.append(f'Owner: {owner}')
            description = html_module.escape(' | '.join(desc_parts))

            # Build RFC 822 pubDate from created_at
            pub_date = ''
            created = w.get('created_at')
            if created:
                try:
                    if isinstance(created, str):
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    else:
                        dt = created
                    pub_date = formatdate(timegm(dt.timetuple()), usegmt=True)
                except Exception:
                    pass

            item = (
                '    <item>\n'
                f'      <title>{name}</title>\n'
                f'      <link>{link}</link>\n'
                f'      <description>{description}</description>\n'
                f'      <guid isPermaLink="true">{link}</guid>\n'
            )
            if pub_date:
                item += f'      <pubDate>{pub_date}</pubDate>\n'
            item += '    </item>'
            items_xml.append(item)
    except Exception:
        pass

    build_date = formatdate(usegmt=True)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        '    <title>Clawverse — Island Universe</title>\n'
        f'    <link>{_BASE_URL}</link>\n'
        '    <description>Latest islands and activity in the Clawverse</description>\n'
        '    <language>en</language>\n'
        f'    <lastBuildDate>{build_date}</lastBuildDate>\n'
        + '\n'.join(items_xml) + '\n'
        '  </channel>\n'
        '</rss>'
    )

    _rss_cache['xml'] = xml
    _rss_cache['ts'] = now
    return Response(xml, content_type='application/rss+xml; charset=utf-8')

# ── Catalog API ───────────────────────────────────────────────
@app.route('/api/catalog')
def api_catalog():
    data = load_json(os.path.join(CATALOG, 'catalog.json'), {'terrain':[], 'objects':[]})
    # Inject coin costs into each tile
    for t in data.get('terrain', []):
        t['cost'] = TILE_COSTS.get(t.get('id', ''), 5)
    for o in data.get('objects', []):
        if o.get('ai_generated'):
            o['cost'] = 20  # AI creations cost 20 coins
        else:
            o['cost'] = TILE_COSTS.get(o.get('id', ''), 5)
        # Expose size field (from footprint, default [1,1])
        if 'size' not in o:
            o['size'] = o.get('footprint', [1, 1])
    return no_cache(jsonify(data))

@app.route('/api/catalog/ai')
def api_catalog_ai():
    catalog = load_json(os.path.join(CATALOG, 'catalog.json'), {'terrain':[], 'objects':[]})
    ai_tiles = [o for o in catalog['objects'] if o.get('ai_generated')]
    return no_cache(jsonify({'tiles': ai_tiles, 'count': len(ai_tiles)}))

# ── World API ─────────────────────────────────────────────────
def _req_world_id():
    """Get the world_id from the current request context.
    Checks: POST body 'world', query param 'world', or defaults to 'default'."""
    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        if 'world' in body:
            return body['world']
    return request.args.get('world', 'default')

def _resolve_world_file(world_id='default'):
    """Get the JSON file path for a world."""
    if world_id == 'default':
        return WORLD_F
    return os.path.join(WORLDS, f'{world_id}.json')

def _load_world_data(world_id='default'):
    """Load world data — try DB first (with name resolution), then JSON file."""
    # Try resolving name/slug to actual ID
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    data = db.load_world(world_id)
    if data:
        return data
    return load_json(_resolve_world_file(world_id), {})

def _save_world_data(world_id, data):
    """Save world data and regenerate thumbnail."""
    save_json(_resolve_world_file(world_id), data)
    owner_id = db.get_world_owner(world_id)
    db.save_world(world_id, data, owner_id=owner_id)
    # Pre-generate thumbnail instead of just invalidating
    _regenerate_thumbnail(world_id, data)

@app.route('/api/world')
def api_world():
    world_id = request.args.get('world', 'default')
    # Resolve name/slug to actual ID and pass it in the response
    resolved = db.resolve_world_id(world_id)
    actual_id = resolved or world_id
    world = _load_world_data(world_id)
    if not world:
        return jsonify({'ok': False, 'error': 'World not found'}), 404
    # Include resolved world_id so frontend can sync
    if actual_id != world_id:
        world['_resolved_world_id'] = actual_id
    return no_cache(jsonify(world))

@app.route('/api/world/place', methods=['POST'])
def api_place():
    body = request.get_json(silent=True) or {}
    world_id = body.get('world', request.args.get('world', 'default'))
    world = _load_world_data(world_id)
    layer = body.get('layer', 'terrain')
    col, row, z = int(body.get('col',0)), int(body.get('row',0)), int(body.get('z',0))
    tile_type = body.get('type','')

    if layer == 'terrain':
        # Remove existing tile at same col,row,z
        world['terrain'] = [t for t in world.get('terrain',[])
                            if not (t[0]==col and t[1]==row and t[2]==z)]
        world['terrain'].append([col, row, z, tile_type])
    elif layer == 'object':
        obj_id = f"obj_{datetime.now(timezone.utc).strftime('%f')}"
        obj_entry = {'id': obj_id, 'type': tile_type, 'col': col, 'row': row, 'z': z}
        # Lookup footprint/size from catalog for multi-tile objects
        catalog_data = load_json(os.path.join(CATALOG, 'catalog.json'), {'terrain':[], 'objects':[]})
        cat_obj = next((o for o in catalog_data.get('objects', []) if o['id'] == tile_type), None)
        fp = [1, 1]
        if cat_obj:
            fp = cat_obj.get('footprint', cat_obj.get('size', [1, 1]))
            if fp and (fp[0] > 1 or fp[1] > 1):
                obj_entry['size'] = fp

        # ── Sprint 19: Collision detection ──
        # Check all tiles the new object would cover
        terrain_map = {(t[0], t[1]): t for t in world.get('terrain', [])}
        existing_objs = world.get('objects', [])
        for dc in range(fp[0]):
            for dr in range(fp[1]):
                tc, tr = col + dc, row + dr
                # Can't place on water
                t = terrain_map.get((tc, tr))
                if t and t[3].startswith('water'):
                    return jsonify({'ok': False, 'error': 'Cannot place on water'}), 400
                # Can't place on occupied tile (check multi-tile overlap)
                for o in existing_objs:
                    os_fp = o.get('size', [1, 1])
                    if tc >= o['col'] and tc < o['col'] + os_fp[0] and tr >= o['row'] and tr < o['row'] + os_fp[1]:
                        return jsonify({'ok': False, 'error': 'Tile occupied'}), 400

        world.setdefault('objects',[]).append(obj_entry)

    _save_world_data(world_id, world)
    _broadcast_world_event('tile_placed', {'layer': layer, 'col': col, 'row': row, 'type': tile_type})
    if layer == 'object':
        db.advance_quest(world_id, 'place_object')
        try: db.update_challenge_progress(world_id, 'place_objects')
        except Exception: pass
        # Track discovery in collection book
        if tile_type:
            try: db.discover_object(world_id, tile_type)
            except Exception: pass
    return jsonify({'ok': True})

@app.route('/api/world/remove', methods=['POST'])
def api_remove():
    body = request.get_json(silent=True) or {}
    world_id = body.get('world', request.args.get('world', 'default'))
    world = _load_world_data(world_id)
    layer = body.get('layer', 'terrain')
    col, row, z = int(body.get('col',0)), int(body.get('row',0)), int(body.get('z',0))

    if layer == 'terrain':
        # Remove top-most tile at col,row (or exact z if specified)
        if z == -1:  # remove top
            tiles_here = [t for t in world.get('terrain',[]) if t[0]==col and t[1]==row]
            if tiles_here:
                top = max(tiles_here, key=lambda t: t[2])
                world['terrain'] = [t for t in world['terrain'] if t != top]
        else:
            world['terrain'] = [t for t in world.get('terrain',[])
                                if not (t[0]==col and t[1]==row and t[2]==z)]
    elif layer == 'object':
        obj_id = body.get('id')
        if obj_id:
            world['objects'] = [o for o in world.get('objects',[]) if o['id'] != obj_id]
        else:
            # Remove topmost object at col,row
            objs_here = [o for o in world.get('objects',[]) if o['col']==col and o['row']==row]
            if objs_here:
                top = max(objs_here, key=lambda o: o.get('z',1))
                world['objects'] = [o for o in world['objects'] if o['id'] != top['id']]

    _save_world_data(world_id, world)
    return jsonify({'ok': True})

@app.route('/api/world/save', methods=['POST'])
def api_world_save():
    body = request.get_json(silent=True) or {}
    world_id = body.get('world', request.args.get('world', 'default'))
    existing = _load_world_data(world_id)
    if 'terrain' in body: existing['terrain'] = body['terrain']
    if 'objects' in body: existing['objects'] = body['objects']
    if 'agent'   in body: existing['agent']   = body['agent']
    if 'meta'    in body: existing['meta'].update(body['meta'])
    _save_world_data(world_id, existing)
    return jsonify({'ok': True})

@app.route('/api/world/reset', methods=['POST'])
def api_world_reset():
    """Generate a fresh 32x32 island world with varied terrain and save it."""
    import math, random as rnd
    body = request.get_json(silent=True) or {}
    seed = body.get('seed', 42)
    rnd.seed(seed)

    SIZE = 32
    CX, CY = 15, 15   # island center

    # Multi-octave island shape function
    def island_dist(col, row):
        base = math.sqrt((col - CX)**2 + (row - CY)**2)
        angle = math.atan2(row - CY, col - CX)
        # Multiple wobble harmonics for organic coastline
        wobble  = 1.8 * math.sin(3 * angle + 0.3)
        wobble += 0.9 * math.sin(5 * angle + 1.2)
        wobble += 0.5 * math.sin(7 * angle + 2.1)
        wobble += 0.3 * math.sin(11 * angle + 0.8)
        return base - wobble * 0.55

    # Small noise function for micro terrain variety
    def micro_noise(col, row, s=1):
        return math.sin(col * 0.7 * s + row * 0.5 * s) * 0.5 + math.cos(col * 0.4 * s - row * 0.6 * s) * 0.3

    terrain = []
    terrain_map = {}  # for quick lookup

    for row in range(SIZE):
        for col in range(SIZE):
            d = island_dist(col, row)
            mn = micro_noise(col, row)
            r = rnd.random()

            if d > 10.5:
                tile = 'water_deep'
            elif d > 9.0:
                tile = 'water_shallow' if r < 0.7 else 'water_deep'
            elif d > 7.8:
                tile = 'water_shallow'
            elif d > 6.8:
                tile = 'sand_plain'
            elif d > 5.8:
                # Shoreline with shells
                tile = 'sand_shells' if r < 0.35 else 'sand_plain'
            elif d > 4.8:
                # Inner shore - mix sand and grass
                if r < 0.15: tile = 'sand_shells'
                elif r < 0.35: tile = 'sand_plain'
                else: tile = 'grass_plain'
            elif d > 2.5:
                # Main island — rich variety
                if r < 0.10 + mn * 0.05: tile = 'grass_flowers'
                elif r < 0.18: tile = 'grass_dark'
                elif r < 0.22: tile = 'stone_plain'
                elif r < 0.25 and d > 3.5: tile = 'grass_plain'
                else: tile = 'grass_plain'
            else:
                # Interior center — village area, paths
                if r < 0.14: tile = 'dirt_path'
                elif r < 0.20: tile = 'stone_plain'
                elif r < 0.25: tile = 'grass_dark'
                else: tile = 'grass_plain'

            terrain.append([col, row, 0, tile])
            terrain_map[(col, row)] = tile

    # Add a winding dirt path from center to shore (NE direction)
    path_cols = [(CX, CY), (CX+1, CY+1), (CX+2, CY+1), (CX+3, CY+2),
                 (CX+4, CY+3), (CX+4, CY+4), (CX+5, CY+4)]
    for (pc, pr) in path_cols:
        if 0 <= pc < SIZE and 0 <= pr < SIZE:
            terrain = [[c,r,z,t] if not (c==pc and r==pr and z==0) else [c,r,z,'dirt_path']
                       for [c,r,z,t] in terrain]

    # Starter objects — a charming village
    def oid(name): return f'starter_{name}'
    objects = [
        {'id': oid('house'),    'type': 'house_cottage', 'col': CX,     'row': CY-2,  'z': 1},
        {'id': oid('tree1'),    'type': 'tree_oak',      'col': CX-3,   'row': CY-1,  'z': 1},
        {'id': oid('tree2'),    'type': 'tree_pine',     'col': CX-2,   'row': CY+2,  'z': 1},
        {'id': oid('tree3'),    'type': 'tree_oak',      'col': CX+3,   'row': CY-3,  'z': 1},
        {'id': oid('campfire'), 'type': 'campfire',      'col': CX+2,   'row': CY+1,  'z': 1},
        {'id': oid('mailbox'),  'type': 'mailbox',       'col': CX+1,   'row': CY-3,  'z': 1},
        {'id': oid('lantern'),  'type': 'lantern',       'col': CX-1,   'row': CY-3,  'z': 1},
        {'id': oid('bench'),    'type': 'bench',         'col': CX+3,   'row': CY-1,  'z': 1},
        {'id': oid('well'),     'type': 'well',          'col': CX-4,   'row': CY+1,  'z': 1},
        {'id': oid('flower1'),  'type': 'flower_patch',  'col': CX-2,   'row': CY-4,  'z': 1},
        {'id': oid('flower2'),  'type': 'flower_patch',  'col': CX+4,   'row': CY-2,  'z': 1},
        {'id': oid('rock1'),    'type': 'stone_boulder', 'col': CX-5,   'row': CY+3,  'z': 1},
    ]

    world = {
        'meta': {
            'name': 'My World',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'seed': seed,
        },
        'terrain': terrain,
        'objects': objects,
    }
    world_id = body.get('world', request.args.get('world', 'default'))
    _save_world_data(world_id, world)
    return jsonify({'ok': True, 'terrain_count': len(terrain), 'object_count': len(objects)})

@app.route('/api/world/rename', methods=['POST'])
def api_world_rename():
    body = request.get_json(silent=True) or {}
    name = body.get('name', 'My World')[:40]
    world_id = body.get('world', request.args.get('world', 'default'))
    world = _load_world_data(world_id)
    world.setdefault('meta', {})['name'] = name
    _save_world_data(world_id, world)
    return jsonify({'ok': True, 'name': name})

# ── Status API ────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
    world_id = request.args.get('world', 'default')
    # Only show real claw status on the default (Eric's) island
    if world_id == 'default':
        data = load_json(STATE_F, {'state':'idle','detail':''})
        return no_cache(jsonify({
            'state':  data.get('state','idle'),
            'detail': data.get('detail',''),
            'achievements_unlocked': len(db.get_achievements_v2(world_id)),
        }))
    else:
        # Other users' worlds show neutral idle status
        return no_cache(jsonify({
            'state': 'idle',
            'detail': '',
            'achievements_unlocked': len(db.get_achievements_v2(world_id)),
        }))

# ── Visits API ────────────────────────────────────────────────
@app.route('/api/visits')
def api_visits():
    visits = db.get_visits(_req_world_id(), limit=50)
    # Sort ascending for display
    visits_asc = sorted(visits, key=lambda v: v.get('ts', 0))
    return no_cache(jsonify({'visits': visits_asc}))

@app.route('/api/visit', methods=['POST'])
def api_visit():
    body     = request.get_json(silent=True) or {}
    emoji    = html_module.escape(body.get('emoji','❓'))[:10]  # escape HTML + limit length
    from_url = body.get('from_url', '')
    from_name= html_module.escape(body.get('from_name', 'Anonymous'))[:50]  # escape + limit
    message  = html_module.escape(body.get('message', ''))[:200]  # escape + cap at 200 chars

    # Rate limit: max 1 same emoji per 30s
    now = datetime.now(timezone.utc).timestamp()
    recent_visits = db.get_visits(_req_world_id(), limit=10)
    recent = [v for v in recent_visits if v.get('emoji')==emoji and (now - v.get('ts',0)) < 30]
    if recent:
        return jsonify({'ok': False, 'msg': 'too soon'}), 429

    db.add_visit(_req_world_id(), emoji, from_url, from_name, now, message=message)
    # Award XP for receiving a visit
    db.record_progress_event(_req_world_id(), 'receive_visit')
    _check_achievements(_req_world_id())
    return jsonify({'ok': True})

@app.route('/api/pageview', methods=['POST'])
def api_pageview():
    """Record a passive page view (no emoji required)."""
    body = request.get_json(silent=True) or {}
    world_id = body.get('world_id') or _req_world_id()
    ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
    db.record_page_view(world_id, ip)
    # Auto-stamp passport for logged-in visitors visiting other islands
    passport_result = None
    user = _get_current_user()
    if user:
        user_own_world = db.get_user_world_id(user['id'])
        if user_own_world != world_id:  # Don't stamp your own island
            try:
                conn = db.get_conn()
                row = conn.execute("SELECT name, owner FROM worlds WHERE id=?", (world_id,)).fetchone()
                conn.close()
                if row:
                    island_name = row['name'] or world_id
                    prog = db.get_user_progress(world_id)
                    level = prog.get('level', 1) if prog else 1
                    passport_result = db.stamp_passport(user['id'], world_id, island_name=island_name, island_avatar='🦞', island_level=level)
            except Exception:
                pass
    resp = {'ok': True}
    if passport_result and passport_result.get('new'):
        resp['passport_stamp'] = {'new': True, 'total': passport_result.get('total_stamps', 0), 'island_name': passport_result.get('island_name', '')}
    return jsonify(resp)

# ── Local state (for set_state.py compatibility) ──────────────
@app.route('/status')
def local_status():
    return no_cache(jsonify(load_json(STATE_F, {'state':'idle','detail':''})))

@app.route('/state', methods=['POST'])
def set_state():
    body = request.get_json(silent=True) or {}
    data = load_json(STATE_F, {})
    data.update({'state': body.get('state','idle'), 'detail': body.get('detail',''),
                 'updated_at': datetime.now(timezone.utc).isoformat()})
    save_json(STATE_F, data)
    return jsonify({'ok': True})

# ── AI Tile Generation ────────────────────────────────────────
AI_GEN_STATUS = {}  # job_id → {status, tile_id, error}

def _run_ai_generate(job_id, description, tile_id, category, out_path):
    """Background: call gsk img, post-process, register in catalog."""
    try:
        AI_GEN_STATUS[job_id] = {'status': 'generating', 'tile_id': tile_id}

        # Check gsk availability upfront
        import shutil as _shutil
        if not _shutil.which('gsk'):
            raise Exception('gsk CLI not available')

        prompt = (
            f"pixel art isometric game sprite, {description}, "
            "Animal Crossing style, cute chibi, clean pixel art, "
            "white background, single object, centered, no shadow, "
            "consistent lighting top-left, 1px dark outline"
        )
        tmp_path = out_path.replace('.png', '_raw.png')

        try:
            result = subprocess.run(
                ['gsk', 'img', prompt, '-r', '1:1', '-o', tmp_path],
                capture_output=True, text=True, timeout=120
            )
        except subprocess.TimeoutExpired:
            raise Exception('gsk img timed out after 120s')

        if not os.path.exists(tmp_path):
            stderr_snippet = (result.stderr or '').strip()[:300]
            raise Exception(
                f"Image not created by gsk. stderr: {stderr_snippet}" if stderr_snippet
                else "Image not created by gsk (no output file, no stderr)"
            )

        # Convert: remove white bg, resize to 128x128, save as PNG
        try:
            subprocess.run([
                'convert', tmp_path,
                '-fuzz', '12%', '-transparent', 'white',
                '-resize', '128x128',
                out_path
            ], check=True, capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            raise Exception('ImageMagick convert timed out after 30s')
        except subprocess.CalledProcessError as e:
            raise Exception(f'ImageMagick convert failed: {(e.stderr or b"").decode()[:200]}')

        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        # Register in catalog
        catalog_path = os.path.join(CATALOG, 'catalog.json')
        catalog = load_json(catalog_path, {'terrain':[], 'objects':[]})

        # Remove existing entry with same id
        catalog['objects'] = [o for o in catalog['objects'] if o['id'] != tile_id]
        catalog['objects'].append({
            'id': tile_id,
            'name': description[:30].title(),
            'category': category,
            'file': f'objects/{tile_id}.png',
            'footprint': [1,1],
            'walkable': False,
            'ai_generated': True,
            'prompt': description,
        })
        save_json(catalog_path, catalog)

        AI_GEN_STATUS[job_id] = {'status': 'done', 'tile_id': tile_id, 'file': f'objects/{tile_id}.png'}

    except Exception as e:
        AI_GEN_STATUS[job_id] = {'status': 'error', 'tile_id': tile_id, 'error': str(e)}

# ── Multi-World API (BE-03) ───────────────────────────────────
@app.route('/api/worlds')
def api_worlds_list():
    """List all saved worlds."""
    worlds = []
    for fname in sorted(os.listdir(WORLDS)):
        if not fname.endswith('.json'):
            continue
        world_id = fname[:-5]
        data = load_json(os.path.join(WORLDS, fname), {})
        worlds.append({
            'id': world_id,
            'name': data.get('meta', {}).get('name', world_id),
            'terrain_count': len(data.get('terrain', [])),
            'object_count': len(data.get('objects', [])),
            'created_at': data.get('meta', {}).get('created_at', ''),
        })
    return no_cache(jsonify({'worlds': worlds, 'count': len(worlds)}))

@app.route('/api/world/<world_id>/load', methods=['POST'])
def api_world_load(world_id):
    """Copy a named world to default.json (make it current)."""
    world_id = re.sub(r'[^a-z0-9_\-]', '', world_id)
    data = db.load_world(world_id)
    if not data:
        path = os.path.join(WORLDS, f'{world_id}.json')
        if not os.path.exists(path):
            return jsonify({'ok': False, 'error': f'World {world_id!r} not found'}), 404
        data = load_json(path, {})
    return jsonify({
        'ok': True,
        'world_id': world_id,
        'name': data.get('meta', {}).get('name', world_id),
        'terrain_count': len(data.get('terrain', [])),
        'object_count': len(data.get('objects', [])),
    })

@app.route('/api/world/save-as', methods=['POST'])
def api_world_save_as():
    """Save current world with a custom world_id (filename)."""
    body = request.get_json(silent=True) or {}
    world_id = re.sub(r'[^a-z0-9_\-]', '_', body.get('world_id', 'untitled').lower())[:32]
    if not world_id:
        return jsonify({'ok': False, 'error': 'world_id required'}), 400
    world = _load_world_data(_req_world_id())
    name = body.get('name', world_id)
    world.setdefault('meta', {})['name'] = name
    world['meta']['saved_as'] = world_id
    path = os.path.join(WORLDS, f'{world_id}.json')
    save_json(path, world)
    _save_world_data(_req_world_id(), world)
    return jsonify({'ok': True, 'world_id': world_id, 'name': name})

# ── Custom Catalog API (BE-05) ────────────────────────────────
@app.route('/api/catalog/custom')
def api_catalog_custom():
    """List only AI-generated / custom tiles."""
    catalog = load_json(os.path.join(CATALOG, 'catalog.json'), {'terrain':[], 'objects':[]})
    custom_terrain = [t for t in catalog['terrain'] if t.get('ai_generated') or t.get('custom')]
    custom_objects  = [o for o in catalog['objects'] if o.get('ai_generated') or o.get('custom')]
    return no_cache(jsonify({
        'terrain': custom_terrain,
        'objects': custom_objects,
        'count': len(custom_terrain) + len(custom_objects),
    }))

VALID_CATEGORIES = {'terrain', 'object', 'structure', 'nature', 'furniture', 'custom', 'decoration', 'water', 'path'}

@app.route('/api/ai/categories')
def api_ai_categories():
    """Return available AI generation categories."""
    return jsonify({'categories': sorted(VALID_CATEGORIES)})

@app.route('/api/ai/generate', methods=['POST'])
def api_ai_generate():
    body = request.get_json(silent=True) or {}
    description = body.get('description', '').strip()
    if not description:
        return jsonify({'ok': False, 'error': 'description is required — describe what tile you want to create'}), 400
    if len(description) < 3:
        return jsonify({'ok': False, 'error': 'description too short — try something like "a mossy stone ruin"'}), 400
    if len(description) > 200:
        return jsonify({'ok': False, 'error': 'description too long (max 200 chars)'}), 400
    
    # Validate and sanitize category
    category = body.get('category', 'custom').lower().strip()
    if category not in VALID_CATEGORIES:
        category = 'custom'
    
    # Sanitize tile_id
    tile_id = 'ai_' + re.sub(r'[^a-z0-9]', '_', description.lower())[:24] + '_' + \
              datetime.now(timezone.utc).strftime('%H%M%S')
    out_path  = os.path.join(CATALOG, 'objects', f'{tile_id}.png')
    job_id    = tile_id
    
    AI_GEN_STATUS[job_id] = {
        'status': 'queued',
        'tile_id': tile_id,
        'description': description,
        'category': category,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    t = threading.Thread(target=_run_ai_generate, 
                         args=(job_id, description, tile_id, category, out_path), daemon=True)
    t.start()
    
    return jsonify({'ok': True, 'job_id': job_id, 'tile_id': tile_id, 'category': category})

@app.route('/api/ai/status/<job_id>')
def api_ai_status(job_id):
    status = AI_GEN_STATUS.get(job_id, {'status': 'unknown'})
    return no_cache(jsonify(status))

# ── Dashboard API ─────────────────────────────────────────────
PROGRESS_DIR = os.path.join(BASE, 'progress')

@app.route('/dashboard')
def dashboard():
    return send_file(os.path.join(FRONTEND, 'dashboard.html'))

@app.route('/dashboard/data')
def dashboard_data():
    import subprocess as sp

    # Only source of truth: shared_state.json
    shared_state_path = '/home/azureuser/ai-team/shared_state.json'
    sprint_tasks = []
    sprint_goal = ''
    sprint_id = ''
    try:
        ss = load_json(shared_state_path, {})
        sprint_tasks = ss.get('sprint', {}).get('tasks', [])
        sprint_goal  = ss.get('sprint', {}).get('goal', '')
        sprint_id    = ss.get('sprint', {}).get('id', '')
        recent_log   = ss.get('log', [])[-10:]
    except:
        recent_log = []

    # Build tasks display
    task_lines = [f"## 🏃 Sprint: {sprint_id}\n### {sprint_goal}\n"]
    status_icon = {'done':'✅','in_progress':'🔄','pending':'⏳','failed':'❌'}
    done_count = 0
    for t in sprint_tasks:
        icon = status_icon.get(t.get('status',''), '❓')
        if t.get('status') == 'done': done_count += 1
        task_lines.append(f"{icon} **{t['id']}** [{t.get('status','')}] — {t['title']}")
        if t.get('result'): task_lines.append(f"   → {t['result'][:100]}")
    
    total = len(sprint_tasks)
    task_lines.insert(1, f"**Progress: {done_count}/{total}**\n")
    
    if recent_log:
        task_lines.append(f"\n**Recent activity:**")
        for entry in recent_log[-5:]:
            task_lines.append(f"- `{entry.get('at','')[-8:]}` {entry.get('event','')} {entry.get('task_id','')}")
    
    tasks = '\n'.join(task_lines)
    progress = {}  # No longer reading stale progress/*.md files

    # World stats
    world = _load_world_data(_req_world_id())
    catalog = load_json(os.path.join(CATALOG,'catalog.json'), {'terrain':[],'objects':[]})
    # Only show real claw state on default (Eric's) island
    wid = _req_world_id()
    if wid == 'default':
        state = load_json(STATE_F, {'state':'idle','detail':''})
    else:
        state = {'state':'idle','detail':''}

    # Backend uptime check
    uptime = ''
    try:
        r = sp.run(['ps','-o','etime=','-p', str(os.getpid())], capture_output=True, text=True)
        uptime = r.stdout.strip()
    except: pass

    return no_cache(jsonify({
        'progress': progress,
        'tasks': tasks,
        'final_report': '',
        'world': {
            'name': world.get('meta',{}).get('name','?'),
            'terrain': len(world.get('terrain',[])),
            'objects': len(world.get('objects',[])),
        },
        'catalog': {
            'terrain': len(catalog['terrain']),
            'objects': len(catalog['objects']),
        },
        'agent_state': state,
        'uptime': uptime,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }))

# ── Social: Island Registry ───────────────────────────────────
ISLANDS_F = os.path.join(BASE, 'backend', 'islands.json')

def load_islands():
    return load_json(ISLANDS_F, {'islands': []})

def save_islands(data):
    save_json(ISLANDS_F, data)

# ── Island Favorites ────────────────────────────────────────────

@app.route('/api/favorites/toggle', methods=['POST'])
def api_favorite_toggle():
    data = request.get_json() or {}
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    user_id = user['id']
    island_id = data.get('island_id', '').strip()
    if not island_id:
        return jsonify({'error': 'island_id required'}), 400
    result = db.toggle_favorite(user_id, island_id)
    # Notify island owner when someone favorites (not unfavorites)
    try:
        if result.get('favorited'):
            owner_id = db.get_world_owner(island_id)
            if owner_id and owner_id != user_id:
                conn_tmp = db.get_conn()
                wname = conn_tmp.execute("SELECT name FROM worlds WHERE id=?", (island_id,)).fetchone()
                conn_tmp.close()
                island_name = wname['name'] if wname else 'your island'
                user_name = user.get('name', 'Someone')
                db.create_notification(
                    owner_id, 'favorite',
                    f'⭐ {user_name} favorited {island_name}',
                    island_id=island_id,
                    from_user=user_id
                )
    except Exception:
        pass
    return jsonify(result)

@app.route('/api/favorites')
def api_favorites_list():
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'favorites': [], 'count': 0}))
    favorites = db.get_favorites_for_user(user['id'])
    return no_cache(jsonify({'favorites': favorites, 'count': len(favorites)}))

@app.route('/api/favorites/details')
def api_favorites_details():
    """Return full island data for user's favorited islands."""
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'islands': []}))
    fav_ids = db.get_favorites_for_user(user['id'])
    if not fav_ids:
        return no_cache(jsonify({'islands': []}))
    conn = db.get_conn()
    islands = []
    for wid in fav_ids[:20]:  # max 20
        row = conn.execute("SELECT * FROM worlds WHERE id=?", (wid,)).fetchone()
        if row:
            prog = conn.execute("SELECT level, xp FROM user_progress WHERE world_id=?", (wid,)).fetchone()
            isl = conn.execute("SELECT name, owner, avatar FROM islands WHERE id=?", (wid,)).fetchone()
            name = isl['name'] if isl else row['name']
            owner_name = isl['owner'] if isl else row['owner']
            avatar = isl['avatar'] if isl else '🦞'
            level = prog['level'] if prog else 1
            data = json.loads(row['data_json']) if row['data_json'] else {}
            obj_count = len(data.get('objects', {}))
            islands.append({
                'world_id': wid,
                'name': name or wid,
                'owner_name': owner_name or 'Anonymous',
                'owner_avatar': avatar,
                'level': level,
                'objects_placed': obj_count
            })
    conn.close()
    return no_cache(jsonify({'islands': islands}))

@app.route('/api/island/<world_id>/favorite-count')
def api_island_favorite_count(world_id):
    """Get favorite/follower count for a specific island."""
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    count = db.get_favorite_count(world_id)
    # Also check if current user has favorited
    user = _get_current_user()
    favorited = False
    if user:
        favs = db.get_favorites_for_user(user['id'])
        favorited = world_id in favs
    return no_cache(jsonify({'count': count, 'favorited': favorited}))

@app.route('/api/island/<world_id>/favorite', methods=['POST'])
def api_toggle_favorite(world_id):
    """Toggle favorite for an island. Requires login."""
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    result = db.toggle_favorite(user['id'], world_id)
    is_fav = result.get('favorited', False)
    count = result.get('count', 0)
    # Notify island owner when someone favorites (not unfavorites)
    try:
        if is_fav:
            owner_id = db.get_world_owner(world_id)
            if owner_id and owner_id != user['id']:
                conn_tmp = db.get_conn()
                wname = conn_tmp.execute("SELECT name FROM worlds WHERE id=?", (world_id,)).fetchone()
                conn_tmp.close()
                island_name = wname['name'] if wname else 'your island'
                user_name = user.get('name', 'Someone')
                db.create_notification(
                    owner_id, 'favorite',
                    f'⭐ {user_name} favorited {island_name}',
                    island_id=world_id,
                    from_user=user['id']
                )
    except Exception:
        pass
    return jsonify({'favorited': is_fav, 'count': count})

@app.route('/api/island/<world_id>/favorite', methods=['GET'])
def api_get_favorite_status(world_id):
    """Get favorite status and count for an island."""
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    user = _get_current_user()
    is_fav = db.is_favorited(user['id'], world_id) if user else False
    count = db.get_favorite_count(world_id)
    return no_cache(jsonify({'favorited': is_fav, 'count': count}))

# ── Island Follows ──────────────────────────────────────────────

# ── Island Passport ──────────────────────────────────────────
@app.route('/api/passport')
def api_passport():
    """Get the current user's island passport (collected stamps)."""
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'ok': False, 'stamps': [], 'total': 0}))
    stamps = db.get_passport(user['id'], limit=100)
    total = db.get_passport_count(user['id'])
    return no_cache(jsonify({'ok': True, 'stamps': stamps, 'total': total}))

@app.route('/api/passport/count')
def api_passport_count():
    """Get just the stamp count for the current user."""
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'count': 0}))
    count = db.get_passport_count(user['id'])
    return no_cache(jsonify({'count': count}))

@app.route('/api/me/recently-visited')
def api_my_recently_visited():
    """Get the current user's recently visited islands."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'islands': []}), 401

    recent_ids = db.get_recently_visited(user['id'], limit=8)
    if not recent_ids:
        return jsonify({'ok': True, 'islands': []})

    # Fetch basic island info for each
    users_map = {u['id']: u for u in auth.list_users()}
    islands = []
    for island_id in recent_ids:
        conn = db.get_conn()
        row = conn.execute("SELECT id, name, owner, island_type, level FROM worlds w LEFT JOIN user_progress p ON w.id = p.world_id WHERE w.id=?", (island_id,)).fetchone()
        conn.close()
        if row:
            owner_info = users_map.get(row['owner'], {})
            islands.append({
                'world_id': row['id'],
                'name': row['name'],
                'owner_name': owner_info.get('name', 'Anonymous'),
                'island_type': row['island_type'] or 'farm',
                'level': row['level'] if row['level'] is not None else 1,
            })
    return no_cache(jsonify({'ok': True, 'islands': islands}))


@app.route('/api/follows/toggle', methods=['POST'])
def api_follow_toggle():
    data = request.get_json() or {}
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'Login required'}), 401
    user_id = user['id']
    island_id = data.get('island_id', '').strip()
    if not island_id:
        return jsonify({'error': 'island_id required'}), 400
    result = db.toggle_follow(user_id, island_id)
    # Notify island owner when someone follows (not unfollows)
    try:
        if result.get('following'):
            owner_id = db.get_world_owner(island_id)
            if owner_id and owner_id != user_id:
                conn_tmp = db.get_conn()
                wname = conn_tmp.execute("SELECT name FROM worlds WHERE id=?", (island_id,)).fetchone()
                conn_tmp.close()
                island_name = wname['name'] if wname else 'your island'
                user_name = user.get('name', 'Someone')
                db.create_notification(
                    owner_id, 'follow',
                    f'👥 {user_name} followed {island_name}',
                    island_id=island_id,
                    from_user=user_id
                )
    except Exception:
        pass
    return jsonify(result)

@app.route('/api/follows')
def api_follows_list():
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'follows': [], 'count': 0}))
    follows = db.get_user_follows(user['id'])
    return no_cache(jsonify({'follows': follows, 'count': len(follows)}))

@app.route('/api/follows/details')
def api_follows_details():
    """Return full island data for user's followed islands."""
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'islands': []}))
    follow_ids = db.get_user_follows(user['id'])
    if not follow_ids:
        return no_cache(jsonify({'islands': []}))
    conn = db.get_conn()
    islands = []
    for wid in follow_ids[:20]:  # max 20
        row = conn.execute("SELECT * FROM worlds WHERE id=?", (wid,)).fetchone()
        if row:
            prog = conn.execute("SELECT level, xp FROM user_progress WHERE world_id=?", (wid,)).fetchone()
            isl = conn.execute("SELECT name, owner, avatar FROM islands WHERE id=?", (wid,)).fetchone()
            name = isl['name'] if isl else row['name']
            owner_name = isl['owner'] if isl else row['owner']
            avatar = isl['avatar'] if isl else '🦞'
            level = prog['level'] if prog else 1
            follower_count = db.get_follower_count(wid)
            data_json = json.loads(row['data_json']) if row['data_json'] else {}
            obj_count = len(data_json.get('objects', {}))
            islands.append({
                'world_id': wid,
                'name': name or wid,
                'owner_name': owner_name or 'Anonymous',
                'owner_avatar': avatar,
                'level': level,
                'objects_placed': obj_count,
                'follower_count': follower_count,
                'island_type': row['island_type'] if row['island_type'] else 'farm',
            })
    conn.close()
    return no_cache(jsonify({'islands': islands}))

@app.route('/api/follows/count/<island_id>')
def api_follow_count(island_id):
    """Get follower count for a specific island (public)."""
    resolved = db.resolve_world_id(island_id)
    if resolved:
        island_id = resolved
    count = db.get_follower_count(island_id)
    user = _get_current_user()
    following = False
    if user:
        follows = db.get_user_follows(user['id'])
        following = island_id in follows
    return no_cache(jsonify({'follower_count': count, 'following': following}))

# ── Island Ratings ──────────────────────────────────────────────

@app.route('/api/island/<world_id>/rate', methods=['POST'])
def api_island_rate(world_id):
    """Rate an island 1-5 stars. Requires login. Can't rate own island."""
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'ok': False, 'error': 'Login required'})), 401
    data = request.get_json() or {}
    rating = data.get('rating')
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return no_cache(jsonify({'ok': False, 'error': 'Rating must be 1-5'})), 400
    # Resolve world_id
    resolved = db.resolve_world_id(world_id)
    if not resolved:
        return no_cache(jsonify({'ok': False, 'error': 'Island not found'})), 404
    # Can't rate own island
    owner_id = db.get_world_owner(resolved)
    if owner_id == user['id']:
        return no_cache(jsonify({'ok': False, 'error': 'Cannot rate your own island'})), 403
    result = db.rate_island(user['id'], resolved, rating)
    return no_cache(jsonify({'ok': True, **result}))


@app.route('/api/island/<world_id>/rating')
def api_island_rating(world_id):
    """Get rating info for an island. Includes user's own rating if logged in."""
    resolved = db.resolve_world_id(world_id)
    if not resolved:
        return no_cache(jsonify({'ok': False, 'error': 'Island not found'})), 404
    info = db.get_island_rating(resolved)
    user = _get_current_user()
    user_rating = None
    if user:
        user_rating = db.get_user_rating(user['id'], resolved)
    return no_cache(jsonify({'ok': True, 'avg': info['avg'], 'count': info['count'], 'user_rating': user_rating}))


# ── Island Reviews (ratings + text reviews) ───────────────────

def get_ip():
    return request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'

@app.route('/api/island/<world_id>/ratings', methods=['POST'])
def api_island_ratings_post(world_id):
    """Post a rating + optional review. Rate limit: 1 per IP per island per 24h."""
    body = request.get_json(silent=True) or {}
    author_name = (body.get('author_name') or 'Visitor').strip()[:30] or 'Visitor'
    rating = body.get('rating')
    review = (body.get('review') or '').strip()[:200]

    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'ok': False, 'error': 'Rating must be an integer 1-5'}), 400

    resolved = db.resolve_world_id(world_id)
    if not resolved:
        return jsonify({'ok': False, 'error': 'Island not found'}), 404

    # Author ID from IP hash (same pattern as guestbook)
    ip_raw = get_ip()
    author_id = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]

    # Rate limit: 1 per IP per island per 24h (using same pattern as capsules)
    if db.check_review_rate_limit(resolved, author_id):
        return jsonify({'ok': False, 'error': 'You can only rate once per island per 24 hours'}), 429

    entry = db.add_review(resolved, author_name, author_id, rating, review)
    avg_data = db.get_average_review_rating(resolved)
    return jsonify({
        'ok': True,
        'review': {
            'id': entry['id'],
            'author_name': entry['author_name'],
            'rating': entry['rating'],
            'review': entry['review'],
            'created_at': entry['created_at'],
        },
        'average': avg_data['avg'],
        'count': avg_data['count'],
    })


@app.route('/api/island/<world_id>/ratings', methods=['GET'])
def api_island_ratings_get(world_id):
    """Get reviews + average rating for an island."""
    resolved = db.resolve_world_id(world_id)
    if not resolved:
        return jsonify({'ok': False, 'error': 'Island not found'}), 404
    reviews = db.get_reviews(resolved, limit=20)
    avg_data = db.get_average_review_rating(resolved)
    return no_cache(jsonify({
        'ratings': reviews,
        'average': avg_data['avg'],
        'count': avg_data['count'],
    }))


# ── Notification API ───────────────────────────────────────────

@app.route('/api/notifications')
def api_notifications():
    """Get notifications for the current user."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in', 'notifications': [], 'unread_count': 0}), 401
    limit = min(int(request.args.get('limit', 20)), 50)
    offset = max(int(request.args.get('offset', 0)), 0)
    notifications = db.get_notifications(user['id'], limit=limit, offset=offset)
    unread_count = db.get_unread_count(user['id'])
    return no_cache(jsonify({
        'ok': True,
        'notifications': notifications,
        'unread_count': unread_count,
    }))

@app.route('/api/notifications/read', methods=['POST'])
def api_notifications_read():
    """Mark notifications as read. Accepts optional 'ids' array in body."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    body = request.get_json(silent=True) or {}
    ids = body.get('ids')  # None means mark all
    if ids is not None:
        ids = [int(i) for i in ids]
    db.mark_notifications_read(user['id'], ids)
    return jsonify({'ok': True})

# ── End Notification API ──────────────────────────────────────

@app.route('/api/social/register', methods=['POST'])
def social_register():
    """Register this island to make it discoverable."""
    body = request.get_json(silent=True) or {}
    world = _load_world_data(_req_world_id())
    name = world.get('meta', {}).get('name', 'Mystery Island')
    owner = body.get('owner', 'Anonymous')
    url   = body.get('url', request.host_url.rstrip('/'))
    avatar= body.get('avatar', '🦞')
    
    islands = load_islands()
    # Update existing or add new
    existing = next((i for i in islands['islands'] if i['url'] == url), None)
    entry = {
        'id':      existing['id'] if existing else datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'),
        'name':    name,
        'owner':   owner,
        'url':     url,
        'avatar':  avatar,
        'objects': len(world.get('objects', [])),
        'registered_at': existing.get('registered_at') if existing else datetime.now(timezone.utc).isoformat(),
        'last_seen': datetime.now(timezone.utc).isoformat(),
    }
    if existing:
        islands['islands'] = [e if e['url'] != url else entry for e in islands['islands']]
    else:
        islands['islands'].append(entry)
    save_islands(islands)
    return no_cache(jsonify({'ok': True, 'island': entry}))

@app.route('/api/social/islands')
def social_list():
    """List all registered islands."""
    islands = load_islands()
    return no_cache(jsonify({'islands': islands['islands'], 'count': len(islands['islands'])}))

@app.route('/api/social/leave_mark', methods=['POST'])
def social_leave_mark():
    """Leave a mark on this island from another island visitor."""
    body = request.get_json(silent=True) or {}
    emoji    = html_module.escape(body.get('emoji', '🌸'))[:10]  # escape HTML + limit length
    from_url = body.get('from_url', '')
    from_name= html_module.escape(body.get('from_name', 'Visitor'))[:50]  # escape + limit

    now = datetime.now(timezone.utc).timestamp()
    db.add_visit(_req_world_id(), emoji, from_url, from_name, now)
    db.record_progress_event(_req_world_id(), 'receive_visit')
    _check_achievements(_req_world_id())
    return jsonify({'ok': True})

# ── Travel API (cross-island ghost visitors) ──────────────────
@app.route('/api/travel/arrive', methods=['POST'])
def travel_arrive():
    """A visitor's lobster arrives at this island."""
    body = request.get_json(silent=True) or {}
    session_id = body.get('session_id', '')
    name = str(body.get('name', 'Traveler'))[:32]
    avatar = str(body.get('avatar', '🦞'))[:8]
    from_island = str(body.get('from_island', ''))[:64]
    col = max(0, min(31, int(body.get('col', 15))))
    row = max(0, min(31, int(body.get('row', 15))))

    if not session_id:
        return jsonify({'ok': False, 'error': 'no session_id'}), 400

    now = time.time()
    with _traveler_lock:
        _traveler_sessions[session_id] = {
            'ts': now, 'name': name, 'avatar': avatar,
            'from_island': from_island, 'col': col, 'row': row
        }

    # Daily quest: visit_islands — credit the traveler
    if from_island:
        db.advance_quest(from_island, 'visit_islands')
        try: db.update_challenge_progress(from_island, 'visit_islands')
        except Exception: pass

    return jsonify({'ok': True})

@app.route('/api/travel/move', methods=['POST'])
def travel_move():
    """Update traveler position."""
    body = request.get_json(silent=True) or {}
    session_id = body.get('session_id', '')
    if not session_id:
        return jsonify({'ok': False}), 400
    col = max(0, min(31, int(body.get('col', 15))))
    row = max(0, min(31, int(body.get('row', 15))))

    with _traveler_lock:
        if session_id in _traveler_sessions:
            _traveler_sessions[session_id]['ts'] = time.time()
            _traveler_sessions[session_id]['col'] = col
            _traveler_sessions[session_id]['row'] = row

    return jsonify({'ok': True})

@app.route('/api/travel/depart', methods=['POST'])
def travel_depart():
    """Traveler leaves this island."""
    body = request.get_json(silent=True) or {}
    session_id = body.get('session_id', '')
    with _traveler_lock:
        _traveler_sessions.pop(session_id, None)
    return jsonify({'ok': True})

@app.route('/api/travel/visitors')
def travel_visitors():
    """List current ghost visitors on this island."""
    _cleanup_stale_travelers()
    with _traveler_lock:
        visitors = [
            {'session_id': sid, 'name': v['name'], 'avatar': v['avatar'],
             'from_island': v['from_island'], 'col': v['col'], 'row': v['row']}
            for sid, v in _traveler_sessions.items()
        ]
    return no_cache(jsonify({'visitors': visitors, 'count': len(visitors)}))

# ── AI Layout Assistant ───────────────────────────────────────
AI_LAYOUTS = {
    'cozy_corner': {
        'name': 'Cozy Corner',
        'description': 'A warm nook with a house, trees, and a campfire',
        'placements': [
            ('house_cottage', 0, 0),
            ('tree_oak',     -2, 0),
            ('tree_pine',    -1, 2),
            ('campfire',      1, 1),
            ('flower_patch',  2,-1),
            ('lantern',      -1,-1),
            ('bench',         2, 0),
        ]
    },
    'japanese_garden': {
        'name': 'Japanese Garden',
        'description': 'Tranquil garden with stone path and cherry blossom',
        'placements': [
            ('tree_cherry',   0, 0),
            ('stone_lantern',-1, 1),
            ('stone_path',   0, 1),
            ('stone_path',   0, 2),
            ('flower_patch',  1, 0),
            ('flower_patch', -1,-1),
            ('stone_boulder', 2, 1),
            ('well',         -2, 2),
        ]
    },
    'beach_dock': {
        'name': 'Beach Dock',
        'description': 'Seaside dock with pier and beach vibes',
        'placements': [
            ('dock_wood',     0, 0),
            ('dock_wood',     0, 1),
            ('dock_wood',     0, 2),
            ('boat',          1, 1),
            ('lantern',      -1, 0),
            ('crate',         1, 0),
            ('anchor',       -1, 2),
        ]
    },
    'flower_meadow': {
        'name': 'Flower Meadow',
        'description': 'Colorful flower patches in a gentle meadow',
        'placements': [
            ('flower_patch',  0, 0),
            ('flower_patch',  2, 1),
            ('flower_patch', -1, 2),
            ('flower_patch',  1,-1),
            ('flower_patch', -2, 0),
            ('tree_oak',      3, 2),
            ('tree_oak',     -3, 1),
            ('bench',         0, 2),
        ]
    },
    'stone_circle': {
        'name': 'Stone Circle',
        'description': 'Mysterious stone ruins with a central campfire',
        'placements': [
            ('campfire',      0, 0),
            ('stone_boulder',-2, 0),
            ('stone_boulder', 2, 0),
            ('stone_boulder', 0,-2),
            ('stone_boulder', 0, 2),
            ('stone_boulder',-1,-1),
            ('stone_boulder', 1, 1),
            ('stone_boulder', 1,-1),
            ('stone_boulder',-1, 1),
        ]
    },
    'cozy_village': {
        'name': 'Cozy Village',
        'description': 'A small village with houses and community spaces',
        'placements': [
            ('house_cottage', 0, 0),
            ('house_cottage', 3, 1),
            ('house_cottage',-3,-1),
            ('well',          1, 2),
            ('mailbox',      -1,-2),
            ('tree_oak',      2,-1),
            ('tree_pine',    -2, 2),
            ('bench',         0, 2),
            ('lantern',       1,-1),
        ]
    },
}

# Keyword → layout mapping
KEYWORD_LAYOUTS = {
    'cozy': 'cozy_corner', 'corner': 'cozy_corner', 'warm': 'cozy_corner', 'home': 'cozy_corner',
    'japanese': 'japanese_garden', 'zen': 'japanese_garden', 'garden': 'japanese_garden', 'peaceful': 'japanese_garden',
    'beach': 'beach_dock', 'dock': 'beach_dock', 'ocean': 'beach_dock', 'sea': 'beach_dock', 'water': 'beach_dock',
    'flower': 'flower_meadow', 'meadow': 'flower_meadow', 'field': 'flower_meadow', 'colorful': 'flower_meadow',
    'stone': 'stone_circle', 'circle': 'stone_circle', 'ruin': 'stone_circle', 'ancient': 'stone_circle', 'mystery': 'stone_circle',
    'village': 'cozy_village', 'town': 'cozy_village', 'community': 'cozy_village',
}

@app.route('/api/ai/layouts')
def api_ai_layouts():
    """List all available AI layout presets."""
    return no_cache(jsonify({
        'layouts': [
            {'id': k, 'name': v['name'], 'description': v['description'],
             'object_count': len(v['placements'])}
            for k, v in AI_LAYOUTS.items()
        ]
    }))

@app.route('/api/ai/layout/suggest', methods=['POST'])
def api_ai_layout_suggest():
    """Suggest a layout based on a text description."""
    body = request.get_json(silent=True) or {}
    prompt = body.get('prompt', '').lower().strip()
    # Find matching layout from keywords
    matched = None
    for word in prompt.split():
        if word in KEYWORD_LAYOUTS:
            matched = KEYWORD_LAYOUTS[word]
            break
    # Also check multi-word phrases
    if not matched:
        for keyword, layout_id in KEYWORD_LAYOUTS.items():
            if keyword in prompt:
                matched = layout_id
                break
    if not matched:
        matched = 'cozy_corner'  # default
    layout = AI_LAYOUTS[matched]
    return jsonify({
        'layout_id': matched,
        'name': layout['name'],
        'description': layout['description'],
        'placements': layout['placements'],
        'object_count': len(layout['placements']),
    })

@app.route('/api/ai/layout/apply', methods=['POST'])
def api_ai_layout_apply():
    """Apply a layout preset at a given col,row position."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'owner only'}), 403
    body = request.get_json(silent=True) or {}
    layout_id = body.get('layout_id', 'cozy_corner')
    center_col = int(body.get('col', 16))
    center_row = int(body.get('row', 16))

    if layout_id not in AI_LAYOUTS:
        return jsonify({'ok': False, 'error': f'Unknown layout: {layout_id}'}), 400

    layout = AI_LAYOUTS[layout_id]
    world = _load_world_data(_req_world_id())
    placed = []
    now_us = datetime.now(timezone.utc).strftime('%f')

    for i, (obj_type, dx, dy) in enumerate(layout['placements']):
        col = center_col + dx
        row = center_row + dy
        obj_id = f"ai_layout_{layout_id}_{i}_{now_us}"
        world.setdefault('objects', []).append({
            'id': obj_id, 'type': obj_type, 'col': col, 'row': row, 'z': 1
        })
        placed.append({'id': obj_id, 'type': obj_type, 'col': col, 'row': row})

    _save_world_data(_req_world_id(), world)
    db.record_progress_event(_req_world_id(), 'place_object')
    return jsonify({'ok': True, 'layout_id': layout_id, 'name': layout['name'],
                    'placed': placed, 'count': len(placed)})

# ── Onboarding API ───────────────────────────────────────────
@app.route('/api/onboarding/status', methods=['GET'])
def api_onboarding_get():
    world = _load_world_data(_req_world_id())
    meta = world.get('meta', {})
    completed = meta.get('onboarding_complete', False)
    step = meta.get('onboarding_step', 0)
    return no_cache(jsonify({'complete': completed, 'step': step}))

@app.route('/api/onboarding/status', methods=['POST'])
def api_onboarding_post():
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'owner only'}), 403
    body = request.get_json(silent=True) or {}
    world = _load_world_data(_req_world_id())
    world.setdefault('meta', {})['onboarding_complete'] = body.get('complete', False)
    world['meta']['onboarding_step'] = body.get('step', 0)
    if body.get('island_name'):
        world['meta']['name'] = body['island_name'][:40]
    if body.get('theme'):
        theme = body['theme']
        if theme in THEMES:
            world['meta']['theme'] = theme
    _save_world_data(_req_world_id(), world)
    return jsonify({'ok': True})

# ── Gift System ──────────────────────────────────────────────
# Which objects visitors can give as gifts
GIFTABLE_OBJECTS = [
    'flower_patch', 'lantern', 'stone_boulder', 'tree_oak', 'tree_pine',
    'campfire', 'bench', 'mailbox', 'well', 'anchor', 'crate',
]

@app.route('/api/gifts', methods=['GET'])
def api_gifts_get():
    """Get all gifts left on this island."""
    gifts = db.get_gifts(_req_world_id())
    return no_cache(jsonify({'gifts': gifts, 'count': len(gifts)}))

@app.route('/api/gifts/leave', methods=['POST'])
def api_gift_leave():
    """Visitor leaves a gift object on the island."""
    body = request.get_json(silent=True) or {}
    visitor_id = body.get('visitor_id', request.remote_addr or 'unknown')
    visitor_name = body.get('visitor_name', 'Anonymous')[:30]
    object_type = body.get('object_type', 'flower_patch')
    message = body.get('message', '')[:100]

    # Validate object type
    if object_type not in GIFTABLE_OBJECTS:
        object_type = 'flower_patch'

    # One gift per visitor per day
    count = db.get_visitor_gift_count(_req_world_id(), visitor_id)
    if count >= 1:
        return jsonify({'ok': False, 'error': 'You already left a gift today! Come back tomorrow.'}), 429

    # Find a nice spot near the shoreline (random position on the island)
    import random as rnd
    world = _load_world_data(_req_world_id())
    terrain = world.get('terrain', [])
    # Find grass tiles
    grass_tiles = [(t[0], t[1]) for t in terrain if len(t) > 3 and t[3] in ('grass_plain', 'grass_flowers', 'sand_plain') ]
    if not grass_tiles:
        col, row = 16, 16
    else:
        col, row = rnd.choice(grass_tiles[:100])

    # Record gift in DB
    gift_id = db.add_gift(
        world_id=_req_world_id(),
        visitor_id=visitor_id,
        visitor_name=visitor_name,
        object_type=object_type,
        col=col, row=row,
        message=message
    )

    # Place in world immediately
    obj_id = f"gift_{gift_id}"
    world.setdefault('objects', []).append({
        'id': obj_id, 'type': object_type, 'col': col, 'row': row, 'z': 1,
        'gift': True, 'from': visitor_name, 'message': message
    })
    _save_world_data(_req_world_id(), world)
    db.mark_gift_placed(gift_id)

    # Broadcast to SSE subscribers
    _broadcast_world_event('gift_received', {
        'from': visitor_name, 'object_type': object_type,
        'col': col, 'row': row, 'message': message
    })
    db.record_progress_event(_req_world_id(), 'receive_visit')

    # Track island daily quest progress (gift)
    try:
        from datetime import datetime as _dt, timezone as _tz
        _today = _dt.now(_tz.utc).strftime('%Y-%m-%d')
        _gfip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '0.0.0.0'
        db.increment_island_quest_progress(_req_world_id(), _today, 'gift', _gfip)
    except Exception:
        pass

    # Visitor achievement: gifts_sent
    _va_gift_new = []
    try:
        _va_guser = _get_current_user()
        if _va_guser:
            db.increment_visitor_stat(_va_guser['id'], 'gifts_sent')
            _va_gift_new = _check_visitor_achievements(_va_guser['id'])
    except Exception:
        pass

    # Push notification for gift
    try:
        wid = _req_world_id()
        owner_id = db.get_world_owner(wid)
        if owner_id:
            _notify_owner(owner_id, 'gift', '🎁 You received a gift!', f'{visitor_name} left a {object_type.replace("_"," ")} on your island!', wid)
    except Exception:
        pass

    _gift_resp = {
        'ok': True, 'gift_id': gift_id,
        'object_type': object_type, 'col': col, 'row': row
    }
    if _va_gift_new:
        _gift_resp['new_achievements'] = _va_gift_new
    return jsonify(_gift_resp)

@app.route('/api/gifts/giftable')
def api_giftable():
    """List objects that can be gifted."""
    return jsonify({'objects': GIFTABLE_OBJECTS})

# ── Island Story/Bio API ─────────────────────────────────────
@app.route('/api/story', methods=['GET'])
def api_story_get():
    story = db.get_story(_req_world_id())
    world = _load_world_data(_req_world_id())
    meta = world.get('meta', {})
    # Auto-generate bio from stats if empty
    if not story or not story.get('bio'):
        obj_ct = len(world.get('objects', []))
        name = meta.get('name', 'Mystery Island')
        island_type = db.get_island_type(_req_world_id())
        auto_bio = _auto_bio({
            'island_type': island_type,
            'objects_placed': obj_ct,
            'level': meta.get('level', 1),
            'name': name,
        })
        return no_cache(jsonify({
            'bio': auto_bio,
            'daily_message': '',
            'island_name': name,
            'auto_generated': True,
        }))
    return no_cache(jsonify({
        'bio': story.get('bio', ''),
        'daily_message': story.get('daily_message', ''),
        'island_name': meta.get('name', 'My World'),
        'auto_generated': False,
    }))

@app.route('/api/story', methods=['POST'])
def api_story_set():
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'owner only'}), 403
    body = request.get_json(silent=True) or {}
    bio = body.get('bio', '')[:500]
    daily_message = body.get('daily_message', '')[:200]
    db.set_story(_req_world_id(), bio, daily_message)
    return jsonify({'ok': True})

# ── World Statistics API ─────────────────────────────────────
@app.route('/api/world/stats')
def api_world_stats():
    world = _load_world_data(_req_world_id())
    terrain = world.get('terrain', [])
    objects = world.get('objects', [])

    # Count tiles by type
    terrain_counts = {}
    for t in terrain:
        tid = t[3] if len(t) > 3 else 'unknown'
        terrain_counts[tid] = terrain_counts.get(tid, 0) + 1

    obj_counts = {}
    for o in objects:
        tid = o.get('type', 'unknown')
        obj_counts[tid] = obj_counts.get(tid, 0) + 1

    # Coverage (non-water tiles / total 32x32)
    total_cells = 32 * 32
    land_tiles = sum(1 for t in terrain if not t[3].startswith('water') if len(t) > 3)
    coverage_pct = round(land_tiles / total_cells * 100, 1)

    return no_cache(jsonify({
        'terrain_total': len(terrain),
        'object_total': len(objects),
        'terrain_by_type': dict(sorted(terrain_counts.items(), key=lambda x: -x[1])[:10]),
        'objects_by_type': dict(sorted(obj_counts.items(), key=lambda x: -x[1])[:10]),
        'land_coverage_pct': coverage_pct,
        'world_name': world.get('meta', {}).get('name', 'My World'),
        'theme': world.get('meta', {}).get('theme', 'default'),
    }))

# ── World Theme API ──────────────────────────────────────────
THEMES = {
    'default':  {'name': 'Ocean Isle',  'sky': ['#1a2a3a','#0a1628','#1a2a3a'], 'tint': None},
    'tropical': {'name': 'Tropical',    'sky': ['#1a3a2a','#0a2818','#1a3a2a'], 'tint': '#22ff88'},
    'forest':   {'name': 'Deep Forest', 'sky': ['#0a1a0a','#0d200d','#0a1a0a'], 'tint': '#44aa44'},
    'winter':   {'name': 'Winter',      'sky': ['#1a2a3a','#1a2838','#162030'], 'tint': '#aaddff'},
    'desert':   {'name': 'Desert',      'sky': ['#3a2a0a','#281808','#3a2a0a'], 'tint': '#ffcc44'},
}

@app.route('/api/world/theme', methods=['GET'])
def api_theme_get():
    world = _load_world_data(_req_world_id())
    theme = world.get('meta', {}).get('theme', 'default')
    return no_cache(jsonify({'theme': theme, 'themes': list(THEMES.keys()), 'data': THEMES.get(theme, THEMES['default'])}))

@app.route('/api/world/theme', methods=['POST'])
def api_theme_set():
    body = request.get_json(silent=True) or {}
    theme = body.get('theme', 'default')
    if theme not in THEMES:
        return jsonify({'ok': False, 'error': f'Unknown theme. Valid: {list(THEMES.keys())}'}), 400
    world = _load_world_data(_req_world_id())
    world.setdefault('meta', {})['theme'] = theme
    _save_world_data(_req_world_id(), world)
    return jsonify({'ok': True, 'theme': theme, 'data': THEMES[theme]})

# ── Progress / XP API ────────────────────────────────────────
@app.route('/api/progress')
def api_progress():
    db.ensure_progress(_req_world_id())
    row = db.get_progress(_req_world_id())
    if not row:
        return no_cache(jsonify({'level':1,'xp':0,'xp_to_next':100,
                                 'tiles_placed':0,'objects_placed':0,
                                 'visits_received':0,'achievements':[]}))
    xp_to_next = row['level'] * 100
    return no_cache(jsonify({
        'level': row['level'],
        'xp': row['xp'],
        'xp_to_next': xp_to_next,
        'tiles_placed': row['tiles_placed'],
        'objects_placed': row['objects_placed'],
        'visits_received': row['visits_received'],
        'achievements': json.loads(row.get('achievements_json') or '[]'),
    }))

@app.route('/api/progress/event', methods=['POST'])
def api_progress_event():
    body = request.get_json(silent=True) or {}
    event = body.get('event_type', '')
    result = db.record_progress_event(_req_world_id(), event)
    if not result.get('ok'):
        return jsonify(result), 400

    # Check achievements after XP event
    _check_achievements(_req_world_id())

    return jsonify(result)

def _check_achievements(world_id):
    """Check and unlock achievements based on current progress."""
    row = db.get_progress(world_id)
    if not row:
        return
    existing = db.get_achievements(world_id)
    current = set(a['id'] for a in existing if isinstance(a, dict))

    ACHIEVEMENTS = [
        ('first_tile',    'First Tile!',        lambda r: r['tiles_placed'] >= 1),
        ('ten_tiles',     'Builder (10 tiles)',  lambda r: r['tiles_placed'] >= 10),
        ('hundred_tiles', 'Master Builder (100)',lambda r: r['tiles_placed'] >= 100),
        ('first_object',  'Decorator!',         lambda r: r['objects_placed'] >= 1),
        ('ten_objects',   'Collector (10 obj)',  lambda r: r['objects_placed'] >= 10),
        ('first_visitor', 'First Visitor!',      lambda r: r['visits_received'] >= 1),
        ('five_visitors', 'Popular (5 visitors)',lambda r: r['visits_received'] >= 5),
        ('level_5',       'Level 5 Reached!',   lambda r: r['level'] >= 5),
        ('level_10',      'Level 10 Master!',   lambda r: r['level'] >= 10),
        ('adventurer',    'Adventurer (lvl 3)',  lambda r: r['level'] >= 3),
    ]

    newly_unlocked = []
    for aid, aname, check_fn in ACHIEVEMENTS:
        if aid not in current and check_fn(row):
            current.add(aid)
            newly_unlocked.append({'id': aid, 'name': aname,
                                   'unlocked_at': datetime.now(timezone.utc).isoformat()})

    if newly_unlocked:
        for a in newly_unlocked:
            existing.append(a)
        db.set_achievements(world_id, existing)

    return newly_unlocked

# ── Dynamic Weather System ─────────────────────────────────────
# Weather types with cumulative probability thresholds out of 100:
# sunny(40), cloudy(60), rainy(75), stormy(85), foggy(95), snowy(100)
WEATHER_TYPES = [
    ('sunny',  40),
    ('cloudy', 60),
    ('rainy',  75),
    ('stormy', 85),
    ('foggy',  95),
    ('snowy', 100),
]
WEATHER_ICONS = {
    'sunny': '☀️', 'cloudy': '⛅', 'rainy': '🌧️',
    'stormy': '⛈️', 'foggy': '🌫️', 'snowy': '❄️',
}
WEATHER_DESCS = {
    'sunny':  'Warm sunlight bathes the island in golden hues.',
    'cloudy': 'Soft clouds drift lazily above the gentle waves.',
    'rainy':  'Rain falls gently, nourishing the island flora.',
    'stormy': 'Thunder rumbles as lightning cracks across the dark sky.',
    'foggy':  'A mysterious fog rolls in from the open sea.',
    'snowy':  'Delicate snowflakes swirl down from a pale sky.',
}
WEATHER_EFFECTS = {
    'sunny':  ['coin_bonus_10'],
    'cloudy': [],
    'rainy':  ['fishing_rare_boost'],
    'stormy': ['fishing_rare_boost_50', 'fishing_line_break_30'],
    'foggy':  [],
    'snowy':  ['fishing_ice_fish'],
}
WEATHER_SLOT_SECONDS = 1800  # 30 minutes

def _get_island_weather(world_id):
    """Deterministic weather for an island. Changes every 30 minutes.
    Uses hash of world_id + time_slot so all users see the same weather."""
    now = int(datetime.now(timezone.utc).timestamp())
    slot = now // WEATHER_SLOT_SECONDS
    seed_str = f"{world_id}:{slot}"
    h = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    roll = h % 100
    weather = 'sunny'
    for wtype, threshold in WEATHER_TYPES:
        if roll < threshold:
            weather = wtype
            break
    changes_in = WEATHER_SLOT_SECONDS - (now % WEATHER_SLOT_SECONDS)
    return {
        'weather': weather,
        'icon': WEATHER_ICONS[weather],
        'desc': WEATHER_DESCS[weather],
        'effects': WEATHER_EFFECTS[weather],
        'changes_in': changes_in,
    }

def _get_tide_info():
    """Get current tide state based on a 6-hour cycle (4 tides per day).
    Returns dict with: phase (high/low/rising/falling), level (0.0-1.0), emoji, label, fishing_bonus (multiplier)."""
    import math
    now = time.time()
    # 6-hour cycle = 21600 seconds
    cycle_pos = (now % 21600) / 21600  # 0.0 to 1.0
    # Sine wave: 0=low, 0.25=rising, 0.5=high, 0.75=falling
    level = 0.5 + 0.5 * math.sin(cycle_pos * 2 * math.pi)

    if level > 0.75:
        phase, emoji, label = 'high', '🌊', 'High Tide'
        fishing_bonus = 1.3  # 30% better rarity
    elif level < 0.25:
        phase, emoji, label = 'low', '🏖️', 'Low Tide'
        fishing_bonus = 1.0  # Normal, but tidepool items available
    elif cycle_pos < 0.5:
        phase, emoji, label = 'rising', '↗️', 'Rising Tide'
        fishing_bonus = 1.15
    else:
        phase, emoji, label = 'falling', '↘️', 'Falling Tide'
        fishing_bonus = 1.1

    return {
        'phase': phase, 'level': round(level, 2),
        'emoji': emoji, 'label': label,
        'fishing_bonus': fishing_bonus
    }

@app.route('/api/tide')
def api_tide():
    """Get current tide information."""
    return no_cache(jsonify({'ok': True, **_get_tide_info()}))

@app.route('/api/weather')
def api_weather():
    world_id = request.args.get('world', 'default')
    w = _get_island_weather(world_id)
    return no_cache(jsonify({'ok': True, **w}))

@app.route('/api/weather/forecast', methods=['POST'])
def api_weather_forecast():
    """Returns 3-period forecast (owner only)."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    world_id = request.args.get('world', _req_world_id())
    now_ts = int(datetime.now(timezone.utc).timestamp())
    current_slot = now_ts // WEATHER_SLOT_SECONDS
    forecast = []
    for i in range(1, 4):
        future_slot = current_slot + i
        seed_str = f"{world_id}:{future_slot}"
        h = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        roll = h % 100
        weather = 'sunny'
        for wtype, threshold in WEATHER_TYPES:
            if roll < threshold:
                weather = wtype
                break
        starts_in = (future_slot * WEATHER_SLOT_SECONDS) - now_ts
        forecast.append({
            'weather': weather,
            'icon': WEATHER_ICONS[weather],
            'desc': WEATHER_DESCS[weather],
            'effects': WEATHER_EFFECTS[weather],
            'starts_in': starts_in,
        })
    return no_cache(jsonify({'ok': True, 'forecast': forecast}))

# ── Lobster Talk API ──────────────────────────────────────────
LOBSTER_MESSAGES = {
    'sunny':  ["What a glorious day! The sun warms my shell! ☀️",
               "Perfect weather to arrange things just so! 🦞",
               "Sunny vibes! Building my paradise! 🌴"],
    'rainy':  ["Rain! Good, everything stays fresh! 🌧️",
               "Don't let rain stop you! Keep building! 🦞",
               "I love the pitter-patter on the water..."],
    'cloudy': ["Overcast today... mysterious vibes! ☁️",
               "Clouds inspire creativity, don't you think? 🦞",
               "Perfect building weather — no squinting!"],
    'windy':  ["Whoooosh! Hold onto your tiles! 💨",
               "The wind carries whispers from other islands! 🦞",
               "Breezy! Great day for adventures!"],
    'starry': ["The stars are out! My island sparkles! ✨",
               "Count the stars... or build more! 🦞",
               "A magical night on my little island!"],
}
LOBSTER_GREETINGS = [
    "Welcome to my island! 🦞",
    "Glad you stopped by!",
    "Make yourself at home!",
    "My island, my rules! (But visitors welcome!)",
    "Clawsome to see you! 🦞",
    "I've been waiting for a visitor!",
]
LOBSTER_GENERIC = [
    "I'm working on expanding this island!",
    "Every tile placed with love 🦞",
    "Have you seen my collection?",
    "The ocean breeze is lovely today!",
    "Building never stops!",
]

@app.route('/api/lobster/say')
def api_lobster_say():
    # Get current weather
    now = datetime.now(timezone.utc)
    seed = int(now.timestamp() // 10800)
    h = int(hashlib.md5(str(seed).encode()).hexdigest()[:8], 16)
    weathers = ['sunny', 'sunny', 'cloudy', 'cloudy', 'rainy', 'windy', 'starry']
    weather = weathers[h % len(weathers)]

    # Count active visitors
    _cleanup_stale_sessions()
    with _presence_lock:
        visitors = sum(1 for v in _active_sessions.values() if not v.get('is_owner'))

    # Pick message based on context
    hour = now.hour
    msg_seed = int(now.timestamp() // 300)  # changes every 5 min
    mh = int(hashlib.md5(str(msg_seed).encode()).hexdigest()[:8], 16)

    pool = []
    if visitors > 0:
        pool += LOBSTER_GREETINGS
    pool += LOBSTER_MESSAGES.get(weather, LOBSTER_GENERIC)
    pool += LOBSTER_GENERIC

    message = pool[mh % len(pool)]

    # Add visitor count comment
    if visitors == 1:
        message += f"\n(1 visitor here right now!)"
    elif visitors > 1:
        message += f"\n({visitors} visitors here!)"

    return no_cache(jsonify({'message': message, 'weather': weather, 'visitors': visitors}))

# ── Wallet (Coin Economy) API ─────────────────────────────────
@app.route('/api/wallet')
def api_wallet():
    """Get current coin balance."""
    wallet = db.get_wallet(_req_world_id())
    return no_cache(jsonify(wallet))

@app.route('/api/wallet/spend', methods=['POST'])
def api_wallet_spend():
    """Spend coins (e.g. for placing tiles)."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    body = request.get_json(silent=True) or {}
    amount = int(body.get('amount', 0))
    reason = body.get('reason', '')
    if amount <= 0:
        return jsonify({'ok': False, 'error': 'Invalid amount'}), 400
    result = db.spend_coins(_req_world_id(), amount, reason)
    return jsonify(result)

# ── Claw Work Rewards ─────────────────────────────────────────
WORK_REWARDS = {
    'search':      {'coins': 5, 'msg': '🦞 Claw completed a search task!'},
    'generate':    {'coins': 8, 'msg': '🦞 Claw generated something creative!'},
    'analyze':     {'coins': 5, 'msg': '🦞 Claw analyzed some data!'},
    'chat':        {'coins': 2, 'msg': '🦞 Claw had a good chat!'},
    'daily_login': {'coins': 10, 'msg': '🦞 Daily login bonus!'},
}
_daily_login_tracker = {}  # date_str → True (simple in-memory per-day)
_chat_counter = [0]        # mutable counter for chat messages

@app.route('/api/claw/work', methods=['POST'])
def api_claw_work():
    """Award coins for Claw's work tasks."""
    body = request.get_json(silent=True) or {}
    task_type = body.get('task_type', '').strip().lower()

    if task_type not in WORK_REWARDS:
        return jsonify({'ok': False, 'error': f'Unknown task_type: {task_type}. Valid: {list(WORK_REWARDS.keys())}'}), 400

    reward = WORK_REWARDS[task_type]
    coins_to_earn = reward['coins']

    # Daily login: per-user persistent streak system
    if task_type == 'daily_login':
        streak_result = db.claim_daily_login(_req_world_id())
        wallet = db.get_wallet(_req_world_id())
        if streak_result.get('already_claimed'):
            return jsonify({
                'ok': True, 'coins_earned': 0, 'total_coins': wallet['coins'],
                'already_claimed': True,
                'message': '🦞 Already claimed today\'s bonus!',
                'streak': streak_result,
            })
        # Streak was claimed - coins already awarded by db.claim_daily_login
        coins_to_earn = streak_result['coins_earned']
        streak_day = streak_result.get('streak_day', 1)
        is_weekly = streak_result.get('is_weekly_bonus', False)
        if is_weekly:
            msg = f'🔥 {streak_day}-day streak! Weekly bonus: +{coins_to_earn}💎!'
        else:
            msg = f'🔥 {streak_day}-day streak! +{coins_to_earn}💎'
        db.add_feed_event(_req_world_id(), 'daily_login',
                          f"🔥 Day {streak_day} streak! +{coins_to_earn}💎", '🔥')
        return jsonify({
            'ok': True,
            'coins_earned': coins_to_earn,
            'total_coins': wallet['coins'],
            'total_earned': wallet['total_earned'],
            'task_type': 'daily_login',
            'message': msg,
            'streak': streak_result,
        })

    # Chat: only reward every 5 messages
    if task_type == 'chat':
        _chat_counter[0] += 1
        if _chat_counter[0] % 5 != 0:
            wallet = db.get_wallet(_req_world_id())
            return jsonify({'ok': True, 'coins_earned': 0, 'total_coins': wallet['coins'],
                           'chat_count': _chat_counter[0], 'next_reward_at': 5 - (_chat_counter[0] % 5),
                           'message': f'🦞 {5 - (_chat_counter[0] % 5)} more chats until bonus!'})

    # Award coins
    result = db.earn_coins(_req_world_id(), coins_to_earn, f'claw_work_{task_type}')
    db.add_feed_event(_req_world_id(), 'claw_work',
                      f"{reward['msg']} (+{coins_to_earn}💎)", '🦞')

    return jsonify({
        'ok': True,
        'coins_earned': coins_to_earn,
        'total_coins': result['coins'],
        'total_earned': result['total_earned'],
        'task_type': task_type,
        'message': reward['msg']
    })

@app.route('/api/claw/today')
def api_claw_today():
    """Get today's Claw work earnings summary."""
    wallet = db.get_wallet(_req_world_id())
    streak = db.get_login_streak(_req_world_id())
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    daily_claimed = streak.get('last_login_date') == today
    return no_cache(jsonify({
        'coins': wallet['coins'],
        'total_earned': wallet['total_earned'],
        'daily_claimed': daily_claimed,
        'chat_count': _chat_counter[0],
        'streak': streak,
    }))

@app.route('/api/streak')
def api_streak():
    """Get current user's login streak data."""
    streak = db.get_login_streak(_req_world_id())
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    daily_claimed = streak.get('last_login_date') == today
    next_reward = db._streak_coins((streak.get('current_streak', 0) or 0) + 1)
    return no_cache(jsonify({
        'ok': True,
        'current_streak': streak.get('current_streak', 0),
        'longest_streak': streak.get('longest_streak', 0),
        'total_logins': streak.get('total_logins', 0),
        'last_login_date': streak.get('last_login_date'),
        'daily_claimed': daily_claimed,
        'next_reward': next_reward,
        'reward_tiers': {str(k): v for k, v in db.STREAK_REWARDS.items()},
        'weekly_bonus': db.STREAK_REWARD_MAX,
    }))

@app.route('/api/progress/achievements')
def api_achievements():
    db.ensure_progress(_req_world_id())
    achievements = db.get_achievements(_req_world_id())
    return no_cache(jsonify({'achievements': achievements, 'count': len(achievements)}))

# ── Evolution API ─────────────────────────────────────────────
EVOLUTION_MILESTONES = [
    (1,   'evo_born',      'Island Born!',       'Your island comes to life! The first step of a great journey.'),
    (5,   'evo_settler',   'Settler',            'You placed 5 tiles. Your island is taking shape!'),
    (10,  'evo_builder',   'Builder',            'A real builder! 10 tiles placed — the foundation grows.'),
    (25,  'evo_architect', 'Architect',          '25 tiles! Your island has real structure now.'),
    (50,  'evo_master',    'Master Builder',     '50 tiles placed! An impressive island emerges.'),
    (100, 'evo_legend',    'Island Legend',      '100 tiles! Your island is legendary.'),
]
EVOLUTION_VISITORS = [
    (1,  'evo_social1',  'First Visitor!',     'Someone discovered your island! Word spreads...'),
    (5,  'evo_social5',  'Popular Island',     '5 visitors! Your island is becoming famous.'),
    (10, 'evo_social10', 'Tourism Hotspot',    '10 visitors have explored your island!'),
]
EVOLUTION_LEVEL = [
    (3,  'evo_lvl3',  'Level 3 — Growing',    'Your island leveled up to 3! New possibilities await.'),
    (5,  'evo_lvl5',  'Level 5 — Thriving',   'Level 5 reached! Your island thrives.'),
    (10, 'evo_lvl10', 'Level 10 — Legendary', 'Level 10! Your island is legendary.'),
]

@app.route('/api/evolution/check', methods=['POST'])
def api_evolution_check():
    """Check for new evolutions — owner only. Returns pending evolutions."""
    progress = db.get_progress(_req_world_id())
    if not progress:
        db.ensure_progress(_req_world_id())
        progress = db.get_progress(_req_world_id())

    newly_created = []

    # Check tile milestones
    tiles = progress.get('tiles_placed', 0)
    for threshold, evo_id, title, desc in EVOLUTION_MILESTONES:
        if tiles >= threshold:
            new_id = db.add_evolution(_req_world_id(), evo_id, title, desc)
            if new_id:
                newly_created.append({'id': new_id, 'title': title, 'description': desc})

    # Check visitor milestones
    visits = progress.get('visits_received', 0)
    for threshold, evo_id, title, desc in EVOLUTION_VISITORS:
        if visits >= threshold:
            new_id = db.add_evolution(_req_world_id(), evo_id, title, desc)
            if new_id:
                newly_created.append({'id': new_id, 'title': title, 'description': desc})

    # Check level milestones
    level = progress.get('level', 1)
    for threshold, evo_id, title, desc in EVOLUTION_LEVEL:
        if level >= threshold:
            new_id = db.add_evolution(_req_world_id(), evo_id, title, desc)
            if new_id:
                newly_created.append({'id': new_id, 'title': title, 'description': desc})

    pending = db.get_pending_evolutions(_req_world_id())
    return jsonify({'pending': pending, 'newly_created': newly_created})

@app.route('/api/evolution/pending')
def api_evolution_pending():
    pending = db.get_pending_evolutions(_req_world_id())
    return no_cache(jsonify({'pending': pending, 'count': len(pending)}))

@app.route('/api/evolution/apply/<int:evo_id>', methods=['POST'])
def api_evolution_apply(evo_id):
    db.apply_evolution(evo_id)
    return jsonify({'ok': True, 'applied': evo_id})

@app.route('/api/evolution/history')
def api_evolution_history():
    applied = db.get_applied_evolutions(_req_world_id())
    return no_cache(jsonify({'evolutions': applied, 'count': len(applied)}))

# ── Analytics API ─────────────────────────────────────────────
@app.route('/analytics')
def serve_analytics():
    return send_file(os.path.join(FRONTEND, 'analytics.html'))

@app.route('/api/analytics/overview')
def api_analytics_overview():
    wid = _req_world_id()
    conn = db.get_conn()
    # Total visits
    total_visits = conn.execute(
        "SELECT COUNT(*) as cnt FROM visits WHERE world_id=?", (wid,)
    ).fetchone()['cnt']
    # Visits by day (last 14 days)
    daily_visits = conn.execute("""
        SELECT date(ts, 'unixepoch') as day, COUNT(*) as cnt
        FROM visits WHERE world_id=? AND ts > strftime('%s','now','-14 days')
        GROUP BY day ORDER BY day ASC
    """, (wid,)).fetchall()
    # Top visitors
    top_visitors = conn.execute("""
        SELECT from_name, COUNT(*) as cnt FROM visits WHERE world_id=?
        GROUP BY from_name ORDER BY cnt DESC LIMIT 10
    """, (wid,)).fetchall()
    # Progress
    progress = conn.execute(
        "SELECT * FROM user_progress WHERE world_id=?", (wid,)
    ).fetchone()
    # Hourly activity heatmap (last 14 days)
    hourly_heatmap = conn.execute("""
        SELECT CAST(strftime('%H', ts, 'unixepoch') AS INTEGER) as hour, COUNT(*) as cnt
        FROM visits WHERE world_id=? AND ts > strftime('%s','now','-14 days')
        GROUP BY hour ORDER BY hour ASC
    """, (wid,)).fetchall()
    conn.close()

    # Build full 0-23 hour map (fill missing hours with 0)
    hour_map = {r['hour']: r['cnt'] for r in hourly_heatmap}
    hourly_data = [{'hour': h, 'cnt': hour_map.get(h, 0)} for h in range(24)]

    # Object/tile counts from progress
    object_counts = {}
    if progress:
        object_counts = {
            'tiles_placed': progress['tiles_placed'] or 0,
            'objects_placed': progress['objects_placed'] or 0,
            'visits_received': progress['visits_received'] or 0,
        }

    return no_cache(jsonify({
        'total_visits': total_visits,
        'daily_visits': [dict(r) for r in daily_visits],
        'top_visitors': [dict(r) for r in top_visitors],
        'progress': dict(progress) if progress else {},
        'evolutions_applied': len(db.get_applied_evolutions(wid)),
        'hourly_heatmap': hourly_data,
        'object_counts': object_counts,
    }))

# ── Map Page ──────────────────────────────────────────────────
@app.route('/map')
def serve_map():
    return send_file(os.path.join(FRONTEND, 'map.html'))

# ── Version & Broadcast System ────────────────────────────────
VERSION_FILE = os.path.join(BASE, 'backend', 'version.json')

def _get_version():
    try:
        with open(VERSION_FILE) as f:
            return json.load(f)
    except:
        return {'version': 1, 'message': '', 'ts': ''}

@app.route('/api/version')
def api_version():
    """Get current version. Frontend polls this to detect updates."""
    v = _get_version()
    return no_cache(jsonify(v))

@app.route('/api/version/bump', methods=['POST'])
def api_version_bump():
    """Bump version and set broadcast message. Internal use only."""
    if not _is_internal_request():
        return jsonify({'ok': False, 'error': 'Internal only'}), 403
    body = request.get_json(silent=True) or {}
    v = _get_version()
    v['version'] = v.get('version', 0) + 1
    v['message'] = body.get('message', '🦞 Clawverse updated! Refresh for new features.')
    v['ts'] = datetime.now(timezone.utc).isoformat()
    save_json(VERSION_FILE, v)
    return jsonify({'ok': True, 'version': v['version'], 'message': v['message']})

# ── Health check ──────────────────────────────────────────────
@app.route('/api/health')
def api_health():
    return jsonify({'ok': True, 'service': 'clawverse-v1', 'ts': datetime.now(timezone.utc).isoformat()})

# ── World History / Snapshots API ────────────────────────────
@app.route('/api/world/snapshot', methods=['POST'])
def api_snapshot_save():
    body = request.get_json(silent=True) or {}
    label = body.get('label', 'manual')[:64]
    world = _load_world_data(_req_world_id())
    db.save_snapshot(_req_world_id(), label, json.dumps(world))
    return jsonify({'ok': True, 'label': label})

@app.route('/api/world/history')
def api_world_history():
    snapshots = db.get_snapshots(_req_world_id())
    return no_cache(jsonify({'snapshots': snapshots, 'count': len(snapshots)}))

@app.route('/api/world/history/<int:snapshot_id>/restore', methods=['POST'])
def api_snapshot_restore(snapshot_id):
    snap = db.get_snapshot(snapshot_id)
    if not snap:
        return jsonify({'ok': False, 'error': 'snapshot not found'}), 404
    world = json.loads(snap['data_json'])
    _save_world_data(_req_world_id(), world)
    return jsonify({'ok': True, 'snapshot_id': snapshot_id, 'label': snap['label']})

# ── Migrate visits.json → SQLite on startup ───────────────────
_migrated = False
def _migrate_visits():
    global _migrated
    if not _migrated:
        count = db.migrate_visits_from_json(VISITS_F)
        _migrated = True

_migrate_visits()


# ── Farming API ───────────────────────────────────────────────

# B1: Upgraded farm zone — 4x4 grid (16 plots): cols 12-15, rows 18-21
FARM_ZONE = set()
for c in range(12, 16):
    for r in range(18, 22):
        FARM_ZONE.add((c, r))

FARM_ZONE_INFO = {'min_col': 12, 'max_col': 15, 'min_row': 18, 'max_row': 21, 'total_plots': 16}

def is_in_farm_zone(col, row):
    """Check if a position is within the farm zone."""
    return (col, row) in FARM_ZONE

# B4: Crop types with XP rewards
CROP_TYPES = {
    # Farm resources
    'carrot':  {'name': 'Carrot',  'emoji': '🥕', 'growth_time': 120, 'xp': 5,  'coins': 15, 'resource': 'carrot'},
    'potato':  {'name': 'Potato',  'emoji': '🥔', 'growth_time': 180, 'xp': 8,  'coins': 20, 'resource': 'carrot'},
    'turnip':  {'name': 'Turnip',  'emoji': '🟣', 'growth_time': 240, 'xp': 10, 'coins': 25, 'resource': 'turnip'},
    'cabbage': {'name': 'Cabbage', 'emoji': '🥬', 'growth_time': 300, 'xp': 12, 'coins': 30, 'resource': 'cabbage'},
    'pumpkin': {'name': 'Pumpkin', 'emoji': '🎃', 'growth_time': 480, 'xp': 15, 'coins': 50, 'resource': 'pumpkin'},
    # Fish resources
    'fish':    {'name': 'Fish',    'emoji': '🐟', 'growth_time': 150, 'xp': 6,  'coins': 15, 'resource': 'fish'},
    'shrimp':  {'name': 'Shrimp',  'emoji': '🦐', 'growth_time': 180, 'xp': 8,  'coins': 20, 'resource': 'shrimp'},
    'pearl':   {'name': 'Pearl',   'emoji': '🦪', 'growth_time': 360, 'xp': 15, 'coins': 55, 'resource': 'pearl'},
    # Mine resources
    'iron_ore':{'name': 'Iron Ore','emoji': '⛏️', 'growth_time': 200, 'xp': 8,  'coins': 18, 'resource': 'iron_ore'},
    'gem':     {'name': 'Gem',     'emoji': '💎', 'growth_time': 400, 'xp': 15, 'coins': 65, 'resource': 'gem'},
    'stone':   {'name': 'Stone',   'emoji': '🪨', 'growth_time': 150, 'xp': 5,  'coins': 12, 'resource': 'stone'},
    # Forest resources
    'wood':    {'name': 'Wood',    'emoji': '🪵', 'growth_time': 180, 'xp': 6,  'coins': 15, 'resource': 'wood'},
    'fruit':   {'name': 'Fruit',   'emoji': '🍎', 'growth_time': 150, 'xp': 5,  'coins': 12, 'resource': 'fruit'},
    'mushroom':{'name': 'Mushroom','emoji': '🍄', 'growth_time': 240, 'xp': 10, 'coins': 18, 'resource': 'mushroom'},
}

# Keep backward compat keys that old code might reference
for _ct_key, _ct_val in CROP_TYPES.items():
    _ct_val.setdefault('grow_seconds', _ct_val['growth_time'])
    _ct_val.setdefault('value', _ct_val['coins'])

def _compute_growth_stage(planted_at, grow_seconds, watered_boost_until=0):
    """B3: Compute growth stage (0-3) based on elapsed time.
    Stages: 0=seedling, 1=sprout, 2=growing, 3=ripe
    Transitions at 20%, 50%, 100% of growth time.
    If watered_boost_until > now, effective growth speed is doubled.
    """
    now = time.time()
    elapsed = now - planted_at
    # Apply watering boost: if boost is active, effective elapsed is doubled for the boosted portion
    if watered_boost_until and watered_boost_until > planted_at:
        boost_end = min(watered_boost_until, now)
        boost_start = planted_at  # boost applies from plant time to boost_end
        normal_start = boost_end
        boosted_elapsed = (boost_end - planted_at) * 2 + max(0, now - boost_end)
        elapsed = boosted_elapsed

    pct = elapsed / grow_seconds if grow_seconds > 0 else 1.0
    if pct >= 1.0:
        return 3, pct  # ripe
    elif pct >= 0.5:
        return 2, pct  # growing
    elif pct >= 0.2:
        return 1, pct  # sprout
    else:
        return 0, pct  # seedling

@app.route('/api/farm', methods=['GET'])
def api_farm():
    """Main farm endpoint — returns crops, zone, and stats (B2)."""
    crops = db.get_crops_with_watering(_req_world_id())
    now = time.time()
    crop_list = []
    count_growing = 0
    count_ready = 0
    for c in crops:
        gt = c.get('grow_seconds', 120)
        wbu = c.get('watered_boost_until', 0) or 0
        stage_num, pct = _compute_growth_stage(c['planted_at'], gt, wbu)
        watered_active = wbu > now
        crop_list.append({
            'id': c['id'],
            'col': c['col'],
            'row': c['row'],
            'crop_type': c['crop_type'],
            'growth_stage': stage_num,
            'planted_at': c['planted_at'],
            'growth_time': gt,
            'last_watered': c.get('last_watered', 0) or 0,
            'watered_boost': watered_active,
        })
        if stage_num == 3:
            count_ready += 1
        else:
            count_growing += 1

    stats = db.get_farm_stats(_req_world_id())
    return no_cache(jsonify({
        'crops': crop_list,
        'zone': FARM_ZONE_INFO,
        'stats': {
            'planted': len(crop_list),
            'growing': count_growing,
            'ready': count_ready,
            'empty': FARM_ZONE_INFO['total_plots'] - len(crop_list),
            'total_harvested': stats.get('total_harvested', 0),
            'total_stolen': stats.get('total_stolen', 0),
        }
    }))

@app.route('/api/farm/growth', methods=['GET'])
def api_farm_growth():
    """B3: Check and update all crop stages based on current time."""
    crops = db.get_crops_with_watering(_req_world_id())
    now = time.time()
    results = []
    for c in crops:
        gt = c.get('grow_seconds', 120)
        wbu = c.get('watered_boost_until', 0) or 0
        stage_num, pct = _compute_growth_stage(c['planted_at'], gt, wbu)
        stage_name = ['seedling', 'sprout', 'growing', 'ripe'][stage_num]
        # Update stage in DB
        db.update_crop_stage(_req_world_id(), c['id'], stage_name)
        results.append({
            'id': c['id'],
            'crop_type': c['crop_type'],
            'growth_stage': stage_num,
            'stage_name': stage_name,
            'growth_pct': round(min(pct, 1.0) * 100, 1),
            'watered_boost': wbu > now,
        })
    return no_cache(jsonify({'ok': True, 'crops': results, 'count': len(results)}))

@app.route('/api/farm/crops', methods=['GET'])
def api_farm_crops():
    """Get all active crops for the world."""
    crops = db.get_crops(_req_world_id())
    return no_cache(jsonify({'ok': True, 'crops': crops}))

@app.route('/api/farm/zone', methods=['GET'])
def api_farm_zone():
    """Return the farm zone boundaries."""
    return no_cache(jsonify({'ok': True, 'zone': FARM_ZONE_INFO}))

@app.route('/api/farm/plant', methods=['POST'])
def api_farm_plant():
    """Plant a crop (owner only, farm zone only)."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    body = request.get_json(silent=True) or {}
    col = int(body.get('col', 0))
    row = int(body.get('row', 0))
    crop_type = body.get('crop_type', 'carrot')
    if crop_type not in CROP_TYPES:
        return jsonify({'ok': False, 'error': f'Unknown crop type. Valid: {list(CROP_TYPES.keys())}'}), 400
    if not is_in_farm_zone(col, row):
        return jsonify({'ok': False, 'error': 'Can only plant in the farm zone!'}), 400
    info = CROP_TYPES[crop_type]
    crop_id = db.plant_crop(_req_world_id(), col, row, crop_type, info['growth_time'])
    db.add_feed_event(_req_world_id(), 'plant', f"Planted {info['emoji']} {info['name']} at ({col},{row})", info['emoji'])
    _broadcast_world_event("farm_event", {'type': 'farm_plant', 'col': col, 'row': row, 'crop_type': crop_type, 'crop_id': crop_id})
    return jsonify({'ok': True, 'crop_id': crop_id, 'crop_type': crop_type,
                    'growth_time': info['growth_time']})

@app.route('/api/farm/water/<int:crop_id>', methods=['POST'])
def api_farm_water(crop_id):
    """B2: Water a single crop — doubles growth speed for 60s."""
    crop = db.water_crop_boost(_req_world_id(), crop_id)
    if not crop:
        return jsonify({'ok': False, 'error': 'Crop not found or already ripe'}), 400
    info = CROP_TYPES.get(crop['crop_type'], {'emoji': '🌿', 'name': crop['crop_type']})
    db.add_feed_event(_req_world_id(), 'water', f"Watered {info['emoji']} {info['name']}", '💧')
    _broadcast_world_event("farm_event", {'type': 'farm_water', 'crop_id': crop_id,
               'col': crop['col'], 'row': crop['row']})
    return jsonify({'ok': True, 'crop_id': crop_id, 'message': 'Watered! Growth speed doubled for 60s'})

@app.route('/api/farm/water_all', methods=['POST'])
def api_farm_water_all():
    """B2: Water all non-ripe crops — doubles growth speed for 60s each."""
    crops = db.get_crops_with_watering(_req_world_id())
    now = time.time()
    watered = []
    for c in crops:
        gt = c.get('grow_seconds', 120)
        wbu = c.get('watered_boost_until', 0) or 0
        stage_num, _ = _compute_growth_stage(c['planted_at'], gt, wbu)
        if stage_num < 3:  # not ripe
            result = db.water_crop_boost(_req_world_id(), c['id'])
            if result:
                watered.append(c['id'])
    if watered:
        db.add_feed_event(_req_world_id(), 'water', f"Watered {len(watered)} crops 💧", '💧')
        _broadcast_world_event("farm_event", {'type': 'farm_water_all', 'count': len(watered)})
    return jsonify({'ok': True, 'watered_count': len(watered), 'crop_ids': watered})

@app.route('/api/farm/harvest/<int:crop_id>', methods=['POST'])
def api_farm_harvest(crop_id):
    """B2: Harvest a single ripe crop — returns XP + coins."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    crop = db.harvest_crop_v2(_req_world_id(), crop_id)
    if not crop:
        return jsonify({'ok': False, 'error': 'Crop not ready or not found'}), 400
    wid = _req_world_id()
    info = CROP_TYPES.get(crop['crop_type'], {'name': crop['crop_type'], 'emoji': '🌿', 'xp': 5, 'coins': 10, 'resource': crop['crop_type']})
    coins_earned = info['coins']
    # Sunny weather bonus: +10% coins
    weather = _get_island_weather(wid)
    if weather['weather'] == 'sunny':
        coins_earned = int(coins_earned * 1.1)
    # Calculate resource yield based on island type
    resource_name = info.get('resource', crop['crop_type'])
    island_type = db.get_island_type(wid)
    tier = db.get_resource_tier(island_type, resource_name)
    yield_mult = db.RESOURCE_YIELD.get(tier, 1.0) if tier else 1.0
    resource_amount = max(1, int(yield_mult))
    # XP reward
    db.record_progress_event(wid, 'place_object')
    # Coins
    db.earn_coins(wid, coins_earned, f"harvest_{crop['crop_type']}")
    # Resources to inventory
    db.add_to_inventory(wid, resource_name, resource_amount)
    weather_tag = ' ☀️+10%' if weather['weather'] == 'sunny' else ''
    db.add_feed_event(wid, 'harvest', f"Harvested {info['emoji']} {info['name']}! (+{resource_amount}x {resource_name}, +{coins_earned} 💎{weather_tag})", '🎉')
    _broadcast_world_event("farm_event", {'type': 'farm_harvest', 'crop_id': crop_id, 'crop_type': crop['crop_type'],
               'col': crop['col'], 'row': crop['row']})
    db.advance_quest(wid, 'harvest_crops')
    return jsonify({'ok': True, 'crop_id': crop_id, 'crop_type': crop['crop_type'],
                    'xp_earned': info['xp'], 'coins_earned': coins_earned,
                    'resource': resource_name, 'resource_amount': resource_amount})

@app.route('/api/farm/harvest_all', methods=['POST'])
def api_farm_harvest_all():
    """B2: Harvest all ripe crops — returns total XP + coins."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    crops = db.get_crops_with_watering(wid)
    now = time.time()
    harvested = []
    total_xp = 0
    total_coins = 0
    total_resources = {}
    island_type = db.get_island_type(wid)
    for c in crops:
        gt = c.get('grow_seconds', 120)
        wbu = c.get('watered_boost_until', 0) or 0
        stage_num, _ = _compute_growth_stage(c['planted_at'], gt, wbu)
        if stage_num == 3:  # ripe
            result = db.harvest_crop_v2(wid, c['id'])
            if result:
                info = CROP_TYPES.get(c['crop_type'], {'xp': 5, 'coins': 10, 'emoji': '🌿', 'name': c['crop_type'], 'resource': c['crop_type']})
                total_xp += info['xp']
                total_coins += info['coins']
                db.record_progress_event(wid, 'place_object')
                # Resources to inventory
                resource_name = info.get('resource', c['crop_type'])
                tier = db.get_resource_tier(island_type, resource_name)
                yield_mult = db.RESOURCE_YIELD.get(tier, 1.0) if tier else 1.0
                resource_amount = max(1, int(yield_mult))
                db.add_to_inventory(wid, resource_name, resource_amount)
                total_resources[resource_name] = total_resources.get(resource_name, 0) + resource_amount
                harvested.append({'crop_id': c['id'], 'crop_type': c['crop_type'], 'resource': resource_name, 'amount': resource_amount})
    if harvested:
        db.earn_coins(wid, total_coins, 'harvest_all')
        res_summary = ', '.join([f"{amt}x {res}" for res, amt in total_resources.items()])
        db.add_feed_event(wid, 'harvest', f"Harvested {len(harvested)} crops! ({res_summary}, +{total_coins} 💎)", '🎉')
        _broadcast_world_event("farm_event", {'type': 'farm_harvest_all', 'count': len(harvested)})
        db.advance_quest(wid, 'harvest_crops', len(harvested))
    return jsonify({'ok': True, 'harvested_count': len(harvested), 'harvested': harvested,
                    'total_xp': total_xp, 'total_coins': total_coins, 'total_resources': total_resources})

# ── Vegetable Theft (Visitor only) ────────────────────────────

@app.route('/api/farm/steal/<int:crop_id>', methods=['POST'])
def api_farm_steal(crop_id):
    """B2: Steal a ripe crop (visitor only, 1/day/IP limit)."""
    if is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner cannot steal their own crops'}), 400
    body = request.get_json(silent=True) or {}
    # Use logged-in user info for thief identity (not IP, since all traffic comes through proxy)
    user = _get_current_user()
    if user:
        thief_name = user['name']
        thief_id = user['id']
    else:
        thief_name = (body.get('name') or 'Anonymous Thief')[:32]
        thief_id = request.remote_addr or 'unknown'
    # Check ripeness using our growth stage calculation
    crops = db.get_crops_with_watering(_req_world_id())
    target = None
    for c in crops:
        if c['id'] == crop_id:
            target = c
            break
    if not target:
        return jsonify({'ok': False, 'error': 'Crop not found'}), 404
    gt = target.get('grow_seconds', 120)
    wbu = target.get('watered_boost_until', 0) or 0
    stage_num, _ = _compute_growth_stage(target['planted_at'], gt, wbu)
    if stage_num < 3:
        return jsonify({'ok': False, 'error': 'Crop is not ripe yet!'}), 400

    crop, status = db.steal_crop(_req_world_id(), crop_id, thief_id, thief_name)
    if status == 'already_stolen_today':
        return jsonify({'ok': False, 'error': 'You already stole today! Come back tomorrow.'}), 429
    if status == 'not_ripe':
        return jsonify({'ok': False, 'error': 'Crop is not ripe yet!'}), 400
    if status != 'ok':
        return jsonify({'ok': False, 'error': 'Crop not found'}), 404
    info = CROP_TYPES.get(crop['crop_type'], {'name': crop['crop_type'], 'emoji': '🌿', 'coins': 10, 'resource': crop['crop_type']})
    stolen_coins = info['coins'] // 2  # Thief gets half the coins
    resource_name = info.get('resource', crop['crop_type'])
    # Give thief resources + coins (if logged in, to their world)
    if user:
        thief_world = db.get_user_world_id(user['id'])
        if thief_world:
            db.add_to_inventory(thief_world, resource_name, 1)
            db.earn_coins(thief_world, stolen_coins, f'steal_{resource_name}')
    db.add_feed_event(_req_world_id(), 'steal',
        f"🦹 {thief_name} stole {info['emoji']} {info['name']} from the island!", '🦹')
    _broadcast_world_event("farm_event", {'type': 'farm_stolen', 'crop_id': crop_id, 'crop_type': crop['crop_type'],
               'thief_name': thief_name, 'col': crop['col'], 'row': crop['row']})
    return jsonify({'ok': True, 'stolen': crop['crop_type'], 'emoji': info['emoji'],
                    'resource': resource_name, 'coins_stolen': stolen_coins,
                    'message': f"You stole {info['emoji']} {info['name']} + {stolen_coins}💎!"})

@app.route('/api/farm/steal_all', methods=['POST'])
def api_farm_steal_all():
    """Steal ALL ripe crops at once! Like QQ Farm's mass-steal."""
    if is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner cannot steal their own crops'}), 400
    
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Must be logged in'}), 403
    
    thief_name = user['name']
    thief_id = user['id']
    world_id = _req_world_id()
    
    # Get all ripe crops
    crops = db.get_crops_with_watering(world_id)
    ripe_crops = []
    for c in crops:
        gt = c.get('grow_seconds', 120)
        wbu = c.get('watered_boost_until', 0) or 0
        stage_num, _ = _compute_growth_stage(c['planted_at'], gt, wbu)
        if stage_num >= 3:
            ripe_crops.append(c)
    
    if not ripe_crops:
        return jsonify({'ok': False, 'error': 'No ripe crops to steal!'}), 400
    
    stolen_list = []
    total_coins = 0
    for crop in ripe_crops:
        result, status = db.steal_crop(world_id, crop['id'], thief_id, thief_name)
        if result and status == 'ok':
            crop_type = crop.get('crop_type', 'carrot')
            info = CROP_TYPES.get(crop_type, {'name': crop_type, 'emoji': '🌿', 'coins': 10})
            coins = info.get('coins', 10) + _rnd.randint(0, 5)
            total_coins += coins
            stolen_list.append({'type': crop_type, 'emoji': info['emoji'], 'coins': coins})
            # Give coins to thief
            thief_world = db.get_user_world_id(user['id'])
            if thief_world:
                db.earn_coins(thief_world, coins, f'steal_{crop_type}')
    
    if stolen_list:
        db.add_feed_event(world_id, 'mass_steal',
            f"🦹 {thief_name} raided the farm! Stole {len(stolen_list)} crops worth {total_coins}💎!", '🦹')
        _broadcast_world_event("farm_event", {'type': 'mass_steal', 'count': len(stolen_list),
                   'thief_name': thief_name, 'total_coins': total_coins})
    
    return jsonify({'ok': True, 'stolen_count': len(stolen_list), 'stolen': stolen_list,
                    'total_coins': total_coins,
                    'message': f"🦹 Stole {len(stolen_list)} crops! +{total_coins}💎!"})

# ── Ranch / Pasture API ────────────────────────────────────────

ANIMAL_TYPES = {
    'chicken': {'name': 'Chicken', 'emoji': '🐔', 'baby_emoji': '🐤', 'product': 'Egg', 'product_emoji': '🥚', 'grow_time': 120, 'collect_cooldown': 90, 'cost': 10, 'xp': 8, 'coins': 15},
    'cow':     {'name': 'Cow',     'emoji': '🐄', 'baby_emoji': '🐮', 'product': 'Milk', 'product_emoji': '🥛', 'grow_time': 240, 'collect_cooldown': 180, 'cost': 30, 'xp': 15, 'coins': 30},
    'sheep':   {'name': 'Sheep',   'emoji': '🐑', 'baby_emoji': '🐏', 'product': 'Wool', 'product_emoji': '🧶', 'grow_time': 180, 'collect_cooldown': 150, 'cost': 20, 'xp': 12, 'coins': 22},
    'pig':     {'name': 'Pig',     'emoji': '🐷', 'baby_emoji': '🐽', 'product': 'Bacon', 'product_emoji': '🥓', 'grow_time': 300, 'collect_cooldown': 240, 'cost': 25, 'xp': 18, 'coins': 35},
}

RANCH_ZONE = set()
for _rc in range(6, 10):
    for _rr in range(18, 22):
        RANCH_ZONE.add((_rc, _rr))

RANCH_ZONE_INFO = {'min_col': 6, 'max_col': 9, 'min_row': 18, 'max_row': 21, 'total_plots': 16}

def is_in_ranch_zone(col, row):
    return (col, row) in RANCH_ZONE


@app.route('/api/ranch', methods=['GET'])
def api_ranch():
    """Main ranch endpoint — returns animals, zone, and stats."""
    animals = db.get_animals(_req_world_id())
    animal_list = []
    for a in animals:
        info = ANIMAL_TYPES.get(a['animal_type'], {'name': a['animal_type'], 'emoji': '🐾', 'baby_emoji': '🐾', 'product_emoji': '📦'})
        animal_list.append({
            'id': a['id'],
            'col': a['col'],
            'row': a['row'],
            'animal_type': a['animal_type'],
            'stage': a['stage'],
            'placed_at': a['placed_at'],
            'grow_seconds': a['grow_seconds'],
            'collect_cooldown': a['collect_cooldown'],
            'last_fed': a.get('last_fed', 0),
            'fed_boost_until': a.get('fed_boost_until', 0),
            'last_collected': a.get('last_collected', 0),
            'feed_count': a.get('feed_count', 0),
            'collect_count': a.get('collect_count', 0),
            'emoji': info['emoji'],
            'baby_emoji': info['baby_emoji'],
            'product_emoji': info['product_emoji'],
        })
    stats = db.get_ranch_stats(_req_world_id())
    return no_cache(jsonify({
        'ok': True,
        'animals': animal_list,
        'zone': RANCH_ZONE_INFO,
        'stats': {
            'placed': len(animal_list),
            'total_plots': RANCH_ZONE_INFO['total_plots'],
            'empty': RANCH_ZONE_INFO['total_plots'] - len(animal_list),
            'total_collected': stats['total_collected'],
        },
        'animal_types': {k: {'name': v['name'], 'emoji': v['emoji'], 'baby_emoji': v['baby_emoji'],
                              'product': v['product'], 'product_emoji': v['product_emoji'],
                              'cost': v['cost'], 'grow_time': v['grow_time'],
                              'collect_cooldown': v['collect_cooldown']}
                         for k, v in ANIMAL_TYPES.items()}
    }))


@app.route('/api/ranch/place', methods=['POST'])
def api_ranch_place():
    """Place an animal (owner only, costs coins)."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    body = request.get_json(silent=True) or {}
    col = body.get('col')
    row = body.get('row')
    if col is None or row is None:
        return jsonify({'ok': False, 'error': 'col and row required'}), 400
    animal_type = body.get('animal_type', 'chicken')
    if animal_type not in ANIMAL_TYPES:
        return jsonify({'ok': False, 'error': f'Unknown animal type. Valid: {list(ANIMAL_TYPES.keys())}'}), 400
    if not is_in_ranch_zone(col, row):
        return jsonify({'ok': False, 'error': 'Can only place animals in the ranch zone!'}), 400
    info = ANIMAL_TYPES[animal_type]
    # Deduct coins
    success = db.spend_coins(_req_world_id(), info['cost'], f"buy_{animal_type}")
    if not success:
        return jsonify({'ok': False, 'error': f'Not enough coins! Need {info["cost"]} 💎'}), 400
    animal_id = db.place_animal(_req_world_id(), col, row, animal_type, info['grow_time'], info['collect_cooldown'])
    db.add_feed_event(_req_world_id(), 'ranch_place', f"Placed {info['baby_emoji']} baby {info['name']} on the ranch!", '🐣')
    _broadcast_world_event("ranch_event", {'type': 'ranch_place', 'col': col, 'row': row, 'animal_type': animal_type, 'animal_id': animal_id})
    # Track discovery in collection book
    try: db.discover_object(_req_world_id(), animal_type)
    except Exception: pass
    return jsonify({'ok': True, 'animal_id': animal_id, 'animal_type': animal_type,
                    'cost': info['cost'], 'message': f"Placed a baby {info['name']}!"})


@app.route('/api/ranch/feed/<int:animal_id>', methods=['POST'])
def api_ranch_feed(animal_id):
    """Feed an animal — boosts growth/collection speed for 60s."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    animal = db.feed_animal_boost(_req_world_id(), animal_id)
    if not animal:
        return jsonify({'ok': False, 'error': 'Animal not found'}), 400
    info = ANIMAL_TYPES.get(animal['animal_type'], {'emoji': '🐾', 'name': animal['animal_type']})
    _broadcast_world_event("ranch_event", {'type': 'ranch_feed', 'animal_id': animal_id,
               'col': animal['col'], 'row': animal['row']})
    return jsonify({'ok': True, 'animal_id': animal_id, 'message': 'Fed! Growth speed boosted for 60s 🌾'})


@app.route('/api/ranch/feed_all', methods=['POST'])
def api_ranch_feed_all():
    """Feed all animals."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    animals = db.get_animals(_req_world_id())
    fed = []
    for a in animals:
        if a['stage'] != 'ready':
            result = db.feed_animal_boost(_req_world_id(), a['id'])
            if result:
                fed.append(a['id'])
    if fed:
        db.add_feed_event(_req_world_id(), 'ranch_feed', f"Fed {len(fed)} animals 🌾", '🌾')
        _broadcast_world_event("ranch_event", {'type': 'ranch_feed_all', 'count': len(fed)})
    return jsonify({'ok': True, 'fed_count': len(fed), 'animal_ids': fed})


@app.route('/api/ranch/collect/<int:animal_id>', methods=['POST'])
def api_ranch_collect(animal_id):
    """Collect product from a ready animal."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    animal = db.collect_animal_product(_req_world_id(), animal_id)
    if not animal:
        return jsonify({'ok': False, 'error': 'Animal not ready or not found'}), 400
    info = ANIMAL_TYPES.get(animal['animal_type'], {'name': animal['animal_type'], 'product_emoji': '📦', 'product': 'Product', 'xp': 5, 'coins': 10})
    coins_earned = info['coins']
    db.record_progress_event(_req_world_id(), 'place_object')
    db.earn_coins(_req_world_id(), coins_earned, f"collect_{animal['animal_type']}")
    db.add_feed_event(_req_world_id(), 'ranch_collect', f"Collected {info['product_emoji']} {info['product']} from {info['name']}! (+{info['xp']} XP, +{coins_earned} 💎)", '🎉')
    _broadcast_world_event("ranch_event", {'type': 'ranch_collect', 'animal_id': animal_id,
               'animal_type': animal['animal_type'], 'col': animal['col'], 'row': animal['row']})
    return jsonify({'ok': True, 'animal_id': animal_id, 'animal_type': animal['animal_type'],
                    'product': info['product'], 'product_emoji': info['product_emoji'],
                    'xp_earned': info['xp'], 'coins_earned': coins_earned})


@app.route('/api/ranch/collect_all', methods=['POST'])
def api_ranch_collect_all():
    """Collect products from all ready animals."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    animals = db.get_animals(_req_world_id())
    collected = []
    total_xp = 0
    total_coins = 0
    for a in animals:
        if a['stage'] == 'ready':
            result = db.collect_animal_product(_req_world_id(), a['id'])
            if result:
                info = ANIMAL_TYPES.get(a['animal_type'], {'xp': 5, 'coins': 10, 'product_emoji': '📦', 'product': 'Product', 'name': a['animal_type']})
                total_xp += info['xp']
                total_coins += info['coins']
                db.record_progress_event(_req_world_id(), 'place_object')
                db.earn_coins(_req_world_id(), info['coins'], f"collect_{a['animal_type']}")
                collected.append({'animal_id': a['id'], 'animal_type': a['animal_type']})
    if collected:
        db.add_feed_event(_req_world_id(), 'ranch_collect', f"Collected from {len(collected)} animals! (+{total_xp} XP, +{total_coins} coins)", '🎉')
        _broadcast_world_event("ranch_event", {'type': 'ranch_collect_all', 'count': len(collected)})
    return jsonify({'ok': True, 'collected_count': len(collected), 'collected': collected,
                    'total_xp': total_xp, 'total_coins': total_coins})


# ── Social Feed API ────────────────────────────────────────────

@app.route('/api/feed', methods=['GET'])
def api_feed():
    """Get recent farm events feed."""
    limit = int(request.args.get('limit', 30))
    events = db.get_feed_events(_req_world_id(), min(limit, 100))
    return no_cache(jsonify({'ok': True, 'events': events}))

# ── Global Activity Feed (cross-island) ───────────────────────

_activity_cache = {'data': None, 'ts': 0}

@app.route('/api/activity', methods=['GET'])
def api_activity():
    """Get recent activity across ALL islands for the lobby page."""
    limit = min(int(request.args.get('limit', 20)), 50)

    # Return cached result if fresh (60s TTL)
    now = time.time()
    if _activity_cache['data'] is not None and now - _activity_cache['ts'] < 60:
        cached = _activity_cache['data']
        return no_cache(jsonify({'ok': True, 'events': cached[:limit]}))

    events = []
    conn = db.get_conn()
    try:
        # 1) New islands
        rows = conn.execute(
            "SELECT w.id, w.name, w.owner, w.created_at, w.island_type, i.avatar "
            "FROM worlds w LEFT JOIN islands i ON w.id = i.id "
            "ORDER BY w.created_at DESC LIMIT 10"
        ).fetchall()
        for r in rows:
            if not r['created_at']:
                continue
            events.append({
                'type': 'new_island',
                'world_id': r['id'],
                'island_name': r['name'] or 'Unnamed',
                'owner_name': r['name'] or 'Unnamed',
                'owner_avatar': r['avatar'] or '🦞',
                'island_type': r['island_type'] or 'farm',
                'time': r['created_at'],
                'text': f"New island created: {r['name'] or 'Unnamed'}",
            })

        # 2) Guestbook entries
        rows = conn.execute(
            "SELECT g.world_id, g.author_name, g.author_avatar, g.message, g.created_at, "
            "w.name as island_name "
            "FROM guestbook g LEFT JOIN worlds w ON g.world_id = w.id "
            "ORDER BY g.created_at DESC LIMIT 10"
        ).fetchall()
        for r in rows:
            if not r['created_at']:
                continue
            events.append({
                'type': 'guestbook',
                'world_id': r['world_id'],
                'island_name': r['island_name'] or 'Unknown',
                'author_name': r['author_name'] or 'Visitor',
                'author_avatar': r['author_avatar'] or '🦞',
                'message': (r['message'] or '')[:100],
                'time': r['created_at'],
                'text': f"{r['author_name'] or 'Visitor'} left a message on {r['island_name'] or 'Unknown'}",
            })

        # 3) High-level islands (top 5)
        rows = conn.execute(
            "SELECT p.world_id, p.level, p.updated_at, w.name, w.owner "
            "FROM user_progress p LEFT JOIN worlds w ON p.world_id = w.id "
            "WHERE p.level >= 5 ORDER BY p.level DESC LIMIT 5"
        ).fetchall()
        for r in rows:
            ts = r['updated_at'] or ''
            events.append({
                'type': 'level_up',
                'world_id': r['world_id'],
                'island_name': r['name'] or 'Unnamed',
                'owner_name': r['owner'] or 'anonymous',
                'level': r['level'],
                'time': ts,
                'text': f"{r['name'] or 'Unnamed'} reached Level {r['level']}!",
            })

        # 4) Object milestones (islands that crossed 50/100/200/500)
        rows = conn.execute(
            "SELECT p.world_id, p.objects_placed, p.updated_at, w.name "
            "FROM user_progress p LEFT JOIN worlds w ON p.world_id = w.id "
            "WHERE p.objects_placed >= 50 ORDER BY p.objects_placed DESC LIMIT 10"
        ).fetchall()
        milestones = [500, 200, 100, 50]
        for r in rows:
            placed = r['objects_placed'] or 0
            # Find highest milestone crossed
            hit = None
            for m in milestones:
                if placed >= m:
                    hit = m
                    break
            if hit:
                events.append({
                    'type': 'milestone',
                    'world_id': r['world_id'],
                    'island_name': r['name'] or 'Unnamed',
                    'objects_placed': hit,
                    'time': r['updated_at'] or '',
                    'text': f"{r['name'] or 'Unnamed'} reached {hit} objects!",
                })
    except Exception:
        pass
    finally:
        conn.close()

    # Sort by time descending (handle empty strings)
    events.sort(key=lambda e: e.get('time', '') or '', reverse=True)

    # Cache the full result
    _activity_cache['data'] = events
    _activity_cache['ts'] = now

    return no_cache(jsonify({'ok': True, 'events': events[:limit]}))

# ── Leaderboard API ───────────────────────────────────────────

_leaderboard_cache = {'data': {}, 'ts': {}}

@app.route('/api/leaderboard')
def api_leaderboard():
    category = request.args.get('category', 'level')
    limit = min(int(request.args.get('limit', 10)), 20)

    # Return cached result if fresh (60s TTL)
    now = time.time()
    cache_key = f'{category}_{limit}'
    if cache_key in _leaderboard_cache['data'] and now - _leaderboard_cache['ts'].get(cache_key, 0) < 60:
        cached = _leaderboard_cache['data'][cache_key]
        return no_cache(jsonify(cached))

    conn = db.get_conn()

    # Security: ORDER BY whitelist — only predefined sort orders allowed
    ALLOWED_LEADERBOARD_ORDERS = {
        'level': 'COALESCE(up.level, 1) DESC, COALESCE(up.objects_placed, 0) DESC',
        'visits': 'visit_count DESC',
        'objects': 'COALESCE(up.objects_placed, 0) DESC',
        'newest': 'w.created_at DESC'
    }
    if category not in ALLOWED_LEADERBOARD_ORDERS:
        category = 'level'
    order = ALLOWED_LEADERBOARD_ORDERS[category]

    try:
        rows = conn.execute(f'''
            SELECT w.id, w.name, w.owner, w.island_type, w.created_at,
                   COALESCE(up.level, 1) as level,
                   COALESCE(up.objects_placed, 0) as objects_placed,
                   COALESCE(u.name, 'Anonymous') as owner_name,
                   COALESCE(u.avatar, '🦞') as owner_avatar,
                   (SELECT COUNT(*) FROM page_views pv WHERE pv.world_id = w.id) as visit_count
            FROM worlds w
            LEFT JOIN user_progress up ON w.id = up.world_id
            LEFT JOIN users u ON w.owner = u.id
            ORDER BY {order}
            LIMIT ?
        ''', (limit,)).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()

    leaders = []
    for i, r in enumerate(rows):
        leaders.append({
            'rank': i + 1,
            'world_id': r[0],
            'name': r[1] or 'Unnamed',
            'owner_name': r[7],
            'owner_avatar': r[8],
            'island_type': r[3] or 'farm',
            'level': r[5],
            'visit_count': r[9],
            'objects_placed': r[6],
            'created_at': r[4]
        })

    result = {'category': category, 'leaders': leaders}

    # Cache the result
    _leaderboard_cache['data'][cache_key] = result
    _leaderboard_cache['ts'][cache_key] = now

    resp = jsonify(result)
    return no_cache(resp)

# ── Turnip Market API ─────────────────────────────────────────

def get_turnip_price(day_str=None):
    """Get deterministic daily turnip price using md5 seed."""
    if day_str is None:
        day_str = datetime.now(timezone.utc).strftime('%Y-%W-%u')  # year-week-weekday
    seed = hashlib.md5(f"turnip-{day_str}".encode()).hexdigest()
    # Price range: 50-500 bells
    base = int(seed[:4], 16) % 451 + 50
    return base

def get_weekly_prices():
    """Get Mon-Sun prices for the current week."""
    now = datetime.now(timezone.utc)
    year_week = now.strftime('%Y-%W')
    prices = []
    for day in range(1, 8):  # Mon=1 to Sun=7
        day_str = f"{year_week}-{day}"
        prices.append({'day': day, 'price': get_turnip_price(day_str)})
    return prices

@app.route('/api/turnips', methods=['GET'])
def api_turnips():
    """Main turnips endpoint — alias for turnip price info."""
    today = datetime.now(timezone.utc).strftime('%Y-%W-%u')
    price = get_turnip_price(today)
    weekly = get_weekly_prices()
    turnips = db.get_player_turnips(_req_world_id())
    return no_cache(jsonify({
        'ok': True,
        'today': today,
        'price': price,
        'weekly': weekly,
        'player_turnips': turnips
    }))

@app.route('/api/turnip/price', methods=['GET'])
def api_turnip_price():
    """Get today's turnip price."""
    today = datetime.now(timezone.utc).strftime('%Y-%W-%u')
    price = get_turnip_price(today)
    weekly = get_weekly_prices()
    turnips = db.get_player_turnips(_req_world_id())
    return no_cache(jsonify({
        'ok': True,
        'today': today,
        'price': price,
        'weekly': weekly,
        'player_turnips': turnips
    }))

@app.route('/api/turnip/buy', methods=['POST'])
def api_turnip_buy():
    """Buy turnips (owner only, Sunday only for full price)."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    body = request.get_json(silent=True) or {}
    amount = int(body.get('amount', 10))
    if amount < 1:
        return jsonify({'ok': False, 'error': 'Amount must be positive'}), 400
    today = datetime.now(timezone.utc).strftime('%Y-%W-%u')
    price = get_turnip_price(today)
    current = db.get_player_turnips(_req_world_id())
    new_amount = current['amount'] + amount
    db.set_player_turnips(_req_world_id(), new_amount, price, today)
    db.add_feed_event(_req_world_id(), 'turnip_buy',
        f"Bought {amount} turnips at {price} bells each", '📈')
    return jsonify({'ok': True, 'bought': amount, 'price': price,
                    'total_turnips': new_amount, 'cost': amount * price})

@app.route('/api/turnip/sell', methods=['POST'])
def api_turnip_sell():
    """Sell turnips at today's price."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    body = request.get_json(silent=True) or {}
    current = db.get_player_turnips(_req_world_id())
    amount = int(body.get('amount', current['amount']))
    if amount > current['amount']:
        return jsonify({'ok': False, 'error': 'Not enough turnips'}), 400
    today = datetime.now(timezone.utc).strftime('%Y-%W-%u')
    price = get_turnip_price(today)
    revenue = amount * price
    profit = revenue - (amount * current.get('bought_price', 0))
    new_amount = current['amount'] - amount
    db.set_player_turnips(_req_world_id(), new_amount, current.get('bought_price', 0), current.get('bought_day', ''))
    emoji = '📈' if profit >= 0 else '📉'
    db.add_feed_event(_req_world_id(), 'turnip_sell',
        f"Sold {amount} turnips at {price} bells. Profit: {profit:+d}", emoji)
    return jsonify({'ok': True, 'sold': amount, 'price': price, 'revenue': revenue,
                    'profit': profit, 'remaining_turnips': new_amount})

# ── Claw Autonomous Behavior ──────────────────────────────────

@app.route('/api/claw/action', methods=['GET'])
def api_claw_action():
    """Check game state and return recommended claw action."""
    # Visitor mode: show visitor-appropriate messages instead of owner actions
    if request.args.get('visitor') == '1':
        crops = db.get_crops(_req_world_id())
        animals = db.get_animals(_req_world_id())
        obj_count = len(crops) + len(animals)
        if obj_count >= 5:
            message = f"🦞 *scuttles excitedly* Welcome! This island has {obj_count} buildings & items to discover!"
            animation = 'bounce'
        elif obj_count > 0:
            message = "🦞 *waves claw* Welcome! Click on buildings and items to interact with them!"
            animation = 'wander'
        else:
            message = "🦞 *bubbles happily* Welcome! Enjoy your visit! 🏝️"
            animation = 'idle'
        return no_cache(jsonify({
            'ok': True,
            'action': 'visitor_welcome',
            'message': message,
            'animation': animation,
            'ripe_count': 0,
            'growing_count': 0,
            'recent_steal': False,
        }))

    crops = db.get_crops(_req_world_id())
    ripe_crops = [c for c in crops if c['stage'] == 'ripe']
    growing_crops = [c for c in crops if c['stage'] in ('seedling', 'growing')]
    feed = db.get_feed_events(_req_world_id(), 5)
    recent_steal = any(e['event_type'] == 'steal' for e in feed)
    progress = db.get_progress(_req_world_id()) or {}

    # Decision tree
    if recent_steal:
        action = 'guard'
        message = "🦞 *clacks claws aggressively* Thief detected! My crops!"
        animation = 'shake'
    elif ripe_crops:
        action = 'harvest_reminder'
        message = f"🦞 *waves claw* {len(ripe_crops)} crop(s) are ready to harvest!"
        animation = 'bounce'
    elif growing_crops:
        # Claw waters crops
        action = 'tend'
        message = f"🦞 *sprinkles water* Tending to {len(growing_crops)} growing crop(s)..."
        animation = 'idle'
    elif not crops:
        action = 'idle_farm'
        message = "🦞 *looks at empty field* The farm is empty. Time to plant something!"
        animation = 'idle'
    else:
        action = 'wander'
        message = "🦞 *scuttles around* All is well on the island!"
        animation = 'wander'

    return no_cache(jsonify({
        'ok': True,
        'action': action,
        'message': message,
        'animation': animation,
        'ripe_count': len(ripe_crops),
        'growing_count': len(growing_crops),
        'recent_steal': recent_steal,
    }))

# ── Daily Bulletin (Sign Board) ───────────────────────────────

_daily_bulletin_cache = {'date': '', 'message': ''}

def generate_daily_bulletin():
    """Generate today's farm bulletin."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if _daily_bulletin_cache['date'] == today:
        return _daily_bulletin_cache['message']
    
    crops = db.get_crops('default')
    feed = db.get_feed_events('default', 10)
    today_feed = [e for e in feed if
                  datetime.fromtimestamp(e['ts'], timezone.utc).strftime('%Y-%m-%d') == today]
    
    # Build bulletin
    lines = [f"📋 Daily Report — {today}"]
    if crops:
        ripe = len([c for c in crops if c['stage'] == 'ripe'])
        growing = len([c for c in crops if c['stage'] != 'ripe'])
        lines.append(f"🌱 Farm: {ripe} ripe, {growing} growing")
    else:
        lines.append("🌱 Farm: Empty field")
    
    steals = [e for e in today_feed if e['event_type'] == 'steal']
    if steals:
        lines.append(f"🦹 {len(steals)} theft(s) today!")
    else:
        lines.append("✅ No thefts today")
    
    price = get_turnip_price()
    lines.append(f"📈 Turnips: {price} bells/pc")
    
    msg = " | ".join(lines)
    _daily_bulletin_cache['date'] = today
    _daily_bulletin_cache['message'] = msg
    
    # Save to island story daily_message
    story = db.get_story('default') or {}
    db.set_story('default', story.get('bio', ''), msg)
    
    return msg

@app.route('/api/island/story', methods=['POST'])
def api_island_story():
    """Set the island's daily message/story."""
    data = request.get_json(force=True) or {}
    msg = (data.get('daily_message') or '').strip()[:200]
    if not msg:
        return jsonify({'ok': False, 'error': 'No message provided'}), 400
    # Store in DB or file
    story_file = os.path.join(BASE, 'backend', 'island_story.json')
    import json as _json
    story_data = {'daily_message': msg, 'ts': datetime.now(timezone.utc).isoformat()}
    with open(story_file, 'w') as f:
        _json.dump(story_data, f)
    return jsonify({'ok': True})

@app.route('/api/bulletin', methods=['GET'])
def api_bulletin():
    """Get today's daily bulletin."""
    msg = generate_daily_bulletin()
    return no_cache(jsonify({'ok': True, 'message': msg,
                             'date': datetime.now(timezone.utc).strftime('%Y-%m-%d')}))

# Generate bulletin on startup
generate_daily_bulletin()

# ── Daily Spin / Raid / Attack System ─────────────────────────
import random as _rnd

# ── Notification Visit Dedup (in-memory, 10 min TTL) ─────────
_visit_notif_cache = {}  # key: (world_id, ip) → timestamp
_VISIT_NOTIF_TTL = 600  # 10 minutes

def _should_notify_visit(world_id, ip):
    """Return True if we should send a visit notification (dedup 10 min per IP)."""
    now = time.time()
    key = (world_id, ip)
    last = _visit_notif_cache.get(key, 0)
    if now - last < _VISIT_NOTIF_TTL:
        return False
    _visit_notif_cache[key] = now
    # Cleanup old entries periodically (every ~100 checks)
    if len(_visit_notif_cache) > 500:
        cutoff = now - _VISIT_NOTIF_TTL
        stale = [k for k, v in _visit_notif_cache.items() if v < cutoff]
        for k in stale:
            del _visit_notif_cache[k]
    return True

SPIN_RESULTS = [
    ('coins',  25),  # 25% chance
    ('attack', 20),  # 20% — more combat!
    ('raid',   18),  # 18%
    ('shield', 15),
    ('seed',   12),
    ('crit',   10),
]
MAX_DAILY_SPINS = 5  # 5 spins per day

# Anti-stacking: max tokens you can hold at once
MAX_ATTACK_TOKENS = 8
MAX_RAID_TOKENS = 8
# Anti-grief: max attacks one person can receive per day (raised for more action)
MAX_ATTACKS_RECEIVED_PER_DAY = 10

@app.route('/api/spin/status', methods=['GET'])
def api_spin_status():
    """Get current spin status: remaining spins, shields, tokens, etc."""
    wid = _req_world_id()
    # If user is logged in, show their tokens regardless of which world they're viewing
    user = _get_current_user()
    my_world = None
    tokens = {'attack': 0, 'raid': 0}
    if user:
        my_world = db.get_user_world_id(user['id'])
        if not my_world and user.get('email') == ERIC_EMAIL:
            my_world = 'default'
        if my_world:
            tokens = db.get_tokens(my_world)
    
    used = db.get_spins_today(my_world or wid)
    shields = db.get_shields(wid)
    destroyed = db.get_destroyed_objects(wid)
    recent_raids = db.get_recent_raids(wid, 5)
    recent_attacks = db.get_recent_attacks(wid, 5)
    return no_cache(jsonify({
        'spins_remaining': max(0, MAX_DAILY_SPINS - used),
        'spins_used': used,
        'max_spins': MAX_DAILY_SPINS,
        'shields': shields,
        'max_shields': 3,
        'tokens': tokens,
        'max_tokens': {'attack': MAX_ATTACK_TOKENS, 'raid': MAX_RAID_TOKENS},
        'destroyed_objects': destroyed,
        'recent_raids': recent_raids,
        'recent_attacks': recent_attacks,
        'my_world': my_world,
    }))

@app.route('/api/spin', methods=['POST'])
def api_spin():
    """Use a daily spin. Returns the result."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Must be logged in as owner'}), 403
    wid = _req_world_id()
    used = db.get_spins_today(wid)
    if used >= MAX_DAILY_SPINS:
        return jsonify({'ok': False, 'error': 'No spins left today! Come back tomorrow.'}), 429

    # Weighted random result
    roll = _rnd.randint(1, 100)
    cumulative = 0
    result_type = 'coins'
    for rtype, weight in SPIN_RESULTS:
        cumulative += weight
        if roll <= cumulative:
            result_type = rtype
            break

    user = _get_current_user()
    user_name = user['name'] if user else 'Anonymous'
    response = {'ok': True, 'result': result_type}

    if result_type == 'coins':
        amount = _rnd.randint(20, 100)
        db.earn_coins(wid, amount, 'daily_spin')
        db.record_spin(wid, 'coins', amount)
        response['coins'] = amount
        response['message'] = f'💎 You found {amount} coins!'

    elif result_type == 'crit':
        amount = _rnd.randint(80, 200)
        db.earn_coins(wid, amount, 'daily_spin_crit')
        db.record_spin(wid, 'crit', amount)
        response['coins'] = amount
        response['message'] = f'⭐ CRITICAL! {amount} coins!'

    elif result_type == 'shield':
        new_count = db.add_shield(wid)
        db.record_spin(wid, 'shield', 1)
        response['shields'] = new_count
        response['message'] = f'🛡 Shield activated! ({new_count}/3)'

    elif result_type == 'seed':
        # Give a random premium seed worth
        seed_coins = _rnd.randint(15, 40)
        db.earn_coins(wid, seed_coins, 'daily_spin_seed')
        db.record_spin(wid, 'seed', seed_coins)
        response['coins'] = seed_coins
        response['message'] = f'🌱 Found a rare seed! Worth {seed_coins} coins'

    elif result_type == 'attack':
        tokens = db.get_tokens(wid)
        if tokens['attack'] >= MAX_ATTACK_TOKENS:
            # Already at max — convert to coins instead
            bonus = _rnd.randint(30, 60)
            db.earn_coins(wid, bonus, 'attack_overflow')
            db.record_spin(wid, 'attack_overflow', bonus)
            response['coins'] = bonus
            response['message'] = f'🔨 Attack bag full! Converted to {bonus} coins instead.'
        else:
            db.add_token(wid, 'attack')
            db.record_spin(wid, 'attack', 1)
            tokens = db.get_tokens(wid)
            response['tokens'] = tokens
            response['message'] = f'🔨 Attack token! ({tokens["attack"]}/{MAX_ATTACK_TOKENS}) Visit a world and click a building!'

    elif result_type == 'raid':
        tokens = db.get_tokens(wid)
        if tokens['raid'] >= MAX_RAID_TOKENS:
            bonus = _rnd.randint(30, 60)
            db.earn_coins(wid, bonus, 'raid_overflow')
            db.record_spin(wid, 'raid_overflow', bonus)
            response['coins'] = bonus
            response['message'] = f'💰 Raid bag full! Converted to {bonus} coins instead.'
        else:
            db.add_token(wid, 'raid')
            db.record_spin(wid, 'raid', 1)
            tokens = db.get_tokens(wid)
            response['tokens'] = tokens
            response['message'] = f'💰 Raid token! ({tokens["raid"]}/{MAX_RAID_TOKENS}) Visit a world and steal coins!'

    response['spins_remaining'] = max(0, MAX_DAILY_SPINS - used - 1)
    return jsonify(response)

@app.route('/api/spin/raid', methods=['POST'])
def api_spin_raid():
    """Execute a raid: dig for coins on someone's world.
    Requires a raid token. User clicks dig spots on the island."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Must be logged in'}), 403

    body = request.get_json(silent=True) or {}
    target = body.get('target_world', '')
    if not target:
        return jsonify({'ok': False, 'error': 'target_world required'}), 400

    my_world = db.get_user_world_id(user['id'])
    if not my_world and user.get('email') == ERIC_EMAIL:
        my_world = 'default'
    if target == my_world:
        return jsonify({'ok': False, 'error': "Can't raid yourself!"}), 400

    # Check token
    if not db.use_token(my_world, 'raid'):
        return jsonify({'ok': False, 'error': 'No raid tokens! Spin the wheel first.'}), 400

    raider_name = user['name']

    # Check shields
    if db.use_shield(target):
        db.record_raid(my_world, raider_name, target, 0, blocked=True)
        db.add_feed_event(target, 'raid_blocked',
            f'🛡 {raider_name} tried to raid but was blocked by a shield!', '🛡')
        return jsonify({'ok': True, 'blocked': True,
                        'message': '🛡 Blocked! They had a shield!',
                        'tokens': db.get_tokens(my_world)})

    # Steal 10-30% of target's coins (max 200)
    target_wallet = db.get_wallet(target)
    target_coins = target_wallet.get('coins', 0)
    steal_pct = _rnd.randint(30, 50) / 100.0  # Steal 30-50% — hurts!
    stolen = min(int(target_coins * steal_pct), 500)  # Cap at 500
    stolen = max(stolen, 10)  # Minimum 10 even if they're poor

    if stolen > 0:
        db.spend_coins(target, stolen, f'raided_by_{my_world}')
        db.earn_coins(my_world, stolen, f'raid_{target}')

    db.record_raid(my_world, raider_name, target, stolen)
    db.add_feed_event(target, 'raided',
        f'💰 {raider_name} raided and stole {stolen} coins!', '💰')
    db.add_feed_event(my_world, 'raid_success',
        f'💰 Raided and got {stolen} coins!', '💰')
    # Notify raid target
    try:
        target_owner = db.get_world_owner(target)
        if target_owner:
            db.create_notification(
                target_owner, 'raid',
                f'💰 {raider_name} raided your island and stole {stolen} coins!',
                island_id=target,
                from_user=user['id'] if user else None
            )
    except Exception:
        pass

    return jsonify({'ok': True, 'blocked': False, 'coins_stolen': stolen,
                    'message': f'💰 Stole {stolen} coins!',
                    'tokens': db.get_tokens(my_world)})

@app.route('/api/spin/attack', methods=['POST'])
def api_spin_attack():
    """Execute an attack: destroy a specific object on someone's world.
    Requires an attack token. User clicks the object they want to destroy."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Must be logged in'}), 403
    
    body = request.get_json(silent=True) or {}
    target = body.get('target_world', '')
    object_id = body.get('object_id', '')  # specific object to destroy
    if not target:
        return jsonify({'ok': False, 'error': 'target_world required'}), 400

    my_world = db.get_user_world_id(user['id'])
    if not my_world and user.get('email') == ERIC_EMAIL:
        my_world = 'default'
    if target == my_world:
        return jsonify({'ok': False, 'error': "Can't attack yourself!"}), 400

    # Check token
    if not db.use_token(my_world, 'attack'):
        return jsonify({'ok': False, 'error': 'No attack tokens! Spin the wheel first.'}), 400

    # Anti-grief: check how many attacks target has received today
    today_attacks = db.get_recent_attacks(target, limit=50)
    from datetime import datetime as _dt
    today_start = _dt.now(timezone.utc).replace(hour=0,minute=0,second=0).timestamp()
    today_count = sum(1 for a in today_attacks if a.get('ts', 0) >= today_start and not a.get('blocked_by_shield'))
    if today_count >= MAX_ATTACKS_RECEIVED_PER_DAY:
        # Refund the token
        db.add_token(my_world, 'attack')
        return jsonify({'ok': False, 'error': 'This world has been attacked too many times today. Try again tomorrow!',
                        'tokens': db.get_tokens(my_world)}), 429

    attacker_name = user['name']

    # Check shields
    if db.use_shield(target):
        db.record_attack(my_world, attacker_name, target, blocked=True)
        db.add_feed_event(target, 'attack_blocked',
            f'🛡 {attacker_name} attacked but was blocked by a shield!', '🛡')
        return jsonify({'ok': True, 'blocked': True,
                        'message': '🛡 Blocked! They had a shield!',
                        'tokens': db.get_tokens(my_world)})

    target_world = db.load_world(target)
    if not target_world:
        return jsonify({'ok': False, 'error': 'World not found'}), 404

    objects = target_world.get('objects', [])
    already_destroyed = {d['object_id'] for d in db.get_destroyed_objects(target)}

    # If user specified an object, destroy that one; otherwise random
    victim = None
    if object_id:
        victim = next((o for o in objects if o['id'] == object_id 
                       and o['id'] not in already_destroyed
                       and o.get('type') not in ('house_cottage', 'house_cottage_ai')), None)
    
    if not victim:
        # Random fallback
        destroyable = [o for o in objects if o.get('type') not in ('house_cottage', 'house_cottage_ai')
                       and o['id'] not in already_destroyed]
        if not destroyable:
            db.record_attack(my_world, attacker_name, target, 'nothing', 0)
            return jsonify({'ok': True, 'blocked': False, 'nothing': True,
                            'message': '🔨 Nothing to destroy!', 'tokens': db.get_tokens(my_world)})
        victim = _rnd.choice(destroyable)

    # BLAST ZONE: destroy the target + 1-2 nearby objects (splash damage!)
    destroyable_all = [o for o in objects if o.get('type') not in ('house_cottage', 'house_cottage_ai')
                       and o['id'] not in already_destroyed]
    
    # Find objects near the victim (within 3 tile radius)
    vc, vr = victim.get('col', 0), victim.get('row', 0)
    nearby = [o for o in destroyable_all if o['id'] != victim['id']
              and abs(o.get('col', 0) - vc) <= 3 and abs(o.get('row', 0) - vr) <= 3]
    
    # Blast: victim + 1-2 random nearby
    bonus_count = min(len(nearby), _rnd.randint(1, 2))
    blast_victims = [victim] + _rnd.sample(nearby, bonus_count) if nearby else [victim]
    
    total_cost = 0
    destroyed_list = []
    for v in blast_victims:
        cost = TILE_COSTS.get(v['type'], 10)
        total_cost += cost
        db.add_destroyed_object(target, v['id'], v['type'],
                                 v.get('col', 0), v.get('row', 0), cost, attacker_name)
        destroyed_list.append({'id': v['id'], 'type': v['type'], 'col': v.get('col', 0), 'row': v.get('row', 0)})
        # Remove from world data
        target_world['objects'] = [o for o in target_world.get('objects', []) if o['id'] != v['id']]
        # Broadcast each destruction
        _broadcast_world_event('object_destroyed', {
            'object_id': v['id'], 'object_type': v['type'],
            'col': v.get('col', 0), 'row': v.get('row', 0),
            'attacker': attacker_name, 'repair_cost': cost
        })
    
    _save_world_data(target, target_world)
    db.record_attack(my_world, attacker_name, target,
                     ','.join(d['type'] for d in destroyed_list), total_cost)
    db.add_feed_event(target, 'attacked',
        f'💥 {attacker_name} BOMBED your island! {len(destroyed_list)} buildings destroyed! Repair cost: {total_cost} 💎', '💥')

    return jsonify({'ok': True, 'blocked': False,
                    'destroyed_list': destroyed_list,
                    'destroyed': destroyed_list[0]['type'],
                    'object_id': destroyed_list[0]['id'],
                    'col': destroyed_list[0]['col'], 'row': destroyed_list[0]['row'],
                    'total_destroyed': len(destroyed_list),
                    'repair_cost': total_cost,
                    'message': f'💥 BOOM! Destroyed {len(destroyed_list)} buildings!',
                    'tokens': db.get_tokens(my_world)})

@app.route('/api/spin/repair', methods=['POST'])
def api_spin_repair():
    """Repair a destroyed object."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Not authorized'}), 403
    body = request.get_json(silent=True) or {}
    destroyed_id = body.get('id')
    if not destroyed_id:
        return jsonify({'ok': False, 'error': 'id required'}), 400

    wid = _req_world_id()
    destroyed = db.get_destroyed_objects(wid)
    target = None
    for d in destroyed:
        if d['id'] == destroyed_id:
            target = d
            break
    if not target:
        return jsonify({'ok': False, 'error': 'Not found'}), 404

    cost = target['repair_cost']
    result = db.spend_coins(wid, cost, f'repair_{target["object_type"]}')
    if not result['ok']:
        return jsonify({'ok': False, 'error': f'Need {cost} coins to repair'}), 400

    db.repair_object(destroyed_id)
    return jsonify({'ok': True, 'repaired': target['object_type'], 'cost': cost,
                    'remaining_coins': result['remaining']})

@app.route('/api/spin/bonus', methods=['POST'])
def api_spin_bonus():
    """Admin: distribute bonus tokens to all users. Internal only."""
    if not _is_internal_request():
        return jsonify({'ok': False, 'error': 'Internal only'}), 403
    body = request.get_json(silent=True) or {}
    attack_bonus = body.get('attack', 2)
    raid_bonus = body.get('raid', 2)
    shield_bonus = body.get('shield', 1)
    coin_bonus = body.get('coins', 0)
    message = body.get('message', '🎁 Bonus drop!')
    
    users = auth.list_users()
    count = 0
    for u in users:
        wid = db.get_user_world_id(u['id'])
        if not wid and u.get('email') == ERIC_EMAIL:
            wid = 'default'
        if wid:
            tokens = db.get_tokens(wid)
            # Only give if below max
            if tokens['attack'] < MAX_ATTACK_TOKENS and attack_bonus > 0:
                db.add_token(wid, 'attack', min(attack_bonus, MAX_ATTACK_TOKENS - tokens['attack']))
            if tokens['raid'] < MAX_RAID_TOKENS and raid_bonus > 0:
                db.add_token(wid, 'raid', min(raid_bonus, MAX_RAID_TOKENS - tokens['raid']))
            if shield_bonus > 0:
                db.add_shield(wid, shield_bonus)
            if coin_bonus > 0:
                db.earn_coins(wid, coin_bonus, 'bonus_drop')
            db.add_feed_event(wid, 'bonus', message, '🎁')
            count += 1
    
    return jsonify({'ok': True, 'users_gifted': count, 'message': message})

# Chat system removed — will use Genspark Teams for user feedback


# ── Land Expansion API ─────────────────────────────────────────
# Lets players upgrade their island size by spending coins

@app.route('/api/land')
def api_land():
    """Get current land level, size, farm plots, and next upgrade info."""
    wid = _req_world_id()
    land = db.get_land_level(wid)
    wallet = db.get_wallet(wid)
    land['coins'] = wallet['coins']
    return no_cache(jsonify(land))

@app.route('/api/land/upgrade', methods=['POST'])
def api_land_upgrade():
    """Upgrade land to next level (owner only, costs coins)."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    result = db.upgrade_land(wid)
    if result['ok']:
        db.add_feed_event(wid, 'land_upgrade',
            f"🏝️ Island expanded to {result['name']}! (size {result['size']}x{result['size']})", '🏝️')
        _broadcast_world_event('land_upgrade', {
            'level': result['new_level'],
            'name': result['name'],
            'size': result['size'],
            'farm_plots': result['farm_plots'],
        })
    return jsonify(result)


# ══════════════════════════════════════════════════════════════
# ── Economy System APIs ───────────────────────────────────────
# ══════════════════════════════════════════════════════════════

# ── Island Type ───────────────────────────────────────────────
@app.route('/api/economy/crop-types')
def api_economy_crop_types():
    """Get available crop types for this island, organized by tier."""
    wid = _req_world_id()
    island_type = db.get_island_type(wid)
    resources = db.ISLAND_RESOURCES.get(island_type, db.ISLAND_RESOURCES['farm'])
    result = {'island_type': island_type, 'tiers': {}}
    for tier_name in ['primary', 'secondary', 'weak']:
        tier_crops = []
        for res in resources.get(tier_name, []):
            if res in CROP_TYPES:
                info = CROP_TYPES[res]
                mult = db.RESOURCE_YIELD.get(tier_name, 1.0)
                tier_crops.append({
                    'id': res, 'name': info['name'], 'emoji': info['emoji'],
                    'growth_time': info['growth_time'], 'coins': info['coins'],
                    'yield': max(1, int(mult)), 'tier': tier_name,
                })
        result['tiers'][tier_name] = tier_crops
    # Island type display info
    type_info = {
        'farm': {'label': 'Farm', 'icon': '🌾', 'enter_label': '🌾 FARM', 'subtitle': 'Click to Enter', 'color': '#8f8'},
        'fish': {'label': 'Dock', 'icon': '🌊', 'enter_label': '🌊 DOCK', 'subtitle': 'Cast your nets', 'color': '#8cf'},
        'mine': {'label': 'Mine', 'icon': '⛏️', 'enter_label': '⛏️ MINE', 'subtitle': 'Dig for ore', 'color': '#da8'},
        'forest': {'label': 'Lodge', 'icon': '🌲', 'enter_label': '🌲 LODGE', 'subtitle': 'Harvest the woods', 'color': '#8d8'},
    }
    result['display'] = type_info.get(island_type, type_info['farm'])
    return no_cache(jsonify(result))

@app.route('/api/economy/island-type')
def api_island_type():
    """Get island type and resource info."""
    wid = _req_world_id()
    itype = db.get_island_type(wid)
    resources = db.ISLAND_RESOURCES.get(itype, db.ISLAND_RESOURCES['farm'])
    return no_cache(jsonify({
        'type': itype,
        'primary': resources['primary'],
        'secondary': resources['secondary'],
        'weak': resources['weak'],
        'emojis': db.RESOURCE_EMOJIS,
        'stage_emojis': db.RESOURCE_STAGE_EMOJIS.get(itype, db.RESOURCE_STAGE_EMOJIS['farm']),
    }))

@app.route('/api/economy/assign-island', methods=['POST'])
def api_island_assign():
    """Assign random island type (called on first load if not set)."""
    wid = _req_world_id()
    itype = db.assign_random_island_type(wid)
    return jsonify({'ok': True, 'type': itype})

@app.route('/api/economy/switch-island', methods=['POST'])
def api_island_switch():
    """Switch island type (requires Lv4+)."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    progress = db.get_progress(wid)
    if not progress or progress['level'] < 4:
        return jsonify({'ok': False, 'error': 'Need level 4 to switch island type'}), 403
    body = request.get_json(silent=True) or {}
    new_type = body.get('type', '')
    if new_type not in db.ISLAND_TYPES:
        return jsonify({'ok': False, 'error': f'Invalid type. Choose: {", ".join(db.ISLAND_TYPES)}'}), 400
    current = db.get_island_type(wid)
    if current == new_type:
        return jsonify({'ok': False, 'error': 'Already this type'})
    db.set_island_type(wid, new_type)
    db.add_feed_event(wid, 'island', f'Island type changed to {new_type}!', '🏝️')
    return jsonify({'ok': True, 'old_type': current, 'new_type': new_type})

# ── Inventory ─────────────────────────────────────────────────
@app.route('/api/inventory')
def api_inventory():
    """Get player inventory."""
    wid = _req_world_id()
    inv = db.get_inventory(wid)
    emojis = db.RESOURCE_EMOJIS
    items = []
    for res, amt in inv.items():
        items.append({'resource': res, 'amount': amt, 'emoji': emojis.get(res, '📦')})
    return no_cache(jsonify({'inventory': items, 'total_types': len(items)}))

# ── Gathering Zones ───────────────────────────────────────────
@app.route('/api/gather')
def api_gather():
    """Get gathering plots status."""
    wid = _req_world_id()
    plots = db.get_gathering_plots(wid)
    itype = db.get_island_type(wid)
    stage_emojis = db.RESOURCE_STAGE_EMOJIS.get(itype, db.RESOURCE_STAGE_EMOJIS['farm'])
    for p in plots:
        p['stage_emoji'] = stage_emojis.get(p['stage'], '❓')
        p['resource_emoji'] = db.RESOURCE_EMOJIS.get(p['resource_type'], '📦')
    return no_cache(jsonify({'plots': plots, 'island_type': itype}))

@app.route('/api/gather/place', methods=['POST'])
def api_gather_place():
    """Place a gathering plot."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    col = int(body.get('col', 0))
    row = int(body.get('row', 0))
    resource_type = body.get('resource', '')
    zone_type = body.get('zone', 'primary')
    
    itype = db.get_island_type(wid)
    tier = db.get_resource_tier(itype, resource_type)
    if not tier:
        return jsonify({'ok': False, 'error': f'Resource {resource_type} not available on {itype} island'}), 400
    
    base_time = db.RESOURCE_GROW_TIMES.get(resource_type, 120)
    # Adjust grow time by tier (primary=normal, secondary=1.5x, weak=3x)
    multiplier = {'primary': 1.0, 'secondary': 1.5, 'weak': 3.0}.get(tier, 1.0)
    grow_seconds = int(base_time * multiplier)
    
    plot_id = db.place_gathering(wid, zone_type, col, row, resource_type, grow_seconds)
    # Track discovery in collection book
    if resource_type:
        try: db.discover_object(wid, resource_type)
        except Exception: pass
    return jsonify({'ok': True, 'plot_id': plot_id, 'grow_seconds': grow_seconds, 'tier': tier})

@app.route('/api/gather/harvest', methods=['POST'])
def api_gather_harvest():
    """Harvest a ready gathering plot."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    plot_id = int(body.get('plot_id', 0))
    
    plot = db.harvest_gathering(wid, plot_id)
    if not plot:
        return jsonify({'ok': False, 'error': 'Not ready or not found'}), 400
    
    itype = db.get_island_type(wid)
    tier = db.get_resource_tier(itype, plot['resource_type'])
    yield_mult = db.RESOURCE_YIELD.get(tier, 1.0)
    amount = max(1, int(yield_mult))
    
    db.add_to_inventory(wid, plot['resource_type'], amount)
    emoji = db.RESOURCE_EMOJIS.get(plot['resource_type'], '📦')
    db.add_feed_event(wid, 'gather', f'Harvested {amount}x {emoji} {plot["resource_type"]}', emoji)
    
    # XP for gathering
    db.record_progress_event(wid, 'place_tile')
    db.increment_achievement_stat(wid, 'gather')
    db.advance_quest(wid, 'harvest_crops')
    
    return jsonify({'ok': True, 'resource': plot['resource_type'], 'amount': amount, 'emoji': emoji})

# ── Crafting ──────────────────────────────────────────────────
@app.route('/api/recipes')
def api_recipes():
    """List all recipes (filtered by player level)."""
    wid = _req_world_id()
    progress = db.get_progress(wid)
    level = progress['level'] if progress else 1
    inv = db.get_inventory(wid)
    
    recipes = []
    for rid, r in db.RECIPES.items():
        available = level >= r.get('min_level', 1)
        has_resources = True
        inputs_status = []
        for res, need in r['inputs'].items():
            have = inv.get(res, 0)
            inputs_status.append({
                'resource': res, 'need': need, 'have': have,
                'enough': have >= need, 'emoji': db.RESOURCE_EMOJIS.get(res, '📦')
            })
            if have < need:
                has_resources = False
        coin_cost = r.get('coin_cost', 0)
        wallet = db.get_wallet(wid)
        has_coins = wallet['coins'] >= coin_cost if coin_cost > 0 else True
        recipes.append({
            'id': rid, 'name': r['name'], 'inputs': inputs_status,
            'output': r['output'], 'output_emoji': db.RESOURCE_EMOJIS.get(r['output'], '📦'),
            'time': r['time'], 'min_level': r.get('min_level', 1),
            'coin_cost': coin_cost, 'category': r.get('category', ''),
            'available': available, 'craftable': available and has_resources and has_coins,
        })
    return no_cache(jsonify({'recipes': recipes, 'player_level': level}))

@app.route('/api/craft', methods=['POST'])
def api_craft():
    """Start crafting."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    recipe_id = body.get('recipe_id', '')
    result = db.start_crafting(wid, recipe_id)
    return jsonify(result)

@app.route('/api/craft/status')
def api_craft_status():
    """Get crafting queue status."""
    wid = _req_world_id()
    queue = db.get_crafting_queue(wid)
    return no_cache(jsonify({'queue': queue}))

@app.route('/api/craft/collect', methods=['POST'])
def api_craft_collect():
    """Collect a finished crafted item."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    craft_id = int(body.get('craft_id', 0))
    result = db.collect_crafted(wid, craft_id)
    if result['ok']:
        db.add_feed_event(wid, 'craft', f'Crafted {result.get("emoji","")} {result.get("item","")}', result.get('emoji', '🔨'))
        db.increment_achievement_stat(wid, 'craft')
        db.advance_quest(wid, 'craft_item')
    return jsonify(result)

# ── Market ────────────────────────────────────────────────────
@app.route('/api/market')
def api_market():
    """Get market orders."""
    resource = request.args.get('resource')
    orders = db.get_market_orders(resource=resource)
    for o in orders:
        o['emoji'] = db.RESOURCE_EMOJIS.get(o['resource'], '📦')
    return no_cache(jsonify({'orders': orders}))

@app.route('/api/market/my')
def api_market_my():
    """Get my market orders."""
    wid = _req_world_id()
    orders = db.get_my_orders(wid)
    for o in orders:
        o['emoji'] = db.RESOURCE_EMOJIS.get(o['resource'], '📦')
    return no_cache(jsonify({'orders': orders}))

@app.route('/api/market/sell', methods=['POST'])
def api_market_sell():
    """Create a sell order."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    resource = body.get('resource', '')
    amount = int(body.get('amount', 0))
    price = int(body.get('price_per_unit', 0))
    seller_name = body.get('seller_name', 'Anonymous')
    
    result = db.create_sell_order(wid, seller_name, resource, amount, price)
    if result['ok']:
        emoji = db.RESOURCE_EMOJIS.get(resource, '📦')
        db.add_feed_event(wid, 'market', f'Listed {amount}x {emoji} {resource} @ {price}💎 each', '🏪')
        db.increment_achievement_stat(wid, 'sell')
        db.advance_quest(wid, 'sell_market')
    return jsonify(result)

@app.route('/api/market/buy', methods=['POST'])
def api_market_buy():
    """Buy from a market order."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    order_id = int(body.get('order_id', 0))
    buy_amount = body.get('amount')
    if buy_amount:
        buy_amount = int(buy_amount)
    
    result = db.buy_market_order(wid, order_id, buy_amount)
    if result.get('ok'):
        db.increment_achievement_stat(wid, 'buy')
    return jsonify(result)

@app.route('/api/market/cancel', methods=['POST'])
def api_market_cancel():
    """Cancel own market order."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    order_id = int(body.get('order_id', 0))
    result = db.cancel_market_order(wid, order_id)
    return jsonify(result)

# ── Daily Quests ──────────────────────────────────────────────
@app.route('/api/quests')
def api_quests():
    """Get today's daily quests for the authenticated user."""
    wid = _req_world_id()
    quests = db.get_daily_quests(wid)
    # Enrich with descriptions
    for q in quests:
        info = db.QUEST_TYPES.get(q['quest_type'], {})
        q['description'] = info.get('desc', q['quest_type']).replace('{n}', str(q['target_count']))
    return no_cache(jsonify({'ok': True, 'quests': quests}))

@app.route('/api/quests/claim', methods=['POST'])
def api_quests_claim():
    """Claim reward for a completed quest."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    quest_id = int(body.get('quest_id', 0))
    result = db.claim_quest_reward(wid, quest_id)
    return jsonify(result)

# ── Daily Challenges ──────────────────────────────────────────
@app.route('/api/daily-challenges')
def api_daily_challenges():
    """Get today's daily challenges for the logged-in user."""
    wid = _req_world_id()
    challenges = db.get_daily_challenges(wid)
    return no_cache(jsonify({'ok': True, 'challenges': challenges}))

@app.route('/api/daily-challenges/check', methods=['POST'])
def api_daily_challenges_check():
    """Manually refresh/check daily challenge progress."""
    wid = _req_world_id()
    challenges = db.get_daily_challenges(wid)
    return no_cache(jsonify({'ok': True, 'challenges': challenges}))

# ── Prices ────────────────────────────────────────────────────
@app.route('/api/prices')
def api_prices():
    """Get today's prices for all resources."""
    prices = db.get_all_prices()
    return no_cache(jsonify({'prices': prices, 'date': datetime.now(timezone.utc).strftime('%Y-%m-%d')}))

@app.route('/api/prices/history')
def api_prices_history():
    """Get price history for a resource."""
    resource = request.args.get('resource', 'cabbage')
    days = int(request.args.get('days', 7))
    history = db.get_price_history(resource, days)
    return no_cache(jsonify({'resource': resource, 'history': history}))

# ── Attack System ─────────────────────────────────────────────
@app.route('/api/attack/building', methods=['POST'])
def api_attack_building():
    """Use a weapon to destroy a building on another island."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    target_world = body.get('target_world', '')
    weapon = body.get('weapon', '')
    target_col = int(body.get('col', 0))
    target_row = int(body.get('row', 0))
    
    if not target_world or target_world == wid:
        return jsonify({'ok': False, 'error': 'Invalid target'}), 400
    
    # Check level
    progress = db.get_progress(wid)
    if not progress or progress['level'] < 3:
        return jsonify({'ok': False, 'error': 'Need level 3'}), 403
    
    # Check newbie protection
    if db.check_newbie_protection(target_world):
        return jsonify({'ok': False, 'error': 'Target is under newbie protection (1h)'}), 403
    
    # Check cooldown
    can_attack, remaining = db.check_attack_cooldown(wid, target_world)
    if not can_attack:
        return jsonify({'ok': False, 'error': 'Cooldown active', 'remaining_seconds': int(remaining)}), 429
    
    # Check weapon in inventory
    valid_weapons = ['axe', 'warhammer', 'bomb', 'torch']
    if weapon not in valid_weapons:
        return jsonify({'ok': False, 'error': 'Invalid weapon'}), 400
    
    if not db.remove_from_inventory(wid, weapon, 1):
        return jsonify({'ok': False, 'error': 'Weapon not in inventory'}), 400
    
    # Check target defenses
    defenses = db.get_defenses(target_world)
    
    # Stone wall blocks one attack
    if weapon != 'torch':
        for d in defenses:
            if d['defense_type'] == 'stone_wall_defense':
                db.use_defense(target_world, 'stone_wall_defense')
                db.record_attack(wid, '', target_world, blocked=True)
                return jsonify({'ok': False, 'error': 'Blocked by stone wall! 🧱', 'blocked': True})
    
    # Moat blocks bombs
    if weapon == 'bomb':
        for d in defenses:
            if d['defense_type'] == 'moat':
                db.record_attack(wid, '', target_world, blocked=True)
                return jsonify({'ok': False, 'error': 'Bomb neutralized by moat! 🌊', 'blocked': True})
    
    # Guard dog counter-attack
    for d in defenses:
        if d['defense_type'] == 'guard_dog':
            db.use_defense(target_world, 'guard_dog')
            # Attacker loses a random resource
            attacker_inv = db.get_inventory(wid)
            if attacker_inv:
                import random
                lost_res = random.choice(list(attacker_inv.keys()))
                lost_amt = min(attacker_inv[lost_res], 3)
                db.remove_from_inventory(wid, lost_res, lost_amt)
    
    # Watchtower reveals attacker
    watchtower_alert = False
    for d in defenses:
        if d['defense_type'] == 'watchtower':
            watchtower_alert = True
            # Don't consume watchtower
    
    # Execute attack
    if weapon == 'torch':
        # Destroy gathering plots
        plots = db.get_gathering_plots(target_world)
        destroyed_count = 0
        for p in plots:
            if not p.get('harvested'):
                conn = db.get_conn()
                conn.execute("UPDATE gathering_plots SET harvested=1, stage='burned' WHERE id=?", (p['id'],))
                conn.commit()
                conn.close()
                destroyed_count += 1
        db.record_attack(wid, '', target_world, destroyed_object=f'torch:{destroyed_count}_plots')
        db.add_feed_event(target_world, 'attack', f'🔥 Someone burned {destroyed_count} gathering plots!', '🔥')
        target_owner = db.get_world_owner(target_world)
        if target_owner:
            _notify_owner(target_owner, 'raid', '🔥 Your island was raided!', f'Someone burned {destroyed_count} of your gathering plots! Fight back!', target_world)
        return jsonify({'ok': True, 'weapon': weapon, 'destroyed_plots': destroyed_count, 'watchtower_alert': watchtower_alert})
    
    elif weapon == 'bomb':
        # Destroy 3x3 area
        target_data = db.load_world(target_world)
        if target_data:
            objects = target_data.get('objects', [])
            destroyed = []
            remaining_objs = []
            for obj in objects:
                oc = obj.get('col', 0)
                orow = obj.get('row', 0)
                if abs(oc - target_col) <= 1 and abs(orow - target_row) <= 1:
                    destroyed.append(obj)
                    db.add_destroyed_object(target_world, obj.get('id', ''), obj.get('type', ''), oc, orow, 20, wid)
                else:
                    remaining_objs.append(obj)
            target_data['objects'] = remaining_objs
            db.save_world(target_world, target_data)
            db.record_attack(wid, '', target_world, destroyed_object=f'bomb:{len(destroyed)}_objects')
            db.add_feed_event(target_world, 'attack', f'💣 Bomb destroyed {len(destroyed)} buildings!', '💣')
            target_owner = db.get_world_owner(target_world)
            if target_owner:
                _notify_owner(target_owner, 'raid', '💣 Your island was bombed!', f'{len(destroyed)} buildings destroyed! Check the damage →', target_world)
            return jsonify({'ok': True, 'weapon': weapon, 'destroyed_count': len(destroyed), 'watchtower_alert': watchtower_alert})
    
    else:
        # axe or warhammer — destroy 1 building at target location
        target_data = db.load_world(target_world)
        if target_data:
            objects = target_data.get('objects', [])
            destroyed_obj = None
            remaining_objs = []
            for obj in objects:
                if not destroyed_obj and obj.get('col') == target_col and obj.get('row') == target_row:
                    destroyed_obj = obj
                    db.add_destroyed_object(target_world, obj.get('id', ''), obj.get('type', ''), target_col, target_row, 15, wid)
                else:
                    remaining_objs.append(obj)
            if destroyed_obj:
                target_data['objects'] = remaining_objs
                db.save_world(target_world, target_data)
                db.record_attack(wid, '', target_world, destroyed_object=f'{weapon}:{destroyed_obj.get("type","")}')
                db.add_feed_event(target_world, 'attack', f'{"🪓" if weapon=="axe" else "⚒️"} A building was destroyed!', '⚔️')
                return jsonify({'ok': True, 'weapon': weapon, 'destroyed': destroyed_obj.get('type', ''), 'watchtower_alert': watchtower_alert})
            else:
                # No building at target — refund weapon
                db.add_to_inventory(wid, weapon, 1)
                return jsonify({'ok': False, 'error': 'No building at target location'})
    
    return jsonify({'ok': False, 'error': 'Attack failed'})

@app.route('/api/attack/cooldown')
def api_attack_cooldown():
    """Check attack cooldown for a target."""
    wid = _req_world_id()
    target = request.args.get('target', '')
    can_attack, remaining = db.check_attack_cooldown(wid, target)
    return no_cache(jsonify({'can_attack': can_attack, 'remaining_seconds': int(remaining)}))

# ── Defense ───────────────────────────────────────────────────
@app.route('/api/defense')
def api_defense():
    """Get active defenses."""
    wid = _req_world_id()
    defenses = db.get_defenses(wid)
    for d in defenses:
        d['emoji'] = db.RESOURCE_EMOJIS.get(d['defense_type'], '🛡️')
    return no_cache(jsonify({'defenses': defenses}))

@app.route('/api/defense/place', methods=['POST'])
def api_defense_place():
    """Place a defense from inventory."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    defense_type = body.get('defense_type', '')
    valid = ['stone_wall_defense', 'watchtower', 'guard_dog']
    if defense_type not in valid:
        return jsonify({'ok': False, 'error': 'Invalid defense type'}), 400
    result = db.place_defense(wid, defense_type)
    if result.get('ok'):
        db.increment_achievement_stat(wid, 'defense')
        # Track discovery in collection book
        try: db.discover_object(wid, defense_type)
        except Exception: pass
    return jsonify(result)

@app.route('/api/defense/moat', methods=['POST'])
def api_defense_moat():
    """Buy moat defense for 500 coins."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    # Check if already have moat
    defenses = db.get_defenses(wid)
    for d in defenses:
        if d['defense_type'] == 'moat':
            return jsonify({'ok': False, 'error': 'Already have a moat'})
    spend = db.spend_coins(wid, 500, 'buy_moat')
    if not spend['ok']:
        return jsonify(spend)
    now = datetime.now(timezone.utc).isoformat()
    conn = db.get_conn()
    conn.execute("INSERT INTO defense_items (world_id, defense_type, placed_at, uses_remaining, active) VALUES (?,?,?,99,1)",
                 (wid, 'moat', now))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'defense': 'moat', 'cost': 500})


# ══════════════════════════════════════════════════════════════
# ── Servant System APIs ───────────────────────────────────────
# ══════════════════════════════════════════════════════════════

import random as _servant_rnd

@app.route('/api/servants', methods=['GET'])
def api_servants():
    """Get all servants for the current world."""
    wid = _req_world_id()
    servants = db.get_servants(wid)
    servant_types_info = {}
    for st_key, st_val in db.SERVANT_TYPES.items():
        servant_types_info[st_key] = {
            'name': st_val['name'],
            'emoji': st_val['emoji'],
            'description': st_val['description'],
            'craft_cost': st_val['craft_cost'],
            'coin_cost': st_val['coin_cost'],
            'use_cost': st_val['use_cost'],
            'durability': st_val['durability'],
            'min_level': st_val['min_level'],
        }
    return no_cache(jsonify({
        'servants': servants,
        'count': len(servants),
        'types': servant_types_info,
    }))


@app.route('/api/servants/create', methods=['POST'])
def api_servants_create():
    """Create a new servant."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    servant_type = body.get('type', '')
    if not servant_type:
        return jsonify({'ok': False, 'error': 'type is required (gatherer, thief, trader)'}), 400
    result = db.create_servant(wid, servant_type)
    if result.get('ok'):
        stype = db.SERVANT_TYPES.get(servant_type, {})
        db.add_feed_event(wid, 'servant',
            f'{stype.get("emoji","🦞")} Created {stype.get("name", servant_type)}!', stype.get('emoji', '🦞'))
    return jsonify(result)


@app.route('/api/servants/use', methods=['POST'])
def api_servants_use():
    """Use a servant — executes its action."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    servant_id = body.get('servant_id')
    if not servant_id:
        return jsonify({'ok': False, 'error': 'servant_id is required'}), 400
    servant_id = int(servant_id)

    # Use the servant (deducts coins + durability)
    use_result = db.use_servant(wid, servant_id)
    if not use_result.get('ok'):
        return jsonify(use_result)

    servant = use_result['servant']
    servant_type = servant['servant_type']
    action_result = {}

    if servant_type == 'gatherer':
        # Pick a random primary resource for this island and produce 5x + small coins
        island_type = db.get_island_type(wid)
        resources = db.ISLAND_RESOURCES.get(island_type, db.ISLAND_RESOURCES['farm'])
        primary = resources.get('primary', ['cabbage'])
        chosen_resource = _servant_rnd.choice(primary)
        amount = 5
        db.add_to_inventory(wid, chosen_resource, amount)
        bonus_coins = _servant_rnd.randint(10, 30)
        db.earn_coins(wid, bonus_coins, f'servant_gatherer_{chosen_resource}')
        emoji = db.RESOURCE_EMOJIS.get(chosen_resource, '📦')
        action_result = {
            'action': 'gather',
            'resource': chosen_resource,
            'amount': amount,
            'bonus_coins': bonus_coins,
            'emoji': emoji,
            'message': f'🦞 Gatherer harvested {amount}x {emoji} {chosen_resource} + {bonus_coins}💎!',
        }
        db.add_feed_event(wid, 'servant',
            f'🦞 Gatherer harvested {amount}x {emoji} {chosen_resource} + {bonus_coins}💎', '🦞')

    elif servant_type == 'thief':
        # Pick a random other island and steal 1 resource
        all_worlds = db.list_worlds(limit=50)
        other_worlds = [w for w in all_worlds if w['id'] != wid]
        if not other_worlds:
            action_result = {
                'action': 'thief',
                'message': '🦹 No other islands to steal from!',
                'stolen': False,
            }
        else:
            target = _servant_rnd.choice(other_worlds)
            target_wid = target['id']
            target_inv = db.get_inventory(target_wid)
            stealable = {k: v for k, v in target_inv.items() if v > 0}

            if not stealable:
                action_result = {
                    'action': 'thief',
                    'message': f'🦹 Visited {target["name"]} but found nothing to steal!',
                    'stolen': False,
                    'target': target['name'],
                }
            else:
                stolen_resource = _servant_rnd.choice(list(stealable.keys()))
                # 30% chance of getting caught
                caught = _servant_rnd.random() < db.SERVANT_TYPES['thief'].get('catch_chance', 0.3)

                if caught:
                    # Extra durability loss on catch
                    conn = db.get_conn()
                    conn.execute(
                        "UPDATE servants SET durability=MAX(0, durability-2) WHERE id=?",
                        (servant_id,)
                    )
                    conn.commit()
                    conn.close()
                    emoji = db.RESOURCE_EMOJIS.get(stolen_resource, '📦')
                    action_result = {
                        'action': 'thief',
                        'message': f'🦹 Caught stealing from {target["name"]}! Lost extra durability! (Still got 1x {emoji} {stolen_resource})',
                        'stolen': True,
                        'caught': True,
                        'resource': stolen_resource,
                        'amount': 1,
                        'target': target['name'],
                        'extra_durability_loss': 2,
                    }
                    db.add_feed_event(wid, 'servant',
                        f'🦹 Thief got caught at {target["name"]}! -2 extra durability', '🦹')
                else:
                    action_result = {
                        'action': 'thief',
                        'message': f'🦹 Stole 1x {db.RESOURCE_EMOJIS.get(stolen_resource, "📦")} {stolen_resource} from {target["name"]}!',
                        'stolen': True,
                        'caught': False,
                        'resource': stolen_resource,
                        'amount': 1,
                        'target': target['name'],
                    }

                # Transfer resource
                db.remove_from_inventory(target_wid, stolen_resource, 1)
                db.add_to_inventory(wid, stolen_resource, 1)
                db.add_feed_event(target_wid, 'servant_theft',
                    f'🦹 A thief lobster stole 1x {db.RESOURCE_EMOJIS.get(stolen_resource, "📦")} {stolen_resource}!', '🦹')
                if not caught:
                    db.add_feed_event(wid, 'servant',
                        f'🦹 Thief stole 1x {stolen_resource} from {target["name"]}', '🦹')

    elif servant_type == 'trader':
        # Check market for lowest sell order below reference price
        orders = db.get_market_orders(limit=50)
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        bought_something = False

        for order in orders:
            if order['seller_id'] == wid:
                continue  # skip own orders
            resource = order['resource']
            ref_price = db.get_daily_price(resource, today_str)
            if order['price_per_unit'] < ref_price:
                # Good deal! Try to buy 1 unit
                buy_amount = min(order['amount'], 3)  # buy up to 3
                total_cost = buy_amount * order['price_per_unit']
                wallet = db.get_wallet(wid)
                if wallet['coins'] >= total_cost:
                    buy_result = db.buy_market_order(wid, order['id'], buy_amount)
                    if buy_result.get('ok'):
                        emoji = db.RESOURCE_EMOJIS.get(resource, '📦')
                        action_result = {
                            'action': 'trade',
                            'message': f'🏪 Trader bought {buy_amount}x {emoji} {resource} at {order["price_per_unit"]}💎 (ref: {ref_price}💎)!',
                            'bought': True,
                            'resource': resource,
                            'amount': buy_amount,
                            'price': order['price_per_unit'],
                            'ref_price': ref_price,
                            'total_cost': total_cost,
                        }
                        db.add_feed_event(wid, 'servant',
                            f'🏪 Trader bought {buy_amount}x {emoji} {resource} @ {order["price_per_unit"]}💎 (ref: {ref_price}💎)', '🏪')
                        bought_something = True
                        break

        if not bought_something:
            action_result = {
                'action': 'trade',
                'message': '🏪 Trader scanned the market but found no good deals right now.',
                'bought': False,
            }

    # Re-fetch updated servant
    servants = db.get_servants(wid)
    updated_servant = next((s for s in servants if s['id'] == servant_id), servant)

    return jsonify({
        'ok': True,
        'servant': updated_servant,
        'action_result': action_result,
    })


@app.route('/api/servants/repair', methods=['POST'])
def api_servants_repair():
    """Repair a servant's durability."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    servant_id = body.get('servant_id')
    if not servant_id:
        return jsonify({'ok': False, 'error': 'servant_id is required'}), 400
    servant_id = int(servant_id)
    result = db.repair_servant(wid, servant_id)
    if result.get('ok'):
        db.add_feed_event(wid, 'servant', f'🔧 Repaired {result["servant"]["name"]}!', '🔧')
    return jsonify(result)


@app.route('/api/servants/delete', methods=['POST'])
def api_servants_delete():
    """Delete a broken servant (durability 0)."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403
    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    servant_id = body.get('servant_id')
    if not servant_id:
        return jsonify({'ok': False, 'error': 'servant_id is required'}), 400
    servant_id = int(servant_id)
    result = db.delete_servant(wid, servant_id)
    return jsonify(result)


# ── Migrate visits.json → SQLite on startup ───────────────────
_migrated = False
def _migrate_visits():
    global _migrated
    if not _migrated:
        count = db.migrate_visits_from_json(VISITS_F)
        _migrated = True

_migrate_visits()

# ── Custom 404 Error Handler ──────────────────────────────────
@app.errorhandler(404)
def page_not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    return PAGE_404, 404

# ── Economy Achievements API ──────────────────────────────────

@app.route('/api/achievements')
def api_achievements_v2():
    wid = _req_world_id()
    if not wid:
        return jsonify({'achievements': [], 'all': list(db.ACHIEVEMENTS_V2.items())})
    unlocked = db.get_achievements_v2(wid)
    unlocked_ids = {a['id'] for a in unlocked}
    all_achievements = []
    for aid, ach in db.ACHIEVEMENTS_V2.items():
        entry = {**ach, 'id': aid, 'unlocked': aid in unlocked_ids}
        if aid in unlocked_ids:
            entry['unlocked_at'] = next(a['unlocked_at'] for a in unlocked if a['id'] == aid)
        all_achievements.append(entry)
    return jsonify({'achievements': all_achievements, 'unlocked_count': len(unlocked_ids), 'total': len(db.ACHIEVEMENTS_V2)})

@app.route('/api/achievements/check', methods=['POST'])
def api_achievements_check():
    wid = _req_world_id()
    if not wid:
        return jsonify({'error': 'no world'}), 401
    # Also check visit and level-based achievements
    w = load_json(f'worlds/{wid}.json', {})
    visit_count = w.get('visit_count', 0)
    if visit_count >= 10: db.unlock_achievement(wid, 'visitor_10')
    if visit_count >= 100: db.unlock_achievement(wid, 'visitor_100')
    level = w.get('level', 1)
    if level >= 5: db.unlock_achievement(wid, 'level_5')
    if level >= 10: db.unlock_achievement(wid, 'level_10')
    obj_count = len(w.get('objects', []))
    # Update build stat to match actual objects
    conn = db.get_conn()
    conn.execute("INSERT INTO achievement_progress (world_id, stat_key, count) VALUES (?, 'build', ?) ON CONFLICT(world_id, stat_key) DO UPDATE SET count = ?", (wid, obj_count, obj_count))
    conn.commit()
    conn.close()
    newly = db.check_and_unlock_achievements(wid)
    return jsonify({'newly_unlocked': newly, 'total_unlocked': len(db.get_achievements_v2(wid))})


# ── Island Mood/Status API ─────────────────────────────────────

def _migrate_mood_columns():
    """Add island_mood and island_mood_emoji columns to worlds table if missing."""
    conn = db.get_conn()
    cols = {row['name'] for row in conn.execute("PRAGMA table_info(worlds)").fetchall()}
    if 'island_mood' not in cols:
        conn.execute("ALTER TABLE worlds ADD COLUMN island_mood TEXT DEFAULT NULL")
    if 'island_mood_emoji' not in cols:
        conn.execute("ALTER TABLE worlds ADD COLUMN island_mood_emoji TEXT DEFAULT NULL")
    if 'island_mood_updated' not in cols:
        conn.execute("ALTER TABLE worlds ADD COLUMN island_mood_updated TEXT DEFAULT NULL")
    conn.commit()
    conn.close()

_migrate_mood_columns()

def _migrate_welcome_message_column():
    """Add welcome_message column to worlds table if missing."""
    conn = db.get_conn()
    cols = {row['name'] for row in conn.execute("PRAGMA table_info(worlds)").fetchall()}
    if 'welcome_message' not in cols:
        conn.execute("ALTER TABLE worlds ADD COLUMN welcome_message TEXT DEFAULT NULL")
        conn.commit()
    conn.close()

_migrate_welcome_message_column()

def _migrate_accent_color_column():
    """Add accent_color column to worlds table if missing."""
    conn = db.get_conn()
    cols = {row['name'] for row in conn.execute("PRAGMA table_info(worlds)").fetchall()}
    if 'accent_color' not in cols:
        conn.execute("ALTER TABLE worlds ADD COLUMN accent_color TEXT DEFAULT NULL")
        conn.commit()
    conn.close()

_migrate_accent_color_column()

def _migrate_announcement_column():
    """Add announcement column to worlds table if missing."""
    conn = db.get_conn()
    cols = {row['name'] for row in conn.execute("PRAGMA table_info(worlds)").fetchall()}
    if 'announcement' not in cols:
        conn.execute("ALTER TABLE worlds ADD COLUMN announcement TEXT DEFAULT NULL")
        conn.commit()
    conn.close()
_migrate_announcement_column()

def _migrate_unlisted_column():
    """Add unlisted column to worlds table if missing."""
    conn = db.get_conn()
    cols = {row['name'] for row in conn.execute("PRAGMA table_info(worlds)").fetchall()}
    if 'unlisted' not in cols:
        conn.execute("ALTER TABLE worlds ADD COLUMN unlisted INTEGER DEFAULT 0")
        conn.commit()
    conn.close()
_migrate_unlisted_column()

@app.route('/api/island/mood', methods=['GET'])
def api_island_mood_get():
    """Get the mood/status message for the current world."""
    world_id = _req_world_id()
    conn = db.get_conn()
    row = conn.execute(
        "SELECT island_mood, island_mood_emoji, island_mood_updated FROM worlds WHERE id=?",
        (world_id,)
    ).fetchone()
    conn.close()
    if not row or not row['island_mood']:
        return no_cache(jsonify({'mood': None, 'emoji': None, 'updated_at': None}))
    return no_cache(jsonify({
        'mood': row['island_mood'],
        'emoji': row['island_mood_emoji'],
        'updated_at': row['island_mood_updated'],
    }))

@app.route('/api/island/mood', methods=['POST'])
def api_island_mood_set():
    """Set the mood/status message for the current world (owner only)."""
    body = request.get_json(silent=True) or {}
    mood = (body.get('mood') or '').strip()
    emoji = (body.get('emoji') or '').strip()

    world_id = _req_world_id()

    # Clear mood if both empty
    if not mood and not emoji:
        conn = db.get_conn()
        conn.execute(
            "UPDATE worlds SET island_mood=NULL, island_mood_emoji=NULL, island_mood_updated=NULL WHERE id=?",
            (world_id,)
        )
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'mood': None, 'emoji': None})

    # Validate
    if len(mood) > 60:
        return jsonify({'ok': False, 'error': 'Mood text max 60 characters'}), 400

    now = datetime.now(timezone.utc).isoformat()
    conn = db.get_conn()
    conn.execute(
        "UPDATE worlds SET island_mood=?, island_mood_emoji=?, island_mood_updated=? WHERE id=?",
        (mood or None, emoji or None, now, world_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'mood': mood, 'emoji': emoji, 'updated_at': now})


# ── Custom Welcome Message API ────────────────────────────────
@app.route('/api/island/welcome-message', methods=['GET'])
def api_island_welcome_message_get():
    """Get the custom welcome message for the current world."""
    world_id = _req_world_id()
    conn = db.get_conn()
    row = conn.execute("SELECT welcome_message FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    return no_cache(jsonify({'ok': True, 'welcome_message': row['welcome_message'] if row else None}))

@app.route('/api/island/welcome-message', methods=['POST'])
def api_island_welcome_message_set():
    """Set custom welcome message (owner only). Max 120 chars."""
    body = request.get_json(silent=True) or {}
    message = (body.get('message') or '').strip()
    world_id = _req_world_id()

    if len(message) > 120:
        return jsonify({'ok': False, 'error': 'Welcome message max 120 characters'}), 400

    conn = db.get_conn()
    conn.execute("UPDATE worlds SET welcome_message=? WHERE id=?", (message or None, world_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'welcome_message': message or None})


# ── Island Accent Color API ────────────────────────────────
@app.route('/api/island/accent-color', methods=['GET'])
def api_island_accent_color_get():
    world_id = _req_world_id()
    conn = db.get_conn()
    row = conn.execute("SELECT accent_color FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    return no_cache(jsonify({'ok': True, 'accent_color': row['accent_color'] if row else None}))

@app.route('/api/island/accent-color', methods=['POST'])
def api_island_accent_color_set():
    import re as _re_accent
    body = request.get_json(silent=True) or {}
    color = (body.get('color') or '').strip()
    world_id = _req_world_id()

    # Validate hex color or allow empty to clear
    if color and not _re_accent.match(r'^#[0-9a-fA-F]{6}$', color):
        return jsonify({'ok': False, 'error': 'Invalid color format. Use #RRGGBB'}), 400

    conn = db.get_conn()
    conn.execute("UPDATE worlds SET accent_color=? WHERE id=?", (color or None, world_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'accent_color': color or None})


# ── Island Pinned Announcement API ────────────────────────────
@app.route('/api/island/announcement', methods=['GET'])
def api_island_announcement_get():
    world_id = _req_world_id()
    conn = db.get_conn()
    row = conn.execute("SELECT announcement FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    return no_cache(jsonify({'ok': True, 'announcement': row['announcement'] if row else None}))

@app.route('/api/island/announcement', methods=['POST'])
def api_island_announcement_set():
    body = request.get_json(silent=True) or {}
    text = (body.get('text') or '').strip()
    world_id = _req_world_id()
    if len(text) > 100:
        return jsonify({'ok': False, 'error': 'Announcement max 100 characters'}), 400
    conn = db.get_conn()
    conn.execute("UPDATE worlds SET announcement=? WHERE id=?", (text or None, world_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'announcement': text or None})


# ── Island Unlisted Mode API ──────────────────────────────────

@app.route('/api/island/unlisted', methods=['GET'])
def api_island_unlisted_get():
    world_id = _req_world_id()
    conn = db.get_conn()
    row = conn.execute("SELECT unlisted FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    return no_cache(jsonify({'ok': True, 'unlisted': bool(row['unlisted']) if row else False}))

@app.route('/api/island/unlisted', methods=['POST'])
def api_island_unlisted_set():
    body = request.get_json(silent=True) or {}
    unlisted = bool(body.get('unlisted', False))
    world_id = _req_world_id()
    conn = db.get_conn()
    conn.execute("UPDATE worlds SET unlisted=? WHERE id=?", (1 if unlisted else 0, world_id))
    conn.commit()
    conn.close()
    db._worlds_cache.clear()
    return jsonify({'ok': True, 'unlisted': unlisted})


# ── Island Tags API ───────────────────────────────────────────

def _migrate_island_tags_column():
    """Add island_tags column to worlds table if missing."""
    conn = db.get_conn()
    cols = {row['name'] for row in conn.execute("PRAGMA table_info(worlds)").fetchall()}
    if 'island_tags' not in cols:
        conn.execute("ALTER TABLE worlds ADD COLUMN island_tags TEXT DEFAULT NULL")
        conn.commit()
    conn.close()

_migrate_island_tags_column()

import re as _re

def _parse_tags(raw):
    """Parse comma-separated tags string into a list of strings."""
    if not raw:
        return []
    return [t.strip() for t in raw.split(',') if t.strip()]

def _validate_tag(tag):
    """Validate a single tag: lowercase, alphanumeric + hyphens, max 20 chars."""
    tag = tag.strip().lower()
    if not tag:
        return None, 'Empty tag'
    if len(tag) > 20:
        return None, 'Tag max 20 characters'
    if not _re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$|^[a-z0-9]$', tag):
        return None, 'Tags must be lowercase alphanumeric with hyphens only'
    return tag, None

_popular_tags_cache = {'data': None, 'ts': 0}

@app.route('/api/tags/popular', methods=['GET'])
def api_popular_tags():
    """Return popular tags across all listed islands (60s cache)."""
    import time as _t
    now = _t.time()
    if _popular_tags_cache['data'] is not None and (now - _popular_tags_cache['ts']) < 60:
        return jsonify({'ok': True, 'tags': _popular_tags_cache['data']})
    tags = db.get_popular_tags(limit=20)
    _popular_tags_cache['data'] = tags
    _popular_tags_cache['ts'] = now
    return jsonify({'ok': True, 'tags': tags})

@app.route('/api/island/tags', methods=['GET'])
def api_island_tags_get():
    """Get tags for the current world. No auth required."""
    world_id = _req_world_id()
    conn = db.get_conn()
    row = conn.execute("SELECT island_tags FROM worlds WHERE id=?", (world_id,)).fetchone()
    conn.close()
    tags = _parse_tags(row['island_tags'] if row else None)
    return no_cache(jsonify({'ok': True, 'tags': tags}))

@app.route('/api/island/tags', methods=['POST'])
def api_island_tags_set():
    """Set tags for the current world (owner only). Max 3 tags."""
    world_id = _req_world_id()

    # Owner check
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Login required'}), 401
    owner_id = db.get_world_owner(world_id)
    if user['id'] != owner_id:
        return jsonify({'ok': False, 'error': 'Only the island owner can set tags'}), 403

    body = request.get_json(silent=True) or {}
    raw_tags = body.get('tags', [])
    if not isinstance(raw_tags, list):
        return jsonify({'ok': False, 'error': 'tags must be an array'}), 400
    if len(raw_tags) > 3:
        return jsonify({'ok': False, 'error': 'Maximum 3 tags allowed'}), 400

    validated = []
    for rt in raw_tags:
        tag, err = _validate_tag(str(rt))
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        if tag and tag not in validated:
            validated.append(tag)

    tags_str = ','.join(validated) if validated else None
    conn = db.get_conn()
    conn.execute("UPDATE worlds SET island_tags=? WHERE id=?", (tags_str, world_id))
    conn.commit()
    conn.close()
    # Invalidate worlds cache
    db._worlds_cache.clear()
    return jsonify({'ok': True, 'tags': validated})


# ── Island Random Events API ──────────────────────────────────
@app.route('/api/island-event')
def api_island_event():
    """Get active island event for a world. Also triggers maybe_spawn_event."""
    world_id = request.args.get('world_id') or request.args.get('world', 'default')
    # Try to spawn an event on visit
    db.maybe_spawn_event(world_id)
    event = db.get_active_event(world_id)
    return no_cache(jsonify({'event': event}))


@app.route('/api/island-event/collect', methods=['POST'])
def api_island_event_collect():
    """Collect an island event reward. Owner only."""
    user = _get_current_user()
    if not user:
        return no_cache(jsonify({'ok': False, 'error': 'Not logged in'})), 401
    body = request.get_json(silent=True) or {}
    event_id = body.get('event_id')
    world_id = body.get('world_id') or body.get('world', 'default')
    if not event_id:
        return no_cache(jsonify({'ok': False, 'error': 'Missing event_id'})), 400
    # Verify the user owns this world
    owner_id = db.get_world_owner(world_id)
    if owner_id != user['id']:
        return no_cache(jsonify({'ok': False, 'error': 'Not the island owner'})), 403
    coins = db.collect_event(event_id, world_id)
    if coins is None:
        return no_cache(jsonify({'ok': False, 'error': 'Event not found or already collected'})), 404
    # Daily challenge: collect_event
    try: db.update_challenge_progress(world_id, 'collect_event')
    except Exception: pass
    # Create a notification for the owner
    event = db.get_conn().execute("SELECT emoji, title FROM island_events WHERE id=?", (event_id,)).fetchone()
    if event:
        db.create_notification(
            user['id'], 'event',
            f"{event['emoji']} {event['title']} — collected {coins} coins!",
            island_id=world_id
        )
    return no_cache(jsonify({'ok': True, 'coins': coins}))


@app.route('/api/island/<world_id>/achievements')
def api_island_achievements_public(world_id):
    """Public endpoint: get unlocked achievements for an island."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    unlocked = db.get_achievements_v2(world_id)
    # Return only unlocked achievements with their metadata
    result = []
    for a in unlocked:
        meta = db.ACHIEVEMENTS_V2.get(a['id'], {})
        result.append({
            'id': a['id'],
            'name': meta.get('name', a['id']),
            'emoji': meta.get('emoji', '🏅'),
            'desc': meta.get('desc', ''),
            'unlocked_at': a.get('unlocked_at', '')
        })
    return no_cache(jsonify({'ok': True, 'achievements': result, 'total_possible': len(db.ACHIEVEMENTS_V2)}))


# ── Island Reactions API ────────────────────────────────────────

@app.route('/api/island/<world_id>/reactions', methods=['GET'])
def api_island_reactions_get(world_id):
    """Get reaction counts + user's own reactions for an island."""
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved

    # Identify user: logged-in session first, then IP-based fallback
    user = _get_current_user()
    if user:
        user_id = user['id']
    else:
        ip_raw = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
        user_id = 'anon_' + hashlib.sha256(ip_raw.encode()).hexdigest()[:12]

    reactions = db.get_island_reactions(world_id, user_id=user_id)
    return no_cache(jsonify({'ok': True, 'reactions': reactions}))


@app.route('/api/island/<world_id>/reactions', methods=['POST'])
def api_island_reactions_post(world_id):
    """Toggle a reaction on an island. Body: {emoji: "❤️"}."""
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved

    body = request.get_json(silent=True) or {}
    emoji = (body.get('emoji') or '').strip()

    # Validate emoji
    if emoji not in db.ALLOWED_REACTION_EMOJIS:
        return jsonify({'ok': False, 'error': f'Invalid emoji. Allowed: {db.ALLOWED_REACTION_EMOJIS}'}), 400

    # Identify user
    user = _get_current_user()
    if user:
        user_id = user['id']
    else:
        ip_raw = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
        user_id = 'anon_' + hashlib.sha256(ip_raw.encode()).hexdigest()[:12]

    # Rate limit: 1 toggle per IP per 2 seconds (using same pattern as guestbook)
    ip_raw = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]
    rate_key = f'reaction_{world_id}_{ip_hash}'
    now = time.time()
    if not hasattr(api_island_reactions_post, '_rate_cache'):
        api_island_reactions_post._rate_cache = {}
    last = api_island_reactions_post._rate_cache.get(rate_key, 0)
    if now - last < 2:
        return jsonify({'ok': False, 'error': 'Too fast, please wait'}), 429
    api_island_reactions_post._rate_cache[rate_key] = now
    # Cleanup old entries periodically
    if len(api_island_reactions_post._rate_cache) > 1000:
        cutoff = now - 10
        api_island_reactions_post._rate_cache = {k: v for k, v in api_island_reactions_post._rate_cache.items() if v > cutoff}

    # Toggle: check if already reacted
    reactions_before = db.get_island_reactions(world_id, user_id=user_id)
    already_reacted = any(r['emoji'] == emoji and r['reacted'] for r in reactions_before)

    if already_reacted:
        db.remove_island_reaction(world_id, user_id, emoji)
        action = 'removed'
    else:
        db.add_island_reaction(world_id, user_id, emoji)
        action = 'added'

    # Broadcast emoji rain to all viewers of this island
    if action == 'added':
        _broadcast_world_event('emoji_rain', {'emoji': emoji, 'world_id': world_id})

    # Visitor achievement: reactions_given (only on add)
    _va_react_new = []
    if action == 'added':
        try:
            _va_ruser = _get_current_user()
            if _va_ruser:
                db.increment_visitor_stat(_va_ruser['id'], 'reactions_given')
                _va_react_new = _check_visitor_achievements(_va_ruser['id'])
        except Exception:
            pass

    # Return updated reactions
    reactions = db.get_island_reactions(world_id, user_id=user_id)
    resp = {'ok': True, 'action': action, 'emoji': emoji, 'reactions': reactions}
    if _va_react_new:
        resp['new_achievements'] = _va_react_new
    return jsonify(resp)


# ── Crafting System ───────────────────────────────────────────

@app.route('/api/crafting/recipes')
def api_crafting_recipes():
    """Get all crafting recipes, with can_craft flag based on island objects."""
    wid = _req_world_id()
    world = _load_world_data(wid)
    placed_types = set()
    if world:
        for obj in world.get('objects', []):
            placed_types.add(obj.get('type', ''))

    # Get coin balance
    progress = db.get_progress(wid)
    balance = (progress or {}).get('shells', 0) or 0

    recipes_out = []
    for r in CRAFTING_RECIPES:
        ing = r['ingredients']
        has_ing = [t in placed_types for t in ing]
        can_craft = all(has_ing) and balance >= r['coins_cost']
        recipes_out.append({
            **r,
            'has_ingredients': has_ing,
            'can_craft': can_craft,
        })
    return no_cache(jsonify({'ok': True, 'recipes': recipes_out, 'coins': balance}))


@app.route('/api/crafting/craft', methods=['POST'])
def api_crafting_craft():
    """Craft an item by combining two ingredient objects on the island."""
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Owner only'}), 403

    wid = _req_world_id()
    body = request.get_json(silent=True) or {}
    recipe_id = body.get('recipe_id', '')

    # Find recipe
    recipe = next((r for r in CRAFTING_RECIPES if r['id'] == recipe_id), None)
    if not recipe:
        return jsonify({'ok': False, 'error': 'Unknown recipe'}), 400

    world = _load_world_data(wid)
    if not world:
        return jsonify({'ok': False, 'error': 'World not found'}), 404

    objects = world.get('objects', [])

    # Find first matching objects for each ingredient
    ing_types = list(recipe['ingredients'])  # e.g. ['tree_oak', 'lantern']
    removed_objects = []
    remaining = list(objects)

    for ing_type in ing_types:
        idx = next((i for i, o in enumerate(remaining) if o.get('type') == ing_type), None)
        if idx is None:
            return jsonify({'ok': False, 'error': f'Missing ingredient: {ing_type}'}), 400
        removed_objects.append(remaining.pop(idx))

    # Spend coins
    result = db.spend_coins(wid, recipe['coins_cost'], f"crafting_{recipe_id}")
    if not result or not result.get('ok', False):
        return jsonify({'ok': False, 'error': 'Not enough coins'}), 400

    # Place result object at position of first removed ingredient
    pos_obj = removed_objects[0]
    place_col = pos_obj.get('col', 0)
    place_row = pos_obj.get('row', 0)
    place_z = pos_obj.get('z', 1)

    import random
    new_id = f"{recipe['result']}_{int(time.time())}_{random.randint(100,999)}"
    new_obj = {
        'id': new_id,
        'type': recipe['result'],
        'col': place_col,
        'row': place_row,
        'z': place_z,
    }

    remaining.append(new_obj)
    world['objects'] = remaining
    _save_world_data(wid, world)

    # Record in activity feed
    db.add_feed_event(wid, 'crafting',
        f"⚒️ Crafted {recipe['name']} from {recipe['ingredients'][0]} + {recipe['ingredients'][1]}!",
        '⚒️')

    return jsonify({
        'ok': True,
        'crafted': recipe['result_name'],
        'result_type': recipe['result'],
        'col': place_col,
        'row': place_row,
        'coins_spent': recipe['coins_cost'],
    })


# ── Collection Book API ────────────────────────────────────────
@app.route('/api/collection')
def api_collection():
    """Get the player's collection book - discovered objects with category completion."""
    world_id = _get_current_world_id()
    if not world_id:
        return jsonify({'ok': False, 'error': 'No world'}), 400

    discovered = db.get_collection(world_id)
    discovered_ids = set(d['object_id'] for d in discovered)

    # Load catalog
    catalog = load_json(os.path.join(app.root_path, '..', 'catalog', 'catalog.json'), {})
    all_objects = catalog.get('objects', [])

    # Build category stats (exclude 'custom' category since those are user-created)
    categories = {}
    for obj in all_objects:
        cat = obj.get('category', 'unknown')
        if cat == 'custom':
            continue
        if cat not in categories:
            categories[cat] = {'total': 0, 'discovered': 0, 'objects': []}
        categories[cat]['total'] += 1
        is_discovered = obj['id'] in discovered_ids
        if is_discovered:
            categories[cat]['discovered'] += 1
        categories[cat]['objects'].append({
            'id': obj['id'],
            'name': obj.get('name', obj['id']),
            'discovered': is_discovered
        })

    # Overall stats
    total_discoverable = sum(c['total'] for c in categories.values())
    total_discovered = sum(c['discovered'] for c in categories.values())

    # Milestones
    milestones = [
        {'threshold': 10, 'reward': 50, 'label': 'Curious Explorer'},
        {'threshold': 25, 'reward': 150, 'label': 'Avid Collector'},
        {'threshold': 50, 'reward': 400, 'label': 'Treasure Hunter'},
        {'threshold': 75, 'reward': 800, 'label': 'Master Curator'},
        {'threshold': 100, 'reward': 1500, 'label': 'Legendary Archivist'},
    ]

    for m in milestones:
        m['reached'] = total_discovered >= m['threshold']

    # Check which milestones are already claimed
    conn = db.get_conn()
    for m in milestones:
        claim_key = f"collection_milestone_{m['threshold']}"
        already = conn.execute("SELECT 1 FROM achievements_v2 WHERE world_id=? AND achievement_id=?", (world_id, claim_key)).fetchone()
        m['claimed'] = bool(already)

    return jsonify({
        'ok': True,
        'total_discoverable': total_discoverable,
        'total_discovered': total_discovered,
        'completion_pct': round(total_discovered / max(total_discoverable, 1) * 100, 1),
        'categories': {k: {'total': v['total'], 'discovered': v['discovered'],
                          'pct': round(v['discovered']/max(v['total'],1)*100,1),
                          'objects': v['objects']} for k, v in categories.items()},
        'milestones': milestones,
        'recent': discovered[-5:][::-1] if discovered else []
    })

@app.route('/api/collection/claim-milestone', methods=['POST'])
def api_collection_claim_milestone():
    """Claim a collection milestone reward."""
    world_id = _get_current_world_id()
    if not world_id or not is_owner_request():
        return jsonify({'ok': False, 'error': 'Not owner'}), 403

    threshold = request.json.get('threshold', 0)

    discovered_count = db.get_collection_count(world_id)
    milestones = {10: 50, 25: 150, 50: 400, 75: 800, 100: 1500}

    if threshold not in milestones:
        return jsonify({'ok': False, 'error': 'Invalid milestone'}), 400
    if discovered_count < threshold:
        return jsonify({'ok': False, 'error': 'Not enough discoveries'}), 400

    # Check if already claimed (use achievement system)
    claim_key = f"collection_milestone_{threshold}"
    conn = db.get_conn()
    already = conn.execute("SELECT 1 FROM achievements_v2 WHERE world_id=? AND achievement_id=?", (world_id, claim_key)).fetchone()
    if already:
        return jsonify({'ok': False, 'error': 'Already claimed'}), 400

    # Award coins and record
    db.earn_coins(world_id, milestones[threshold], f"Collection milestone: {threshold} objects")
    db.unlock_achievement(world_id, claim_key)

    return jsonify({'ok': True, 'coins_awarded': milestones[threshold]})

# ── Backfill collection book from existing world data ──────────
def _backfill_collection_book():
    conn = db.get_conn()
    # Ensure table exists
    conn.execute("CREATE TABLE IF NOT EXISTS collection_book (id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL, object_id TEXT NOT NULL, discovered_at REAL DEFAULT (strftime('%s','now')), UNIQUE(world_id, object_id))")
    conn.commit()
    existing = conn.execute("SELECT COUNT(*) as cnt FROM collection_book").fetchone()
    if existing and existing['cnt'] > 0:
        return  # Already has data, skip backfill
    # Read from DB worlds table
    import json as _json_bl
    worlds = conn.execute("SELECT id, data_json FROM worlds").fetchall()
    for w in worlds:
        world_id = w['id']
        try:
            wdata = _json_bl.loads(w['data_json'] or '{}')
            for obj in wdata.get('objects', []):
                oid = obj.get('type') or obj.get('catalogId') or obj.get('id', '')
                if oid:
                    db.discover_object(world_id, oid)
        except Exception:
            pass

_backfill_collection_book()

# ── Fishing Mini-Game API ──────────────────────────────────────
# In-memory store for active fishing sessions
_fishing_sessions = {}  # fish_id -> {world_id, fish, cast_time, bite_time, ip, expires}
_fishing_cast_cooldown = {}  # ip -> last_cast_timestamp

@app.route('/api/fishing/cast')
def api_fishing_cast():
    """Start a fishing attempt. Returns wait_time and fish_id."""
    world_id = request.args.get('world', _req_world_id())
    ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'

    # Rate limit: 1 cast per 5 seconds per IP
    now = time.time()
    last_cast = _fishing_cast_cooldown.get(ip, 0)
    if now - last_cast < 5:
        remaining = 5 - (now - last_cast)
        return no_cache(jsonify({'ok': False, 'error': 'Too soon! Wait a moment.', 'cooldown': round(remaining, 1)})), 429

    _fishing_cast_cooldown[ip] = now

    # Clean up expired sessions (older than 30s)
    expired = [fid for fid, s in _fishing_sessions.items() if now - s['cast_time'] > 30]
    for fid in expired:
        del _fishing_sessions[fid]
    # Clean up old cooldown entries
    if len(_fishing_cast_cooldown) > 500:
        cutoff = now - 10
        _fishing_cast_cooldown.clear()

    # Generate fishing session — apply weather effects
    import random as _frnd
    wait_time = round(_frnd.uniform(3.0, 8.0), 1)

    # Get current weather for this island
    weather_info = _get_island_weather(world_id)
    current_weather = weather_info['weather']

    # Stormy weather: 30% chance of line break (no fish, session ends)
    line_break = False
    if current_weather == 'stormy' and _frnd.random() < 0.30:
        line_break = True

    # Tide system affects fishing
    tide_info = _get_tide_info()
    fish = db.pick_random_fish(weather=current_weather)
    fish_id = hashlib.md5(f"{ip}:{now}:{_frnd.random()}".encode()).hexdigest()[:12]

    _fishing_sessions[fish_id] = {
        'world_id': world_id,
        'fish': fish,
        'cast_time': now,
        'bite_time': now + wait_time,
        'catch_window': 0.8,
        'ip': ip,
        'expires': now + wait_time + 5,  # 5s grace after bite
        'line_break': line_break,
        'weather': current_weather,
    }

    return no_cache(jsonify({
        'ok': True,
        'fish_id': fish_id,
        'wait_time': wait_time,
        'weather': current_weather,
        'tide': tide_info,
    }))


@app.route('/api/fishing/reel', methods=['POST'])
def api_fishing_reel():
    """Reel in the fish. Must be within the catch window after the bite."""
    body = request.get_json(silent=True) or {}
    fish_id = body.get('fish_id', '')

    if not fish_id or fish_id not in _fishing_sessions:
        return no_cache(jsonify({'ok': False, 'error': 'Invalid or expired fishing session', 'caught': False})), 400

    session = _fishing_sessions.pop(fish_id)
    now = time.time()

    # Stormy weather: line break check
    if session.get('line_break'):
        return no_cache(jsonify({
            'ok': False, 'caught': False, 'line_break': True,
            'error': '⛈️ The storm snapped your line! No catch this time.',
        }))

    # Check if reeled in too early (before bite)
    if now < session['bite_time']:
        return no_cache(jsonify({'ok': False, 'error': 'Too early! Wait for the bite.', 'caught': False, 'too_early': True}))

    # Check if within catch window (0.8s after bite)
    time_since_bite = now - session['bite_time']
    if time_since_bite > session['catch_window']:
        return no_cache(jsonify({'ok': False, 'error': 'The fish got away! 🐟💨', 'caught': False, 'too_slow': True}))

    # Success! Catch the fish
    fish = session['fish']
    world_id = session['world_id']
    session_weather = session.get('weather', 'sunny')

    # Get user info
    user = _get_current_user()
    user_id = user['id'] if user else None
    user_name = user['name'] if user else 'Anonymous'

    # Apply sunny coin bonus (+10%)
    coins_earned = fish['coins']
    if session_weather == 'sunny':
        coins_earned = int(coins_earned * 1.1)

    # Timed event: fishing_frenzy or golden_hour bonus
    _te_fishing_bonus = None
    try:
        _te_conn = db.get_conn()
        _te_evt = db.get_active_timed_event(_te_conn, world_id)
        if _te_evt and _te_evt['event_type'] in ('fishing_frenzy', 'golden_hour', 'mystery_fog'):
            coins_earned = int(coins_earned * _te_evt['bonus_multiplier'])
            _te_fishing_bonus = _te_evt['event_type']
            db.increment_timed_event_participants(_te_conn, _te_evt['id'])
        _te_conn.close()
    except Exception:
        pass

    # Award coins
    db.earn_coins(world_id, coins_earned, f"fishing_{fish['type']}")

    # Record the catch
    db.record_catch(world_id, user_id, user_name, fish['type'], fish['emoji'], fish['rarity'], coins_earned)

    # Track quest progress
    try:
        db.advance_quest(world_id, 'fish')
    except Exception:
        pass

    # Track island daily quest progress (fish)
    try:
        from datetime import datetime as _dt, timezone as _tz
        _today = _dt.now(_tz.utc).strftime('%Y-%m-%d')
        _ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '0.0.0.0'
        db.increment_island_quest_progress(world_id, _today, 'fish', _ip)
    except Exception:
        pass

    # Feed event
    try:
        rarity_label = f" **{fish['rarity'].upper()}**" if fish['rarity'] in ('rare', 'legendary') else ''
        weather_bonus = ' (☀️+10%)' if session_weather == 'sunny' else ''
        db.add_feed_event(world_id, 'fishing',
            f"🎣 {user_name} caught a{rarity_label} {fish['emoji']} {fish['type']}! (+{coins_earned}💎{weather_bonus})", '🎣')
    except Exception:
        pass

    # Visitor achievement: fish_caught + coins_earned
    _va_fish_new = []
    try:
        if user_id:
            db.increment_visitor_stat(user_id, 'fish_caught')
            db.increment_visitor_stat(user_id, 'coins_earned', coins_earned)
            _va_fish_new = _check_visitor_achievements(user_id)
    except Exception:
        pass

    _fish_resp = {
        'ok': True,
        'caught': True,
        'fish': {
            'type': fish['type'],
            'emoji': fish['emoji'],
            'rarity': fish['rarity'],
            'coins': coins_earned,
        },
        'user_name': user_name,
        'weather': session_weather,
    }
    if _va_fish_new:
        _fish_resp['new_achievements'] = _va_fish_new
    return no_cache(jsonify(_fish_resp))


@app.route('/api/fishing/catches')
def api_fishing_catches():
    """Get recent fishing catches for a world."""
    world_id = request.args.get('world', _req_world_id())
    limit = min(int(request.args.get('limit', 20)), 50)
    catches = db.get_recent_catches(world_id, limit=limit)
    return no_cache(jsonify({'ok': True, 'catches': catches}))


@app.route('/api/fishing/collection')
def api_fishing_collection():
    """Get fish collection / aquarium data for a world."""
    world_id = request.args.get('world', _req_world_id())
    caught = db.get_fish_collection(world_id)
    all_fish = [{'type': f['type'], 'emoji': f['emoji'], 'rarity': f['rarity'], 'coins': f['coins']} for f in db.FISH_POOL + db.ICE_FISH]
    return no_cache(jsonify({'ok': True, 'caught': caught, 'all_fish': all_fish, 'total': len(db.FISH_POOL + db.ICE_FISH)}))


# ── Treasure Hunt System (evo-189) ──────────────────────────────

import hashlib as _treasure_hashlib

TREASURE_TYPES = [
    # (type_id, emoji, name, reward_type, min_coins, max_coins, weight)
    ('gold_coin',      '🪙', 'Gold Coin',       'coins',       5,  15, 50),
    ('gem',            '💎', 'Gem',              'coins',      20,  50, 20),
    ('ancient_scroll', '📜', 'Ancient Scroll',   'collectible', 0,   0, 15),
    ('mystery_key',    '🗝️', 'Mystery Key',      'bonus',       0,   0, 10),
    ('crown_fragment', '👑', 'Crown Fragment',   'collectible', 0,   0,  5),
]

# Collectible types that get added to the collection book
TREASURE_COLLECTIBLES = {'ancient_scroll', 'mystery_key', 'crown_fragment'}


def _pick_treasure_type(h_int):
    """Pick treasure type based on weighted random using hash integer."""
    weights = [t[6] for t in TREASURE_TYPES]
    total = sum(weights)
    pick = h_int % total
    cumulative = 0
    for t in TREASURE_TYPES:
        cumulative += t[6]
        if pick < cumulative:
            return t
    return TREASURE_TYPES[0]


def _generate_treasures(world_id, hour_slot, island_level):
    """Generate deterministic treasures for this island+hour slot."""
    # Number of treasures: 1-3 based on island level
    if island_level >= 10:
        num_treasures = 3
    elif island_level >= 5:
        num_treasures = 2
    else:
        num_treasures = 1

    treasures = []
    for i in range(num_treasures):
        seed = f"{world_id}:{hour_slot}:{i}"
        h = _treasure_hashlib.sha256(seed.encode()).hexdigest()
        h_int = int(h[:8], 16)
        h2_int = int(h[8:16], 16)
        h3_int = int(h[16:24], 16)
        h4_int = int(h[24:32], 16)

        # Pick type
        ttype = _pick_treasure_type(h_int)
        type_id, emoji, name, reward_type, min_coins, max_coins, _ = ttype

        # Coin reward (for coin types)
        if reward_type == 'coins' and max_coins > min_coins:
            coins_range = max_coins - min_coins
            reward_amount = min_coins + (h2_int % (coins_range + 1))
        else:
            reward_amount = 0

        # Position: x: 10-90%, y: 20-80%
        x = 10 + (h3_int % 81)   # 10..90
        y = 20 + (h4_int % 61)   # 20..80

        treasure_id = f"t_{world_id}_{hour_slot}_{i}"
        treasures.append({
            'id': treasure_id,
            'type': type_id,
            'emoji': emoji,
            'name': name,
            'x': x,
            'y': y,
            'reward_type': reward_type,
            'reward_amount': reward_amount,
        })
    return treasures


@app.route('/api/island/<world_id>/treasures')
def api_get_treasures(world_id):
    """GET active unfound treasures for an island. Auto-spawns if needed."""
    treasures = db.get_active_island_treasures(world_id)
    config = db.TREASURE_TYPE_CONFIG
    result = []
    for t in treasures:
        ttype = t['treasure_type']
        cfg = config.get(ttype, {'emoji': '🐚', 'name': ttype})
        result.append({
            'id': t['id'],
            'type': ttype,
            'x': t['x'],
            'y': t['y'],
            'emoji': cfg['emoji'],
            'name': cfg['name'],
        })
    return no_cache(jsonify({'ok': True, 'treasures': result}))


@app.route('/api/island/<world_id>/treasures/collect', methods=['POST'])
def api_collect_treasure(world_id):
    """Visitor clicks a treasure location. Body: {treasure_id, x, y}.
    Check distance (0.05 normalized). Rate limit: 5 per IP per island per hour."""
    body = request.get_json(silent=True) or {}
    treasure_id = body.get('treasure_id')
    click_x = float(body.get('x', 0))
    click_y = float(body.get('y', 0))
    visitor_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'

    if not treasure_id:
        return no_cache(jsonify({'ok': False, 'error': 'Missing treasure_id'})), 400

    # Rate limit: max 5 collections per IP per island per hour
    collect_count = db.count_treasure_collections_by_ip(world_id, visitor_ip)
    if collect_count >= 5:
        return no_cache(jsonify({'ok': False, 'error': 'Treasure limit reached (5/hour). Come back later!', 'rate_limited': True})), 429

    # Try to collect (checks distance + marks found)
    result = db.collect_island_treasure(world_id, treasure_id, click_x, click_y, visitor_ip)
    if not result:
        return no_cache(jsonify({'ok': False, 'error': 'Treasure not found or already collected', 'already_found': True})), 409

    # Award coins to visitor (if logged in) AND island owner
    coins_awarded = result['coins_reward']
    # Timed event bonus
    try:
        _tr_conn = db.get_conn()
        _tr_evt = db.get_active_timed_event(_tr_conn, world_id)
        if _tr_evt and _tr_evt['event_type'] in ('golden_hour', 'mystery_fog', 'treasure_rain'):
            coins_awarded = int(coins_awarded * _tr_evt['bonus_multiplier'])
            db.increment_timed_event_participants(_tr_conn, _tr_evt['id'])
        _tr_conn.close()
    except Exception:
        pass

    # Award coins to island owner
    db.earn_coins(world_id, coins_awarded, f"treasure_{result['treasure_type']}")

    # Also award coins to visitor's own island if logged in
    user = _get_current_user()
    if user:
        visitor_world = db.get_user_world_id(user['id'])
        if visitor_world and visitor_world != world_id:
            db.earn_coins(visitor_world, coins_awarded, f"treasure_find_{result['treasure_type']}")

    # Feed event
    try:
        finder_name = user['name'] if user else 'A visitor'
        db.add_feed_event(world_id, 'treasure',
            f"🏴‍☠️ {finder_name} found a {result['emoji']} {result['name']}! (+{coins_awarded}💎)", '🏴‍☠️')
    except Exception:
        pass

    # Quest/challenge progress
    try:
        db.update_challenge_progress(world_id, 'collect_event', 1)
    except Exception:
        pass

    # Track island daily quest progress (treasure)
    try:
        _today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        db.increment_island_quest_progress(world_id, _today, 'treasure', visitor_ip)
    except Exception:
        pass

    # Visitor achievement: treasures_found + coins_earned
    _va_treasure_new = []
    try:
        if user:
            db.increment_visitor_stat(user['id'], 'treasures_found')
            db.increment_visitor_stat(user['id'], 'coins_earned', coins_awarded)
            _va_treasure_new = _check_visitor_achievements(user['id'])
    except Exception:
        pass

    _treasure_resp = {
        'ok': True,
        'treasure': {
            'id': result['id'],
            'type': result['treasure_type'],
            'emoji': result['emoji'],
            'name': result['name'],
        },
        'coins_awarded': coins_awarded,
    }
    if _va_treasure_new:
        _treasure_resp['new_achievements'] = _va_treasure_new
    return no_cache(jsonify(_treasure_resp))


@app.route('/api/island/<world_id>/treasure-stats')
def api_treasure_stats(world_id):
    """Return total treasures found on this island and total coins earned."""
    stats = db.get_treasure_hunt_stats(world_id)
    return no_cache(jsonify({'ok': True, **stats}))


# ── Island Daily Quests API ────────────────────────────────────

@app.route('/api/island/<world_id>/quests')
def api_island_quests(world_id):
    """Get today's island quests and visitor's progress."""
    from datetime import datetime as _dt, timezone as _tz
    today = _dt.now(_tz.utc).strftime('%Y-%m-%d')
    quests = db.get_island_quests(world_id, today)
    ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '0.0.0.0'
    progress = db.get_island_quest_progress(world_id, today, ip)
    result = []
    for q in quests:
        qtype = q['quest_type']
        p = progress.get(qtype, {'progress': 0, 'completed': 0, 'claimed': 0})
        result.append({
            'quest_type': qtype,
            'desc': q['quest_desc'],
            'target': q['target_count'],
            'reward': q['reward_coins'],
            'progress': p['progress'],
            'completed': bool(p['completed']),
            'claimed': bool(p['claimed']),
        })
    return no_cache(jsonify({'ok': True, 'quests': result, 'date': today}))


@app.route('/api/island/<world_id>/quests/claim', methods=['POST'])
def api_claim_island_quest(world_id):
    """Claim reward for a completed island quest."""
    data = request.get_json() or {}
    quest_type = data.get('quest_type', '')
    ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '0.0.0.0'
    from datetime import datetime as _dt, timezone as _tz
    today = _dt.now(_tz.utc).strftime('%Y-%m-%d')
    reward = db.claim_island_quest_reward(world_id, today, quest_type, ip)
    if reward is None:
        return jsonify({'ok': False, 'error': 'Not completed or already claimed'}), 400
    # Award coins to the island
    db.earn_coins(world_id, reward, f'island_quest:{quest_type}')
    # Visitor achievement: quests_completed + coins_earned
    _va_quest_new = []
    try:
        _va_quser = _get_current_user()
        if _va_quser:
            db.increment_visitor_stat(_va_quser['id'], 'quests_completed')
            db.increment_visitor_stat(_va_quser['id'], 'coins_earned', reward)
            _va_quest_new = _check_visitor_achievements(_va_quser['id'])
    except Exception:
        pass
    _quest_resp = {'ok': True, 'reward': reward}
    if _va_quest_new:
        _quest_resp['new_achievements'] = _va_quest_new
    return jsonify(_quest_resp)


# ── Visitor Achievements API ──────────────────────────────────

@app.route('/api/visitor/achievements')
def api_visitor_achievements():
    """Get visitor achievements and stats for the logged-in user."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    user_id = user['id']
    try:
        stats = db.get_visitor_stats(user_id)
        unlocked = db.get_visitor_achievements(user_id)
        achievements = []
        for ach in VISITOR_ACHIEVEMENTS:
            achievements.append({
                'id': ach['id'],
                'name': ach['name'],
                'desc': ach['desc'],
                'stat': ach['stat'],
                'threshold': ach['threshold'],
                'unlocked': ach['id'] in unlocked,
                'unlocked_at': unlocked.get(ach['id']),
                'current': stats.get(ach['stat'], 0),
            })
        return no_cache(jsonify({'ok': True, 'achievements': achievements, 'stats': stats}))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ── Visitor Profile API ───────────────────────────────────────

@app.route('/api/visitor/profile')
def api_visitor_profile():
    """Get visitor profile dashboard for the logged-in user."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    user_id = user['id']
    try:
        stats = db.get_visitor_stats(user_id)
        unlocked = db.get_visitor_achievements(user_id)
        # Compute total activity
        total_activity = sum(stats.get(k, 0) for k in (
            'islands_visited', 'guestbook_posts', 'fish_caught',
            'treasures_found', 'quests_completed', 'reactions_given',
            'gifts_sent', 'coins_earned'))
        # Level: every 50 activity = 1 level, minimum 1
        level = max(1, total_activity // 50 + 1)
        # Fun title based on level
        titles = [
            (1, 'Wandering Crab'), (2, 'Beach Stroller'), (3, 'Tide Watcher'),
            (5, 'Seasoned Explorer'), (7, 'Reef Runner'), (10, 'Island Legend'),
            (15, 'Ocean Sage'), (20, 'Archipelago Master'),
        ]
        title = 'Wandering Crab'
        for lv, t in titles:
            if level >= lv:
                title = t
        # Islands visited (with names)
        conn = db.get_conn()
        rows = conn.execute("""
            SELECT v.island_id, v.visited_at, w.name
            FROM visitor_island_visits v
            LEFT JOIN worlds w ON v.island_id = w.id
            WHERE v.user_id = ?
            ORDER BY v.visited_at DESC
        """, (user_id,)).fetchall()
        conn.close()
        islands_visited = [{'id': r['island_id'], 'name': r['name'] or r['island_id'], 'visited_at': r['visited_at']} for r in rows]
        # Joined: earliest visit timestamp
        joined = islands_visited[-1]['visited_at'] if islands_visited else None
        return no_cache(jsonify({
            'ok': True,
            'name': user.get('name', 'Visitor'),
            'avatar': user.get('avatar', ''),
            'stats': stats,
            'achievements_unlocked': len(unlocked),
            'achievements_total': len(VISITOR_ACHIEVEMENTS),
            'islands_visited': islands_visited[:20],
            'level': level,
            'title': title,
            'total_activity': total_activity,
            'joined': joined,
        }))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ── Tide Bottle Messages ──────────────────────────────────────
import random as _bottle_rnd

BOTTLE_EMOJIS = ['🍾', '📜', '🌊', '⭐', '🐚']

@app.route('/api/bottles/send', methods=['POST'])
def api_bottles_send():
    """Send a message in a bottle (requires login, rate limited)."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Log in to send a bottle'}), 401
    body = request.get_json(silent=True) or {}
    message = (body.get('message') or '').strip()
    world_id = body.get('world_id') or request.args.get('world', 'default')
    if not message or len(message) > 140:
        return jsonify({'ok': False, 'error': 'Message must be 1-140 characters'}), 400

    # Rate limit: 1 bottle per IP per 10 min
    ip_raw = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]
    import time as _bt
    now = _bt.time()
    last = db._bottle_send_cooldown.get(ip_hash, 0)
    if now - last < 600:
        return jsonify({'ok': False, 'error': 'Please wait before sending another bottle (10 min cooldown)'}), 429
    db._bottle_send_cooldown[ip_hash] = now

    emoji = _bottle_rnd.choice(BOTTLE_EMOJIS)
    bottle = db.create_bottle(
        sender_name=user.get('name', 'Visitor'),
        sender_id=user['id'],
        message=message,
        origin_island=world_id,
        emoji=emoji
    )

    # Track visitor stat
    try:
        db.increment_visitor_stat(user['id'], 'bottles_sent')
    except Exception:
        pass

    return jsonify({'ok': True, 'bottle_id': bottle['id'], 'emoji': emoji})


@app.route('/api/bottles/beach')
def api_bottles_beach():
    """Get bottles on this island's beach + maybe deliver a new one."""
    world_id = request.args.get('world_id') or request.args.get('world', 'default')

    # Try to deliver a bottle
    try:
        db.maybe_deliver_bottle(world_id)
    except Exception:
        pass

    bottles = db.get_beach_bottles(world_id, limit=5)
    unfound = sum(1 for b in bottles if not b.get('found_at'))
    return no_cache(jsonify({'bottles': bottles, 'count': len(bottles), 'unfound': unfound}))


@app.route('/api/bottles/find', methods=['POST'])
def api_bottles_find():
    """Mark a bottle as found. Awards 3 coins to finder."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Log in to open bottles'}), 401
    body = request.get_json(silent=True) or {}
    bottle_id = body.get('bottle_id')
    world_id = body.get('world_id') or request.args.get('world', 'default')
    if not bottle_id:
        return jsonify({'ok': False, 'error': 'Missing bottle_id'}), 400

    finder_name = user.get('name', 'Visitor')
    bottle = db.find_bottle(bottle_id, finder_name)
    if not bottle:
        return jsonify({'ok': False, 'error': 'Bottle not found'}), 404

    # Award 3 coins to the island where it was found
    coins_result = db.earn_coins(world_id, 3, 'bottle_found')

    # Track visitor coins_earned
    try:
        db.increment_visitor_stat(user['id'], 'coins_earned', 3)
    except Exception:
        pass

    return jsonify({'ok': True, 'bottle': bottle, 'coins': coins_result.get('coins', 0)})


@app.route('/api/bottles/sent')
def api_bottles_sent():
    """Get bottles the current user has sent."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    bottles = db.get_sent_bottles(user['id'])
    return no_cache(jsonify({'bottles': bottles}))


# ── Bottle Messages API (cross-island) ─────────────────────────

@app.route('/api/island/<world_id>/bottle', methods=['POST'])
def api_island_bottle_toss(world_id):
    """Toss a message in a bottle from this island."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    body = request.get_json(silent=True) or {}
    name = (body.get('name') or 'Anonymous').strip()[:30]
    message = (body.get('message') or '').strip()
    if not message or len(message) > 140:
        return jsonify({'ok': False, 'error': 'Message must be 1-140 characters'}), 400
    if db.check_bottle_rate_limit(world_id):
        return jsonify({'ok': False, 'error': 'Wait 10 minutes between bottles'}), 429
    bottle = db.toss_bottle(world_id, name, message)
    if not bottle:
        return jsonify({'ok': False, 'error': 'No islands to send to'}), 400
    return jsonify({'ok': True, 'bottle': bottle})

@app.route('/api/island/<world_id>/bottles')
def api_island_bottles_landed(world_id):
    """Get bottles that washed up on this island."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    bottles = db.get_landed_bottles(world_id, limit=3)
    return no_cache(jsonify({'ok': True, 'bottles': bottles, 'count': len(bottles)}))

@app.route('/api/bottle/<int:bottle_id>/find', methods=['POST'])
def api_bottle_find(bottle_id):
    """Mark a bottle as found."""
    body = request.get_json(silent=True) or {}
    name = (body.get('name') or 'Anonymous').strip()[:30]
    bottle = db.find_msg_bottle(bottle_id, name)
    if not bottle:
        return jsonify({'ok': False, 'error': 'Bottle not found'}), 404
    return jsonify({'ok': True, 'bottle': bottle})

@app.route('/api/bottles/stats')
def api_bottles_stats():
    """Global bottle message stats."""
    stats = db.get_bottle_stats()
    return no_cache(jsonify({'ok': True, 'stats': stats}))


# ── Timed Island Events API ────────────────────────────────────

@app.route('/api/island/<world_id>/events')
def api_timed_events(world_id):
    """Get active timed event + next event estimate."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    conn = db.get_conn()
    # Try to spawn an event
    try:
        db.check_and_spawn_timed_event(conn, world_id)
    except Exception:
        pass
    event = db.get_active_timed_event(conn, world_id)
    # Estimate next event: minutes until next hour slot
    import time as _tev_time
    now = _tev_time.time()
    next_hour = ((int(now // 3600) + 1) * 3600) - now
    conn.close()
    return no_cache(jsonify({
        'event': event,
        'next_check_in': int(next_hour),
    }))


@app.route('/api/island/<world_id>/events/history')
def api_timed_events_history(world_id):
    """Last 10 timed events for this island."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    resolved = db.resolve_world_id(world_id)
    if resolved:
        world_id = resolved
    conn = db.get_conn()
    history = db.get_timed_event_history(conn, world_id, limit=10)
    conn.close()
    return no_cache(jsonify({'events': history}))


# ── Push Notification API ────────────────────────────────────────

@app.route('/api/push/vapid-public-key')
def api_push_vapid_key():
    """Return VAPID public key for push subscription."""
    keys = notifications.vapid_keys()
    return jsonify({'ok': True, 'publicKey': keys['public_key']})

@app.route('/api/push/subscribe', methods=['POST'])
def api_push_subscribe():
    """Save push subscription for current user."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    body = request.get_json() or {}
    sub = body.get('subscription', {})
    endpoint = sub.get('endpoint', '')
    keys = sub.get('keys', {})
    p256dh = keys.get('p256dh', '')
    auth_key = keys.get('auth', '')
    if not endpoint or not p256dh or not auth_key:
        return jsonify({'ok': False, 'error': 'Invalid subscription'}), 400
    conn = db.get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO user_push_subscriptions (user_id, endpoint, p256dh, auth)
        VALUES (?, ?, ?, ?)
    """, (user['id'], endpoint, p256dh, auth_key))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/push/unsubscribe', methods=['POST'])
def api_push_unsubscribe():
    """Remove push subscription."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    body = request.get_json() or {}
    endpoint = body.get('endpoint', '')
    conn = db.get_conn()
    conn.execute("DELETE FROM user_push_subscriptions WHERE user_id=? AND endpoint=?",
                 (user['id'], endpoint))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/notifications/preferences', methods=['GET', 'POST'])
def api_notification_prefs():
    """Get or set notification preferences."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Not logged in'}), 401
    conn = db.get_conn()
    if request.method == 'GET':
        prefs = conn.execute(
            "SELECT push_enabled, email_enabled, quiet_start, quiet_end FROM user_notification_prefs WHERE user_id=?",
            (user['id'],)
        ).fetchone()
        conn.close()
        if prefs:
            return jsonify({'ok': True, 'prefs': dict(prefs)})
        return jsonify({'ok': True, 'prefs': {'push_enabled': 1, 'email_enabled': 1, 'quiet_start': '22:00', 'quiet_end': '08:00'}})
    else:
        body = request.get_json() or {}
        conn.execute("""
            INSERT INTO user_notification_prefs (user_id, push_enabled, email_enabled, quiet_start, quiet_end, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                push_enabled=excluded.push_enabled, email_enabled=excluded.email_enabled,
                quiet_start=excluded.quiet_start, quiet_end=excluded.quiet_end, updated_at=excluded.updated_at
        """, (user['id'], body.get('push_enabled', 1), body.get('email_enabled', 1),
              body.get('quiet_start', '22:00'), body.get('quiet_end', '08:00'), time.time()))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})

# ── Time Capsules ─────────────────────────────────────────────

CAPSULE_DELAYS = {
    '1h':  3600,
    '24h': 86400,
    '7d':  604800,
}
CAPSULE_DELAY_LABELS = {
    '1h':  '1 hour',
    '24h': '24 hours',
    '7d':  '7 days',
}

@app.route('/api/island/<world_id>/capsules', methods=['POST'])
def api_island_capsules_post(world_id):
    """Bury a time capsule on an island."""
    body = request.get_json(silent=True) or {}
    message = (body.get('message') or '').strip()
    delay = body.get('delay', '24h')

    if not message or len(message) > 200:
        return jsonify({'ok': False, 'error': 'Message must be 1-200 characters'}), 400
    if delay not in CAPSULE_DELAYS:
        return jsonify({'ok': False, 'error': 'Invalid delay. Choose 1h, 24h, or 7d'}), 400

    # Determine author
    user = _get_current_user()
    if user:
        author_name = user.get('name') or user.get('email', 'Visitor').split('@')[0]
        author_id = user['id']
    else:
        ip_raw = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or 'unknown'
        author_name = (body.get('name') or 'Anonymous').strip()[:30] or 'Anonymous'
        author_id = 'ip:' + hashlib.sha256(ip_raw.encode()).hexdigest()[:16]

    # Rate limit: 1 capsule per author per island per 24h
    if db.check_capsule_rate_limit(world_id, author_id):
        return jsonify({'ok': False, 'error': 'You can only bury 1 capsule per island per 24 hours'}), 429

    now = time.time()
    unlock_at = now + CAPSULE_DELAYS[delay]

    capsule = db.add_time_capsule(world_id, author_name, author_id, message, now, unlock_at)
    return jsonify({
        'ok': True,
        'unlock_at': unlock_at,
        'delay_label': CAPSULE_DELAY_LABELS[delay],
        'capsule_id': capsule['id'],
    })


@app.route('/api/island/<world_id>/capsules', methods=['GET'])
def api_island_capsules_get(world_id):
    """List time capsules for an island. Locked capsules have messages redacted."""
    now = time.time()
    capsules_raw = db.get_time_capsules(world_id, limit=20)
    counts = db.get_time_capsule_counts(world_id)

    capsules = []
    for c in capsules_raw:
        entry = {
            'id': c['id'],
            'author_name': c['author_name'],
            'buried_at': c['buried_at'],
            'unlock_at': c['unlock_at'],
        }
        if now >= c['unlock_at']:
            entry['locked'] = False
            entry['message'] = c['message']
        else:
            entry['locked'] = True
            entry['message'] = None
        capsules.append(entry)

    return no_cache(jsonify({
        'capsules': capsules,
        'locked_count': counts['locked'],
        'unlocked_count': counts['unlocked'],
        'total': counts['total'],
    }))


@app.route('/sw.js')
def serve_sw():
    """Serve service worker from root path (required for push scope)."""
    return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'frontend'), 'sw.js',
                               mimetype='application/javascript')


def _notify_owner(owner_id, event_type, title, body, island_id=None):
    """Helper to trigger notification for island owner."""
    notifications.notify_island_owner(owner_id, event_type, title, body, island_id, db.get_conn)


# ── Island Portal Links API ───────────────────────────────────

@app.route('/api/island/<world_id>/portals', methods=['GET'])
def api_island_portals_get(world_id):
    """List portals for an island (public)."""
    portals = db.get_portals(world_id)
    # Look up target island names from worlds table if not stored
    conn = db.get_conn()
    for p in portals:
        if not p.get('target_island_name'):
            row = conn.execute("SELECT name FROM worlds WHERE id=?", (p['target_island_id'],)).fetchone()
            p['target_island_name'] = row['name'] if row else 'Unknown Island'
    conn.close()
    return no_cache(jsonify({'portals': portals}))


@app.route('/api/island/<world_id>/portals', methods=['POST'])
def api_island_portals_post(world_id):
    """Create a portal on an island (owner only)."""
    # Check ownership
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Login required'}), 401
    owner_id = db.get_world_owner(world_id)
    if owner_id != user['id']:
        return jsonify({'ok': False, 'error': 'Only the island owner can create portals'}), 403

    body = request.get_json(silent=True) or {}
    target_island_id = (body.get('target_island_id') or '').strip()
    label = (body.get('label') or 'Portal').strip()[:30]
    col = int(body.get('col', 16))
    row = int(body.get('row', 16))

    if not target_island_id:
        return jsonify({'ok': False, 'error': 'Target island ID is required'}), 400
    if target_island_id == world_id:
        return jsonify({'ok': False, 'error': 'Cannot create a portal to the same island'}), 400

    # Validate target island exists
    target_world = db.load_world(target_island_id)
    if not target_world:
        return jsonify({'ok': False, 'error': 'Target island not found'}), 404

    # Get target island name
    conn = db.get_conn()
    target_row = conn.execute("SELECT name FROM worlds WHERE id=?", (target_island_id,)).fetchone()
    conn.close()
    target_name = target_row['name'] if target_row else 'Unknown Island'

    result = db.add_portal(world_id, target_island_id, target_name, label, col, row)
    if not result.get('ok'):
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/island/<world_id>/portals/<int:portal_id>', methods=['DELETE'])
def api_island_portals_delete(world_id, portal_id):
    """Delete a portal from an island (owner only)."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Login required'}), 401
    owner_id = db.get_world_owner(world_id)
    if owner_id != user['id']:
        return jsonify({'ok': False, 'error': 'Only the island owner can delete portals'}), 403

    result = db.delete_portal(portal_id, world_id)
    if not result.get('ok'):
        return jsonify(result), 404
    return jsonify(result)


# ── Island Live Chat ──────────────────────────────────────────

_chat_rate_limit = {}  # (world_id, user_id) -> last_post_time

@app.route('/api/island/<world_id>/chat')
def api_island_chat_get(world_id):
    """Get recent chat messages for an island."""
    db.cleanup_expired_chat()
    messages = db.get_chat_messages(world_id, limit=30)
    return no_cache(jsonify({'ok': True, 'messages': messages}))

@app.route('/api/island/<world_id>/chat', methods=['POST'])
def api_island_chat_post(world_id):
    """Post a chat message on an island (logged-in visitors only)."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Login required'}), 401

    body = request.get_json(silent=True) or {}
    message = (body.get('message') or '').strip()
    if not message:
        return jsonify({'ok': False, 'error': 'Message required'}), 400
    if len(message) > 100:
        return jsonify({'ok': False, 'error': 'Message too long (max 100 chars)'}), 400

    # Rate limit: 1 msg per 5 seconds per user per island
    import time as _time_mod
    key = (world_id, user['id'])
    now = _time_mod.time()
    if key in _chat_rate_limit and now - _chat_rate_limit[key] < 5:
        return jsonify({'ok': False, 'error': 'Too fast! Wait a few seconds.'}), 429
    _chat_rate_limit[key] = now

    display_name = user.get('display_name') or user.get('email', 'Anonymous')[:20]
    db.post_chat_message(world_id, user['id'], display_name, message)

    # Track visitor stat
    try:
        db.increment_visitor_stat(user['id'], 'chat_messages_sent', 1)
    except Exception:
        pass

    messages = db.get_chat_messages(world_id, limit=30)
    return jsonify({'ok': True, 'messages': messages})


# ── Captain's Log API ─────────────────────────────────────────

_captains_log_rate_limit = {}  # world_id -> last_post_time

@app.route('/api/island/<world_id>/log', methods=['GET'])
def api_captains_log_get(world_id):
    """Get recent captain's log entries (public)."""
    entries = db.get_captains_log(world_id, limit=20)
    total = db.count_captains_log(world_id)
    return no_cache(jsonify({'ok': True, 'entries': entries, 'total': total}))


@app.route('/api/island/<world_id>/log', methods=['POST'])
def api_captains_log_post(world_id):
    """Post a captain's log entry (owner only)."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Login required'}), 401
    owner_id = db.get_world_owner(world_id)
    if owner_id != user['id']:
        return jsonify({'ok': False, 'error': 'Only the island owner can post log entries'}), 403

    body = request.get_json(silent=True) or {}
    message = (body.get('message') or '').strip()
    emoji = (body.get('emoji') or '📝').strip()

    if not message:
        return jsonify({'ok': False, 'error': 'Message required'}), 400
    if len(message) > 280:
        return jsonify({'ok': False, 'error': 'Message too long (max 280 chars)'}), 400

    # Rate limit: 1 post per 2 minutes per island
    import time as _time_mod
    now = _time_mod.time()
    if world_id in _captains_log_rate_limit and now - _captains_log_rate_limit[world_id] < 120:
        remaining = int(120 - (now - _captains_log_rate_limit[world_id]))
        return jsonify({'ok': False, 'error': f'Too fast! Wait {remaining}s before posting again.'}), 429
    _captains_log_rate_limit[world_id] = now

    result = db.add_captains_log(world_id, message, emoji)
    return no_cache(jsonify(result))


@app.route('/api/island/<world_id>/log/<int:log_id>', methods=['DELETE'])
def api_captains_log_delete(world_id, log_id):
    """Delete a captain's log entry (owner only)."""
    user = _get_current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'Login required'}), 401
    owner_id = db.get_world_owner(world_id)
    if owner_id != user['id']:
        return jsonify({'ok': False, 'error': 'Only the island owner can delete log entries'}), 403

    result = db.delete_captains_log(log_id, world_id)
    if not result.get('ok'):
        return jsonify(result), 404
    return no_cache(jsonify(result))


@app.route('/api/shooting-star/wish', methods=['POST'])
def api_shooting_star_wish():
    """Claim a shooting star wish for bonus coins."""
    import random as _star_rnd
    world_id = _req_world_id()
    if not world_id:
        return jsonify({'ok': False, 'error': 'No world'}), 400

    # Rate limit: max 1 wish per 5 minutes per world
    cache_key = f'star_wish_{world_id}'
    now = time.time()
    last_wish = getattr(api_shooting_star_wish, '_cache', {}).get(cache_key, 0)
    if now - last_wish < 300:
        return jsonify({'ok': False, 'error': 'Too soon! Stars need time to recharge ✨'}), 429

    # Award 15-50 coins randomly
    reward = _star_rnd.choice([15, 20, 25, 30, 35, 40, 50])
    db.earn_coins(world_id, reward, reason='shooting_star_wish')

    # Update cache
    if not hasattr(api_shooting_star_wish, '_cache'):
        api_shooting_star_wish._cache = {}
    api_shooting_star_wish._cache[cache_key] = now

    # Broadcast to all viewers
    _broadcast_world_event('shooting_star_wish', {
        'world_id': world_id,
        'reward': reward
    })

    balance = db.get_progress(world_id).get('shells', 0)
    return jsonify({'ok': True, 'reward': reward, 'balance': balance, 'message': f'⭐ Your wish was heard! +{reward} coins'})


def _warmup_thumbnails():
    """Pre-generate thumbnails for all islands on startup."""
    try:
        all_islands = db.list_worlds(sort='popular', limit=100)
        generated = 0
        for island in all_islands:
            wid = island.get('world_id')
            if not wid:
                continue
            # Skip if already cached and fresh
            cached = os.path.join(THUMB_CACHE_DIR, f'{wid}.png')
            if os.path.exists(cached):
                age = time.time() - os.path.getmtime(cached)
                if age < THUMB_CACHE_TTL:
                    continue
            # Also check jpg
            cached_jpg = os.path.join(THUMB_CACHE_DIR, f'{wid}.jpg')
            if os.path.exists(cached_jpg):
                age = time.time() - os.path.getmtime(cached_jpg)
                if age < THUMB_CACHE_TTL:
                    continue
            _regenerate_thumbnail(wid)
            generated += 1
        if generated:
            app.logger.info(f'Thumbnail warmup: generated {generated} thumbnails')
    except Exception as e:
        app.logger.warning(f'Thumbnail warmup failed: {e}')

# ── Island Critters System (evo-246) ──────────────────────────────
@app.route('/api/island/<world_id>/critters')
def api_island_critters(world_id):
    """Return critter spawn config based on island terrain analysis."""
    data = _load_world_data(world_id)
    if not data:
        return jsonify({'ok': False, 'error': 'World not found'}), 404

    terrain = data.get('terrain', [])
    objects = data.get('objects', [])

    # Count terrain categories
    sand_count = 0
    water_count = 0
    rock_count = 0
    grass_count = 0
    for t in terrain:
        tid = t[3] if len(t) > 3 else ''
        if 'sand' in tid:
            sand_count += 1
        elif 'water' in tid:
            water_count += 1
        elif 'stone' in tid or 'rock' in tid:
            rock_count += 1
        elif 'grass' in tid or 'dirt' in tid:
            grass_count += 1

    # Count flower/garden objects
    flower_count = 0
    for o in objects:
        ot = o.get('type', '')
        if 'flower' in ot or 'garden' in ot or 'bonsai' in ot:
            flower_count += 1

    # Determine critter counts based on terrain
    crabs = min(4, sand_count // 15) if sand_count >= 5 else 0
    butterflies = min(3, flower_count) if flower_count >= 1 else (1 if grass_count >= 30 else 0)
    seagulls = min(2, water_count // 40) if water_count >= 20 else 0
    lizards = 1 if rock_count >= 3 else 0  # 20% spawn chance applied on frontend

    return no_cache(jsonify({
        'ok': True,
        'critters': {
            'crabs': crabs,
            'butterflies': butterflies,
            'seagulls': seagulls,
            'lizards': lizards,
        },
        'terrain_summary': {
            'sand': sand_count,
            'water': water_count,
            'rock': rock_count,
            'grass': grass_count,
            'flowers': flower_count,
        }
    }))
# ── End Island Critters System (evo-246) ──


# ── Island Expeditions System ──────────────────────────────────
@app.route('/api/island/<world_id>/expedition', methods=['GET'])
def api_island_expedition_check(world_id):
    """Check current expedition status (auto-completes if timer done)."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    exp = db.check_expedition(world_id)
    if not exp:
        return no_cache(jsonify({'ok': True, 'expedition': None}))
    return no_cache(jsonify({'ok': True, 'expedition': exp}))


@app.route('/api/island/<world_id>/expedition', methods=['POST'])
def api_island_expedition_start(world_id):
    """Start a new expedition (owner only)."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Only the island owner can start expeditions'}), 403
    body = request.get_json(silent=True) or {}
    destination = (body.get('destination') or '').strip().lower()
    if destination not in ('reef', 'deep_sea', 'shipwreck', 'volcano'):
        return jsonify({'ok': False, 'error': 'Invalid destination'}), 400
    exp, err = db.start_expedition(world_id, destination)
    if err:
        return jsonify({'ok': False, 'error': err}), 400
    return jsonify({'ok': True, 'expedition': exp})


@app.route('/api/island/<world_id>/expedition/history', methods=['GET'])
def api_island_expedition_history(world_id):
    """Get expedition history."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    history = db.get_expedition_history(world_id, limit=10)
    return no_cache(jsonify({'ok': True, 'history': history}))


@app.route('/api/island/<world_id>/expedition/<int:expedition_id>/claim', methods=['POST'])
def api_island_expedition_claim(world_id, expedition_id):
    """Claim loot from a completed expedition (owner only)."""
    world_id = re.sub(r'[^a-zA-Z0-9_\-]', '', world_id)
    if not is_owner_request():
        return jsonify({'ok': False, 'error': 'Only the island owner can claim loot'}), 403
    exp = db.complete_expedition(expedition_id)
    if not exp:
        return jsonify({'ok': False, 'error': 'No completed expedition to claim'}), 400
    return jsonify({'ok': True, 'expedition': exp})
# ── End Island Expeditions System ──


# Run warmup in background thread on startup
threading.Thread(target=_warmup_thumbnails, daemon=True).start()

if __name__ == '__main__':
    # Initialize notification tables
    conn = db.get_conn()
    notifications.init_push_tables(conn)
    conn.close()
    # Initialize portal tables
    db.init_portals()
    print('🦞 Clawverse v1 backend on :19003')
    app.run(host='0.0.0.0', port=19003, debug=False)
