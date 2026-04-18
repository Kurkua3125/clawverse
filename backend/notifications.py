"""
Clawverse Push Notification + Email Fallback System
"""
import os, json, time, threading, urllib.request

# ── VAPID Key Management ──
VAPID_KEY_FILE = os.path.join(os.path.dirname(__file__), 'vapid_keys.json')
VAPID_CLAIMS = {"sub": "mailto:noreply@genclawverse.ai"}

def get_vapid_keys():
    """Get or generate VAPID keys for Web Push."""
    if os.path.exists(VAPID_KEY_FILE):
        with open(VAPID_KEY_FILE) as f:
            return json.load(f)
    
    import base64
    from py_vapid import Vapid
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    vapid = Vapid()
    vapid.generate_keys()
    # Get urlsafe base64 public key for Web Push subscription
    pub_raw = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_b64 = base64.urlsafe_b64encode(pub_raw).rstrip(b'=').decode('utf-8')
    keys = {
        'private_key': vapid.private_pem().decode('utf-8'),
        'public_key': pub_b64
    }
    with open(VAPID_KEY_FILE, 'w') as f:
        json.dump(keys, f, indent=2)
    return keys

_vapid_keys = None
def vapid_keys():
    global _vapid_keys
    if _vapid_keys is None:
        _vapid_keys = get_vapid_keys()
    return _vapid_keys

# ── Database Schema ──
def init_push_tables(conn):
    """Create push notification tables."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            created_at REAL DEFAULT (strftime('%s','now')),
            UNIQUE(user_id, endpoint)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_notification_prefs (
            user_id TEXT PRIMARY KEY,
            push_enabled INTEGER DEFAULT 1,
            email_enabled INTEGER DEFAULT 1,
            quiet_start TEXT DEFAULT '22:00',
            quiet_end TEXT DEFAULT '08:00',
            updated_at REAL DEFAULT (strftime('%s','now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_type TEXT,
            sent_at REAL DEFAULT (strftime('%s','now'))
        )
    """)
    conn.commit()

# ── Send Web Push ──
def send_push(user_id, title, body, url='/', event_type='general', db_conn_func=None):
    """Send web push notification to all subscriptions for a user."""
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("[PUSH] pywebpush not installed, skipping push")
        return False

    if db_conn_func is None:
        return False

    conn = db_conn_func()
    subs = conn.execute(
        "SELECT endpoint, p256dh, auth FROM user_push_subscriptions WHERE user_id=?",
        (user_id,)
    ).fetchall()
    conn.close()

    if not subs:
        return False

    keys = vapid_keys()
    payload = json.dumps({
        'title': title,
        'body': body,
        'url': url,
        'event_type': event_type
    })

    sent = False
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub['endpoint'],
                    'keys': {'p256dh': sub['p256dh'], 'auth': sub['auth']}
                },
                data=payload,
                vapid_private_key=keys['private_key'],
                vapid_claims=VAPID_CLAIMS,
                timeout=10
            )
            sent = True
        except Exception as e:
            err = str(e)
            # Remove expired/invalid subscriptions
            if '410' in err or '404' in err:
                try:
                    c = db_conn_func()
                    c.execute("DELETE FROM user_push_subscriptions WHERE endpoint=?", (sub['endpoint'],))
                    c.commit()
                    c.close()
                except:
                    pass
            print(f"[PUSH] Error sending to {sub['endpoint'][:50]}...: {err[:100]}")
    return sent

