"""Clawverse — Email-based authentication system.

Flow:
1. User enters email → POST /api/auth/request-code
2. Backend generates 6-digit code, stores in SQLite, sends via gsk email
3. User enters code → POST /api/auth/verify-code
4. Backend verifies code, creates/loads user, returns session token (cookie)
5. All subsequent requests use session cookie for identity
"""
import sqlite3
import os
import json
import secrets
import hashlib
import subprocess
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clawverse.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_tables():
    """Create auth-related tables."""
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT DEFAULT '',
        avatar TEXT DEFAULT '🦞',
        island_name TEXT DEFAULT '',
        created_at TEXT,
        last_login TEXT
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT,
        expires_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS verification_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        used INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS ip_rate_limit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL,
        created_at REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ip_rate_limit_ip_created ON ip_rate_limit(ip, created_at);
    """)
    conn.commit()
    conn.close()

def generate_user_id(email):
    """Generate a deterministic, URL-safe user ID from email."""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()[:12]

def generate_code():
    """Generate a 6-digit verification code."""
    return f"{secrets.randbelow(900000) + 100000}"

def generate_session_token():
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)

def store_verification_code(email, code, ttl_seconds=600):
    """Store a verification code with expiry (default 10 min)."""
    now = time.time()
    conn = get_conn()
    # Invalidate old codes for this email
    conn.execute("UPDATE verification_codes SET used=1 WHERE email=? AND used=0", (email.lower().strip(),))
    conn.execute(
        "INSERT INTO verification_codes (email, code, created_at, expires_at) VALUES (?,?,?,?)",
        (email.lower().strip(), code, now, now + ttl_seconds)
    )
    conn.commit()
    conn.close()

def verify_code(email, code):
    """Verify a code. Returns True if valid, False otherwise."""
    now = time.time()
    email = email.lower().strip()
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM verification_codes WHERE email=? AND code=? AND used=0 AND expires_at>?",
        (email, code, now)
    ).fetchone()
    if row:
        conn.execute("UPDATE verification_codes SET used=1 WHERE id=?", (row['id'],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_or_create_user(email, name=''):
    """Get existing user or create a new one. Returns user dict."""
    email = email.lower().strip()
    user_id = generate_user_id(email)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if row:
        # Update last_login
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (now, user_id))
        conn.commit()
        user = dict(row)
        user['last_login'] = now
        conn.close()
        return user
    
    # Create new user
    if not name:
        name = email.split('@')[0]
    island_name = f"{name}'s Island"
    conn.execute(
        "INSERT INTO users (id, email, name, avatar, island_name, created_at, last_login) VALUES (?,?,?,?,?,?,?)",
        (user_id, email, name, '🦞', island_name, now, now)
    )
    conn.commit()
    conn.close()
    return {
        'id': user_id, 'email': email, 'name': name, 'avatar': '🦞',
        'island_name': island_name, 'created_at': now, 'last_login': now,
        'is_new': True
    }

def create_session(user_id, ttl_seconds=86400*30):
    """Create a session token for a user (default 30 day expiry)."""
    token = generate_session_token()
    now = datetime.now(timezone.utc).isoformat()
    expires = datetime.fromtimestamp(
        time.time() + ttl_seconds, tz=timezone.utc
    ).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
        (token, user_id, now, expires)
    )
    conn.commit()
    conn.close()
    return token

def get_session_user(token):
    """Get user from session token. Returns user dict or None."""
    if not token:
        return None
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT u.* FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token=? AND s.expires_at>?",
        (token, now)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_session(token):
    """Delete a session (logout)."""
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()

ALLOWED_USER_FIELDS = {'name', 'avatar', 'island_name'}

def update_user(user_id, **kwargs):
    """Update user fields (name, avatar, island_name)."""
    updates = {k: v for k, v in kwargs.items() if k in ALLOWED_USER_FIELDS and v is not None}
    if not updates:
        return
    conn = get_conn()
    for k, v in updates.items():
        if k not in ALLOWED_USER_FIELDS:
            continue  # defense-in-depth: skip any field not in whitelist
        conn.execute(f"UPDATE users SET {k}=? WHERE id=?", (v, user_id))
    conn.commit()
    conn.close()

def list_users(limit=100):
    """List all users."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, email, name, avatar, island_name, created_at, last_login FROM users ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user(user_id):
    """Get a single user by ID."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def send_verification_email(email, code):
    """Send verification code via gsk email send (uses connected Gmail/Outlook)."""
    subject = f"🦞 Clawverse — Your verification code: {code}"
    body = f"""Hi there! 👋

Your Clawverse verification code is:

**{code}**

This code expires in 10 minutes.

If you didn't request this, you can safely ignore this email.

— 🦞 Clawverse
https://ysnlpjle.gensparkclaw.com

