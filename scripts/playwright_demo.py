#!/usr/bin/env python3
"""
Record Clawverse gameplay demo using Playwright.
Playwright renders pages headlessly — zero browser chrome.
Records video at exact 1920x1080 with real interactions.
"""
from playwright.sync_api import sync_playwright
import time, os, subprocess, json

DEMO_DIR = '/opt/clawverse/demo/gameplay'
BASE = 'http://127.0.0.1:19003'
os.makedirs(DEMO_DIR, exist_ok=True)

def record_scene(browser, name, actions_fn, width=1920, height=1080):
    """Record a single gameplay scene."""
    context = browser.new_context(
        viewport={"width": width, "height": height},
        record_video_dir=DEMO_DIR,
        record_video_size={"width": width, "height": height},
    )
    page = context.new_page()
    
    try:
        actions_fn(page)
    except Exception as e:
        print(f"    ⚠ Error during {name}: {e}")
    
    video_path = page.video.path()
    context.close()
    
    # Rename video file
    final_path = os.path.join(DEMO_DIR, f'{name}.webm')
    if os.path.exists(video_path):
        os.rename(video_path, final_path)
        print(f"  ✅ {name} recorded")
        return final_path
    return None

def login(page):
    """Log in as Eric J."""
    # Generate verification code
    code = subprocess.check_output([
        'python3', '-c',
        "import sys,os; sys.path.insert(0,'/opt/clawverse/backend'); import auth; e=os.environ.get('ADMIN_EMAIL','admin@genclawverse.ai'); c=auth.generate_code(); auth.store_verification_code(e,c); print(c)"
    ]).decode().strip()
    
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(2000)
    
    # Login via API
    page.evaluate(f"""
        fetch('/api/auth/verify-code', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{email: '{os.environ.get("ADMIN_EMAIL","admin@genclawverse.ai")}', code: '{code}'}})
        }})
    """)
    page.wait_for_timeout(1000)
    page.reload()
    page.wait_for_timeout(3000)

def scene_lobby_browse(page):
    """Browse the lobby — scroll through islands."""
    page.goto(f'{BASE}')
    page.wait_for_timeout(3000)
    
    # Slow scroll down
    for _ in range(6):
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(400)
    
    page.wait_for_timeout(500)
    
    # Scroll back up
    for _ in range(8):
        page.mouse.wheel(0, -250)
        page.wait_for_timeout(300)
    
    page.wait_for_timeout(1000)

def scene_visit_island(page):
    """Visit the Neon Paradise island."""
    page.goto(f'{BASE}/island/demo_neon_paradise')
    page.wait_for_timeout(4000)
    
    # Dismiss welcome popup if visible
    try:
        page.click('text=Start Exploring', timeout=2000)
    except:
        pass
    
    page.wait_for_timeout(2000)

def scene_visit_genspark(page):
    """Visit the massive Genspark island."""
    page.goto(f'{BASE}/island/ac4163459b8f')
    page.wait_for_timeout(4000)
    try:
        page.click('text=Start Exploring', timeout=2000)
    except:
        pass
    page.wait_for_timeout(2000)

def scene_build_mode(page):
    """Enter build mode and place objects."""
    login(page)
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(3000)
    
    # Click Build button
    page.evaluate("""
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.includes('Build') && b.offsetParent !== null) {
                b.click(); break;
            }
        }
    """)
    page.wait_for_timeout(1500)
    
    # Look for the build palette/panel and click something
    page.evaluate("""
        // Try to open object palette
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            const t = b.textContent.trim();
            if (t.includes('🏠') || t.includes('Objects') || t === '🏠') {
                b.click(); break;
            }
        }
    """)
    page.wait_for_timeout(1500)
    
    # Click on an object in the palette
    page.evaluate("""
        const items = document.querySelectorAll('.palette-item, .catalog-item, [data-type]');
        if (items.length > 3) items[3].click();
    """)
    page.wait_for_timeout(1000)
    
    # Click on the canvas to place
    page.click('canvas', position={"x": 500, "y": 400})
    page.wait_for_timeout(500)
    page.click('canvas', position={"x": 600, "y": 350})
    page.wait_for_timeout(500)
    page.click('canvas', position={"x": 700, "y": 400})
    page.wait_for_timeout(1500)

def scene_farm_mode(page):
    """Enter farm mode and plant crops."""
    login(page)
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(3000)
    
    # Click Farm button in bottom toolbar
    page.evaluate("""
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.includes('Farm') && b.offsetParent !== null && b.offsetHeight > 0) {
                b.click(); break;
            }
        }
    """)
    page.wait_for_timeout(2000)
    
    # Look for plant button
    page.evaluate("""
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if ((b.textContent.includes('Plant') || b.textContent.includes('🌱')) && b.offsetParent !== null) {
                b.click(); break;
            }
        }
    """)
    page.wait_for_timeout(1500)
    
    # Select carrot
    page.evaluate("""
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.includes('Carrot') || b.textContent.includes('🥕')) {
                b.click(); break;
            }
        }
    """)
    page.wait_for_timeout(1000)
    
    # Click on farm area to plant
    page.click('canvas', position={"x": 500, "y": 500})
    page.wait_for_timeout(500)
    page.click('canvas', position={"x": 550, "y": 520})
    page.wait_for_timeout(500)
    page.click('canvas', position={"x": 600, "y": 540})
    page.wait_for_timeout(1500)

def scene_spin(page):
    """Do the daily spin."""
    login(page)
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(3000)
    
    # Click spin button
    page.evaluate("""
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.includes('🎰') || b.textContent.includes('SPIN')) {
                b.click(); break;
            }
        }
    """)
    page.wait_for_timeout(3000)