# ── Send Notification Email ──
def send_notification_email(email, title, body, island_url, api_key=None):
    """Send notification email via MailChannels API."""
    if not api_key:
        api_key = os.environ.get("MAILCHANNELS_API_KEY", "")
    if not api_key:
        print("[EMAIL] No MailChannels API key, skipping email")
        return False

    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#0a1525;color:#ddeeff;border-radius:12px;">
        <h2 style="text-align:center;color:#7cc8ff;">🦞 {title}</h2>
        <p style="text-align:center;font-size:15px;color:#bbddee;line-height:1.5;">{body}</p>
        <div style="text-align:center;margin:20px 0;">
            <a href="{island_url}" style="display:inline-block;padding:12px 32px;background:#44ff88;color:#0a1525;font-weight:bold;font-size:16px;border-radius:8px;text-decoration:none;">View Your Island →</a>
        </div>
        <hr style="border:1px solid #1a3050;margin:20px 0;">
        <p style="text-align:center;font-size:11px;color:#556677;">
            <a href="{island_url}" style="color:#7cc8ff;">genclawverse.ai</a> — Build your pixel island
        </p>
    </div>
    """

    payload = json.dumps({
        "personalizations": [{"to": [{"email": email}], "dkim_domain": "genclawverse.ai", "dkim_selector": "mcdkim"}],
        "from": {"email": "noreply@genclawverse.ai", "name": "Clawverse"},
        "subject": f"🦞 {title}",
        "content": [{"type": "text/html", "value": html_body}]
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.mailchannels.net/tx/v1/send",
            data=payload,
            headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201, 202)
    except Exception as e:
        print(f"[EMAIL] Error: {e}")
        return False

# ── Main Notification Dispatcher ──
def notify_island_owner(owner_id, event_type, title, body, island_id=None, db_conn_func=None):
    """
    Notify an island owner about an event.
    Checks preferences, quiet hours, then dispatches via push and/or email.
    Runs in background thread to not block the request.
    """
    def _do_notify():
        if not db_conn_func:
            return

        conn = db_conn_func()

        # Get user info
        user = conn.execute("SELECT email FROM users WHERE id=?", (owner_id,)).fetchone()
        if not user:
            conn.close()
            return

        # Get preferences (defaults: push=on, email=on)
        prefs = conn.execute(
            "SELECT push_enabled, email_enabled, quiet_start, quiet_end FROM user_notification_prefs WHERE user_id=?",
            (owner_id,)
        ).fetchone()

        push_enabled = prefs['push_enabled'] if prefs else 1
        email_enabled = prefs['email_enabled'] if prefs else 1
        quiet_start = prefs['quiet_start'] if prefs else '22:00'
        quiet_end = prefs['quiet_end'] if prefs else '08:00'

        # Check quiet hours (simple UTC check)
        from datetime import datetime
        now_hm = datetime.utcnow().strftime('%H:%M')
        in_quiet = False
        if quiet_start and quiet_end:
            if quiet_start > quiet_end:  # e.g. 22:00 - 08:00 (overnight)
                in_quiet = now_hm >= quiet_start or now_hm < quiet_end
            else:
                in_quiet = quiet_start <= now_hm < quiet_end

        if in_quiet:
            conn.close()
            return

        island_url = f"https://genclawverse.ai/island/{island_id}" if island_id else "https://genclawverse.ai"

        # Try web push first
        push_sent = False
        if push_enabled:
            push_sent = send_push(owner_id, title, body, island_url, event_type, db_conn_func)

        # Email fallback: if push not sent AND email enabled AND user inactive 4h+
        if not push_sent and email_enabled and user['email']:
            # Check last activity
            last_active = conn.execute(
                "SELECT MAX(created_at) as t FROM verification_codes WHERE email=? AND used=1",
                (user['email'],)
            ).fetchone()
            inactive_hours = 999
            if last_active and last_active['t']:
                inactive_hours = (time.time() - last_active['t']) / 3600

            # Rate limit: max 2 emails/day
            today_start = time.time() - 86400
            email_count = conn.execute(
                "SELECT COUNT(*) as c FROM notification_email_log WHERE user_id=? AND sent_at>?",
                (owner_id, today_start)
            ).fetchone()['c']

            if inactive_hours >= 4 and email_count < 2:
                ok = send_notification_email(user['email'], title, body, island_url)
                if ok:
                    conn.execute(
                        "INSERT INTO notification_email_log (user_id, event_type) VALUES (?,?)",
                        (owner_id, event_type)
                    )
                    conn.commit()

        conn.close()

    # Run in background to not block the request
    threading.Thread(target=_do_notify, daemon=True).start()