(This is an automated message. Please do not reply.)"""
    
    try:
        result = subprocess.run(
            ['gsk', 'email', 'send',
             '--to', email,
             '--subject', subject,
             '--body', body],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

# Rate limiting: max 3 codes per email per 10 minutes, max 10 total per IP per hour
def check_rate_limit(email, window_seconds=600, max_attempts=3):
    """Check if email has exceeded rate limit. Returns True if OK to proceed."""
    now = time.time()
    email = email.lower().strip()
    conn = get_conn()
    # Per-email limit
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM verification_codes WHERE email=? AND created_at>?",
        (email, now - window_seconds)
    ).fetchone()
    if row['cnt'] >= max_attempts:
        conn.close()
        return False
    # Global rate limit: max 50 codes total per hour (anti-bomb)
    row2 = conn.execute(
        "SELECT COUNT(*) as cnt FROM verification_codes WHERE created_at>?",
        (now - 3600,)
    ).fetchone()
    conn.close()
    return row2['cnt'] < 50

def check_email_allowed(email):
    """Block obviously fake/test emails to prevent email bombing."""
    email = email.lower().strip()
    domain = email.split('@')[-1] if '@' in email else ''
    local = email.split('@')[0] if '@' in email else ''
    
    # Block disposable/fake domains (expanded blacklist)
    blocked_domains = [
        # Original list
        'example.com', 'example.org', 'test.com', 'tempmail.com',
        'throwaway.email', 'mailinator.com', 'guerrillamail.com',
        'yopmail.com', 'fakeinbox.com', 'sharklasers.com',
        'guerrillamail.info', 'grr.la', 'dispostable.com',
        # Expanded disposable email domains
        '10minutemail.com', '10minutemail.net', '33mail.com', 'anonbox.net',
        'burnermail.io', 'cockli.com', 'discard.email', 'dispose.it',
        'emailondeck.com', 'emailtemp.org', 'filzmail.com',
        'getairmail.com', 'getnada.com', 'guerillamail.com',
        'guerrillamail.de', 'guerrillamail.net', 'harakirimail.com',
        'hidemail.de', 'inboxbear.com', 'jetable.org', 'klzlk.com',
        'mailcatch.com', 'maildrop.cc', 'mailexpire.com', 'mailforspam.com',
        'mailinator.net', 'mailnesia.com', 'mailnull.com', 'mailsac.com',
        'mohmal.com', 'mytemp.email', 'nada.email', 'nomail.xl.cx',
        'owlpic.com', 'spamgourmet.com', 'spamspot.com',
        'temp-mail.org', 'temp-mail.io', 'tempemail.co', 'tempinbox.com',
        'tempmail.net', 'tempmailer.com', 'trashmail.com', 'trashmail.net',
        'tuta.com', 'tutanota.com', 'wegwerfmail.de', 'yopmail.fr',
        'zep-hyr.com',
    ]
    if domain in blocked_domains:
        return False
    
    # Block obviously scripted local parts (bomb/sectest patterns)
    blocked_prefixes = ['emailbomb', 'sectest', 'parallel_', 'spam_', 'hack_']
    for p in blocked_prefixes:
        if local.startswith(p):
            return False
    
    # Must have a real-looking domain
    if '.' not in domain or len(domain) < 4:
        return False
    return True

# ── Anti-bot protections ──────────────────────────────────────

# Turnstile config (test keys by default; override with env vars for production)
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '1x0000000000000000000000000000000AA')

def verify_turnstile(token, remote_ip=None):
    """Verify a Cloudflare Turnstile response token.
    Returns True if valid, False otherwise."""
    if not token:
        return False
    data = urllib.parse.urlencode({
        'secret': TURNSTILE_SECRET_KEY,
        'response': token,
    })
    if remote_ip:
        data += '&remoteip=' + urllib.parse.quote(remote_ip)
    try:
        req = urllib.request.Request(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data=data.encode('utf-8'),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get('success', False)
    except Exception:
        # If Turnstile service is unreachable, fail open (don't block users)
        return True


def check_honeypot(body):
    """Check honeypot field. Returns True if the request looks human (field empty)."""
    website = (body.get('website') or '').strip()
    return len(website) == 0


def check_ip_rate_limit(ip, window_seconds=3600, max_requests=10):
    """Per-IP rate limiting. Returns True if OK to proceed."""
    if not ip:
        return True
    now = time.time()
    conn = get_conn()
    # Clean up old entries (older than window)
    conn.execute("DELETE FROM ip_rate_limit WHERE created_at < ?", (now - window_seconds,))
    # Count requests in window
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM ip_rate_limit WHERE ip=? AND created_at>?",
        (ip, now - window_seconds)
    ).fetchone()
    conn.commit()
    conn.close()
    return row['cnt'] < max_requests


def record_ip_request(ip):
    """Record an IP request for rate limiting."""
    if not ip:
        return
    now = time.time()
    conn = get_conn()
    conn.execute("INSERT INTO ip_rate_limit (ip, created_at) VALUES (?, ?)", (ip, now))
    conn.commit()
    conn.close()


def check_request_timing(form_opened_at, min_ms=2000):
    """Check if the request was submitted too quickly (likely a bot).
    Returns True if timing looks human."""
    if form_opened_at is None:
        return False  # Missing timestamp — suspicious
    try:
        opened_at = float(form_opened_at)
    except (TypeError, ValueError):
        return False
    now_ms = time.time() * 1000
    elapsed = now_ms - opened_at
    # Reject if submitted in less than min_ms, or if timestamp is in the future
    if elapsed < min_ms or elapsed < 0:
        return False
    return True


# Initialize on import
init_auth_tables()