def scene_shop(page):
    """Open the shop."""
    login(page)
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(3000)
    
    # Click Shop button
    page.evaluate("""
        const btns = document.querySelectorAll('button');
        for (const b of btns) {
            if (b.textContent.includes('Shop') || b.textContent.includes('🏪')) {
                b.click(); break;
            }
        }
    """)
    page.wait_for_timeout(2000)
    
    # Browse shop items
    page.evaluate("""
        const panel = document.querySelector('.shop-panel, #shop-panel, [class*=shop]');
        if (panel) panel.scrollTop += 200;
    """)
    page.wait_for_timeout(2000)

def scene_enchanted(page):
    """Visit Enchanted Kingdom."""
    page.goto(f'{BASE}/island/demo_enchanted_kingdom')
    page.wait_for_timeout(4000)
    try:
        page.click('text=Start Exploring', timeout=2000)
    except:
        pass
    page.wait_for_timeout(2000)

def scene_space(page):
    """Visit Space Station."""
    page.goto(f'{BASE}/island/78820b5f58a4')
    page.wait_for_timeout(4000)
    try:
        page.click('text=Start Exploring', timeout=2000)
    except:
        pass
    page.wait_for_timeout(2000)

def main():
    print("🎬 Recording Clawverse Gameplay Demo with Playwright\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        scenes = [
            ('01_lobby', scene_lobby_browse),
            ('02_neon', scene_visit_island),
            ('03_genspark', scene_visit_genspark),
            ('04_build', scene_build_mode),
            ('05_farm', scene_farm_mode),
            ('06_spin', scene_spin),
            ('07_shop', scene_shop),
            ('08_enchanted', scene_enchanted),
            ('09_space', scene_space),
        ]
        
        for name, fn in scenes:
            print(f"  🎬 Recording: {name}")
            record_scene(browser, name, fn)
        
        browser.close()
    
    # Convert webm to mp4 and add labels
    print("\n=== Post-production ===")
    
    labels = {
        '01_lobby': ('Island Directory', '36 islands to explore'),
        '02_neon': ('Neon Paradise', '246 items'),
        '03_genspark': ('Genspark', '3,194 items — Lv.29'),
        '04_build': ('Build Mode', 'Place objects on your island'),
        '05_farm': ('Farm', 'Plant & harvest crops'),
        '06_spin': ('Daily Spin', 'Win coins & rewards'),
        '07_shop': ('Shop', 'Buy items & upgrades'),
        '08_enchanted': ('Enchanted Kingdom', '193 items'),
        '09_space': ('Space Station', 'Sci-fi outpost'),
    }
    
    for name, (label, sub) in labels.items():
        webm = os.path.join(DEMO_DIR, f'{name}.webm')
        mp4 = os.path.join(DEMO_DIR, f'{name}.mp4')
        
        if not os.path.exists(webm):
            print(f"  ❌ {name}.webm missing")
            continue
        
        # Convert + add label + trim to max 6s
        subprocess.run([
            'ffmpeg', '-y', '-i', webm,
            '-t', '6',
            '-vf', (
                f"drawbox=x=0:y=ih-75:w=iw:h=75:color=black@0.5:t=fill,"
                f"drawtext=text='{label}':fontcolor=white:fontsize=30:x=35:y=h-58:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
                f"drawtext=text='{sub}':fontcolor=0xaaaaaa:fontsize=17:x=35:y=h-25:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
                f"fade=in:0:15,fade=out:st=5.3:d=0.7"
            ),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
            mp4
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(mp4) and os.path.getsize(mp4) > 10000:
            dur = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4]).decode().strip()
            print(f"  ✅ {name}.mp4 ({dur}s)")
        else:
            print(f"  ❌ {name}.mp4 failed")
    
    # Title + end cards
    for card_name, text, sub, color in [
        ('title', 'CLAWVERSE', 'Build. Visit. Collect.', '0x44ddff'),
        ('endcard', 'clawverse.com', 'Open Source — Coming Soon', '0x44ff88'),
    ]:
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=0x0a0e27:s=1920x1080:d=2.5',
            '-vf', (
                f"drawtext=text='{text}':fontcolor=white:fontsize=88:x=(w-text_w)/2:y=(h-text_h)/2-40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
                f"drawtext=text='{sub}':fontcolor={color}:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
                f"fade=in:0:20,fade=out:st=2:d=0.5"
            ),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
            os.path.join(DEMO_DIR, f'{card_name}.mp4')
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("  ✅ Cards done")
    
    # Final assembly
    print("\n=== Final Assembly ===")
    concat = os.path.join(DEMO_DIR, 'concat.txt')
    with open(concat, 'w') as f:
        f.write("file 'title.mp4'\n")
        for name in ['01_lobby', '02_neon', '03_genspark', '04_build', '05_farm', 
                      '06_spin', '07_shop', '08_enchanted', '09_space']:
            mp4 = f'{name}.mp4'
            if os.path.exists(os.path.join(DEMO_DIR, mp4)):
                f.write(f"file '{mp4}'\n")
        f.write("file 'endcard.mp4'\n")
    
    final = os.path.join(DEMO_DIR, 'clawverse_gameplay_demo.mp4')
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', final
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(final) and os.path.getsize(final) > 500000:
        dur = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final]).decode().strip()
        sz = os.path.getsize(final) / (1024*1024)
        print(f"\n🎬 DONE: {final}")
        print(f"   Duration: {dur}s | Size: {sz:.1f}MB | 1920x1080")
    else:
        print("\n❌ Final assembly failed")

if __name__ == '__main__':
    main()
