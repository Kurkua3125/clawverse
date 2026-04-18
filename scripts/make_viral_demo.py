#!/usr/bin/env python3
"""
Make a VIRAL Clawverse demo video.
Strategy: Screenshots of LOADED pages → Ken Burns animation → fast snap cuts → music
No loading screens. No black frames. Every second is beautiful content.
"""
from playwright.sync_api import sync_playwright
import subprocess, os, time, json

DEMO_DIR = '/opt/clawverse/demo/viral'
BASE = 'http://127.0.0.1:19003'
os.makedirs(DEMO_DIR, exist_ok=True)

def take_screenshot(page, url, name, wait=8, dismiss_popup=True):
    """Navigate, wait for FULL load, dismiss popups, then screenshot."""
    print(f"  📸 {name}...")
    page.goto(url, wait_until='load', timeout=60000)
    page.wait_for_timeout(wait * 1000)
    
    if dismiss_popup:
        # Dismiss any popups/overlays
        try:
            page.evaluate("""
                document.querySelectorAll('[id*=overlay],[id*=popup],[id*=welcome],[id*=onboarding]').forEach(el => {
                    if (el.style.display !== 'none') el.style.display = 'none';
                });
                document.querySelectorAll('button').forEach(b => {
                    if (b.textContent.includes('Start Exploring') || b.textContent.includes('Close') || b.textContent.includes('✕')) {
                        try { b.click(); } catch(e) {}
                    }
                });
            """)
            page.wait_for_timeout(1000)
        except:
            pass
    
    path = os.path.join(DEMO_DIR, f'{name}.jpg')
    page.screenshot(path=path, type='jpeg', quality=95)
    sz = os.path.getsize(path) // 1024
    print(f"    ✅ {sz}KB")
    return path

def img_to_clip(img, out, dur=3, direction='in'):
    """Image → video with Ken Burns effect. direction: 'in' (zoom in) or 'out' (zoom out)."""
    if direction == 'in':
        # Zoom in (push closer)
        zoom = f"z='min(zoom+0.0004,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    elif direction == 'out':
        # Zoom out (pull back)
        zoom = f"z='if(eq(on,1),1.04,max(zoom-0.0004,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    elif direction == 'left':
        # Pan left
        zoom = f"z=1.03:x='iw*0.03*(1-on/({dur}*30))':y='ih/2-(ih/zoom/2)'"
    else:
        # Pan right
        zoom = f"z=1.03:x='iw*0.03*on/({dur}*30)':y='ih/2-(ih/zoom/2)'"
    
    subprocess.run([
        'ffmpeg', '-y', '-loop', '1', '-i', img,
        '-vf', (
            f"scale=2048:1152,crop=1920:1080,"
            f"zoompan={zoom}:d={dur*30}:s=1920x1080:fps=30"
        ),
        '-t', str(dur),
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
        out
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("🎬 Making VIRAL Clawverse Demo\n")
    
    # ── Step 1: Take beautiful screenshots ──
    print("=== Step 1: Capturing loaded pages ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()
        
        # Login first
        page.goto(f'{BASE}/island/default', wait_until='load', timeout=60000)
        page.wait_for_timeout(3000)
        code = subprocess.check_output([
            'python3', '-c',
            "import sys,os;sys.path.insert(0,'/opt/clawverse/backend');import auth;e=os.environ.get('ADMIN_EMAIL','admin@genclawverse.ai');c=auth.generate_code();auth.store_verification_code(e,c);print(c)"
        ]).decode().strip()
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@genclawverse.ai')
        page.evaluate(f"fetch('{BASE}/api/auth/verify-code',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:'{admin_email}',code:'{code}'}})}})")
        page.wait_for_timeout(1500)
        
        screenshots = [
            # Start with the MOST SPECTACULAR islands (hook first!)
            ('01_neon', f'{BASE}/island/demo_neon_paradise', 10),
            ('02_genspark', f'{BASE}/island/ac4163459b8f', 10),
            ('03_golden', f'{BASE}/island/demo_golden_empire', 10),
            ('04_enchanted', f'{BASE}/island/demo_enchanted_kingdom', 10),
            ('05_cherry', f'{BASE}/island/ecddd6186a6c', 10),
            ('06_castle', f'{BASE}/island/96bd33c64af9', 8),
            ('07_space', f'{BASE}/island/78820b5f58a4', 8),
            ('08_tropical', f'{BASE}/island/demo_tropical_resort', 8),
            ('09_luck', f'{BASE}/island/60dd3f3795ee', 8),
            ('10_claw', f'{BASE}/island/default', 8),
            # Lobby last (or use for context)
            ('11_lobby', f'{BASE}', 6),
            # Build mode
            ('12_build', f'{BASE}/island/default', 8),
        ]
        
        for name, url, wait in screenshots:
            take_screenshot(page, url, name, wait)
        
        # Special: take build mode screenshot
        page.goto(f'{BASE}/island/default', wait_until='load', timeout=60000)
        page.wait_for_timeout(5000)
        # Enter build mode
        page.evaluate("""
            document.querySelectorAll('button').forEach(b => {
                if(b.textContent.includes('Build') && b.offsetHeight>0) b.click();
            });
        """)
        page.wait_for_timeout(2000)
        # Open palette
        page.evaluate("""
            document.querySelectorAll('button').forEach(b => {
                if((b.textContent.includes('🏠') || b.textContent.includes('Objects')) && b.offsetHeight>0) b.click();
            });
        """)
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(DEMO_DIR, '12_build.jpg'), type='jpeg', quality=95)
        print("  ✅ build mode captured")
        
        # Farm mode
        page.goto(f'{BASE}/island/default', wait_until='load', timeout=60000)
        page.wait_for_timeout(5000)
        page.evaluate("""
            document.querySelectorAll('button').forEach(b => {
                if(b.textContent.includes('Farm') && b.offsetHeight>0) b.click();
            });
        """)
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(DEMO_DIR, '13_farm.jpg'), type='jpeg', quality=95)
        print("  ✅ farm mode captured")
        
        ctx.close()
        browser.close()
    
    # ── Step 2: Build video clips with alternating Ken Burns ──
    print("\n=== Step 2: Building clips ===")
    
    scenes = [
        # Start with WOW — no intro title, jump straight into content
        ('01_neon', 2.5, 'in'),
        ('02_genspark', 2.5, 'out'),
        ('03_golden', 2.5, 'left'),
        ('04_enchanted', 2.5, 'right'),
        ('12_build', 2, 'in'),      # Build mode
        ('13_farm', 2, 'out'),       # Farm mode
        ('05_cherry', 2, 'left'),
        ('06_castle', 2, 'right'),
        ('07_space', 2, 'in'),
        ('08_tropical', 2, 'out'),
        ('09_luck', 2, 'left'),
        ('10_claw', 2.5, 'in'),
        ('11_lobby', 2, 'out'),
    ]
    
    clips = []
    for name, dur, direction in scenes:
        img = os.path.join(DEMO_DIR, f'{name}.jpg')
        clip = os.path.join(DEMO_DIR, f'{name}_clip.mp4')
        if os.path.exists(img) and os.path.getsize(img) > 10000:
            img_to_clip(img, clip, dur, direction)
            if os.path.exists(clip) and os.path.getsize(clip) > 10000:
                clips.append(clip)
                print(f"  ✅ {name} ({dur}s)")
            else:
                print(f"  ❌ {name} clip failed")
        else:
            print(f"  ❌ {name} screenshot missing")
    
    # End card (short, punchy)
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=0x0a0e27:s=1920x1080:d=2',
        '-vf', (
            "drawtext=text='clawverse.com':fontcolor=white:fontsize=72:"
            "x=(w-text_w)/2:y=(h-text_h)/2-30:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            "drawtext=text='Build your island now':fontcolor=0x44ff88:fontsize=28:"
            "x=(w-text_w)/2:y=(h-text_h)/2+30:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            "fade=in:0:15"
        ),
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
        os.path.join(DEMO_DIR, 'endcard.mp4')
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    clips.append(os.path.join(DEMO_DIR, 'endcard.mp4'))
    print("  ✅ endcard")
    
    # ── Step 3: Assemble ──
    print("\n=== Step 3: Assembly ===")
    concat = os.path.join(DEMO_DIR, 'concat.txt')
    with open(concat, 'w') as f:
        for c in clips:
            f.write(f"file '{os.path.basename(c)}'\n")
    
    final_silent = os.path.join(DEMO_DIR, 'demo_silent.mp4')
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        final_silent
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(final_silent):
        dur = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final_silent]).decode().strip()
        sz = os.path.getsize(final_silent) / (1024*1024)
        print(f"\n🎬 Silent version: {dur}s, {sz:.1f}MB")
    
    # ── Step 4: Generate background music ──
    print("\n=== Step 4: Background music ===")
    try:
        music_path = os.path.join(DEMO_DIR, 'bgm.mp3')
        result = subprocess.run([
            'gsk', 'audio', 
            'An upbeat, energetic chiptune/pixel-art style background music for a game trailer. Fast tempo, happy, adventurous, 8-bit inspired but modern. 30 seconds.',
            '-m', 'udio/v2.5',
            '-d', '30',
            '-o', music_path
        ], capture_output=True, text=True, timeout=120)
        if os.path.exists(music_path) and os.path.getsize(music_path) > 10000:
            print(f"  ✅ BGM generated: {os.path.getsize(music_path)//1024}KB")
            
            # Mix audio with video
            final = os.path.join(DEMO_DIR, 'clawverse_viral_demo.mp4')
            subprocess.run([
                'ffmpeg', '-y',
                '-i', final_silent,
                '-i', music_path,
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '128k',
                '-shortest',
                '-map', '0:v', '-map', '1:a',
                final
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(final):
                dur = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final]).decode().strip()
                sz = os.path.getsize(final) / (1024*1024)
                print(f"\n🎬 FINAL (with music): {final}")
                print(f"   Duration: {dur}s | Size: {sz:.1f}MB")
            else:
                print("  ⚠ Music mixing failed, using silent version")
        else:
            print("  ⚠ BGM generation failed, using silent version")
    except Exception as e:
        print(f"  ⚠ Music error: {e}, using silent version")
    
    # Also output the silent version path
    print(f"\n🎬 Silent version: {final_silent}")
    print("Done!")

if __name__ == '__main__':
    main()
