#!/usr/bin/env python3
"""
Record a LIVE demo of Clawverse with real browser interaction.
Chrome is in kiosk/app mode — no browser chrome visible.
Uses xdotool for mouse movements and scrolling.
Records each scene as a separate clip for post-production.
"""
import subprocess, time, json, os, urllib.request

CDP_PORT = 9223
DEMO_DIR = '/opt/clawverse/demo/live'
BASE_URL = 'https://ysnlpjle.gensparkclaw.com'
os.makedirs(DEMO_DIR, exist_ok=True)

ENV = {**os.environ, 'DISPLAY': ':99'}

def xdo(*args):
    subprocess.run(['xdotool'] + list(args), env=ENV, capture_output=True)

def navigate(url):
    """Navigate via CDP."""
    try:
        tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json').read())
        for t in tabs:
            if t.get('type') == 'page':
                import websocket
                ws = websocket.create_connection(t['webSocketDebuggerUrl'], timeout=10)
                ws.send(json.dumps({"id":1,"method":"Page.navigate","params":{"url":url}}))
                for _ in range(20):
                    msg = json.loads(ws.recv())
                    if msg.get('id') == 1:
                        break
                ws.close()
                return True
    except Exception as e:
        print(f"    Nav error: {e}")
    return False

def record_clip(name, duration):
    """Start recording a clip, return the ffmpeg process."""
    output = os.path.join(DEMO_DIR, f'{name}.mp4')
    proc = subprocess.Popen([
        'ffmpeg', '-y',
        '-f', 'x11grab', '-video_size', '1920x1080', '-framerate', '30',
        '-i', ':99',
        '-t', str(duration),
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
        output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=ENV)
    return proc

def smooth_scroll_down(steps=8, delay=0.3):
    """Smooth scroll down with mouse wheel."""
    xdo('mousemove', '960', '540')
    time.sleep(0.2)
    for _ in range(steps):
        xdo('click', '5')  # scroll down
        time.sleep(delay)

def smooth_scroll_up(steps=10, delay=0.25):
    """Smooth scroll up."""
    for _ in range(steps):
        xdo('click', '4')  # scroll up
        time.sleep(delay)

def mouse_move_smooth(x1, y1, x2, y2, steps=20, delay=0.02):
    """Smooth mouse movement."""
    for i in range(steps + 1):
        t = i / steps
        x = int(x1 + (x2 - x1) * t)
        y = int(y1 + (y2 - y1) * t)
        xdo('mousemove', str(x), str(y))
        time.sleep(delay)

def main():
    print("🎬 Recording LIVE Clawverse Demo\n")
    
    # Hide mouse cursor to a corner first
    xdo('mousemove', '960', '540')
    
    # ── Scene 1: Lobby — scroll through islands (8s) ──
    print("  🎬 Scene 1: Lobby")
    navigate(BASE_URL)
    time.sleep(5)  # Wait for full load
    
    proc = record_clip('01_lobby', 10)
    time.sleep(1)
    smooth_scroll_down(10, 0.35)
    time.sleep(0.5)
    smooth_scroll_up(12, 0.25)
    time.sleep(0.5)
    proc.wait()
    print("    ✅ lobby (10s)")
    
    # ── Scene 2: Neon Paradise (6s) ──
    print("  🎬 Scene 2: Neon Paradise")
    navigate(f'{BASE_URL}/island/demo_neon_paradise')
    time.sleep(5)
    
    proc = record_clip('02_neon', 6)
    time.sleep(1)
    # Slight pan movement (drag canvas)
    mouse_move_smooth(700, 400, 500, 300, 30, 0.05)
    time.sleep(2)
    proc.wait()
    print("    ✅ neon (6s)")
    
    # ── Scene 3: Genspark — the mega build (6s) ──
    print("  🎬 Scene 3: Genspark")
    navigate(f'{BASE_URL}/island/ac4163459b8f')
    time.sleep(5)
    
    proc = record_clip('03_genspark', 6)
    time.sleep(1)
    mouse_move_smooth(600, 500, 400, 350, 30, 0.05)
    time.sleep(2)
    proc.wait()
    print("    ✅ genspark (6s)")
    
    # ── Scene 4: Golden Empire (5s) ──
    print("  🎬 Scene 4: Golden Empire")
    navigate(f'{BASE_URL}/island/demo_golden_empire')
    time.sleep(5)
    
    proc = record_clip('04_golden', 5)
    time.sleep(4)
    proc.wait()
    print("    ✅ golden (5s)")
    
    # ── Scene 5: Enchanted Kingdom (5s) ──
    print("  🎬 Scene 5: Enchanted Kingdom")
    navigate(f'{BASE_URL}/island/demo_enchanted_kingdom')
    time.sleep(5)
    
    proc = record_clip('05_enchanted', 5)
    time.sleep(4)
    proc.wait()
    print("    ✅ enchanted (5s)")
    
    # ── Scene 6: Cherry Blossom (5s) ──
    print("  🎬 Scene 6: Cherry Blossom")
    navigate(f'{BASE_URL}/island/ecddd6186a6c')
    time.sleep(5)
    
    proc = record_clip('06_cherry', 5)
    time.sleep(4)
    proc.wait()
    print("    ✅ cherry (5s)")
    
    # ── Scene 7: Space Station (5s) ──
    print("  🎬 Scene 7: Space Station")
    navigate(f'{BASE_URL}/island/78820b5f58a4')
    time.sleep(5)
    
    proc = record_clip('07_space', 5)
    time.sleep(4)
    proc.wait()
    print("    ✅ space (5s)")
    
    # ── Scene 8: Castle Fortress (5s) ──
    print("  🎬 Scene 8: Castle Fortress")
    navigate(f'{BASE_URL}/island/96bd33c64af9')
    time.sleep(5)
    
    proc = record_clip('08_castle', 5)
    time.sleep(4)
    proc.wait()
    print("    ✅ castle (5s)")
    
    # ── Scene 9: Claw Island (5s) ──
    print("  🎬 Scene 9: Claw Island")
    navigate(f'{BASE_URL}/island/default')
    time.sleep(5)
    
    proc = record_clip('09_claw', 5)
    time.sleep(4)
    proc.wait()
    print("    ✅ claw (5s)")
    
    # ── Scene 10: Back to Lobby (4s) ──
    print("  🎬 Scene 10: Return to Lobby")
    navigate(BASE_URL)
    time.sleep(4)
    
    proc = record_clip('10_end', 4)
    time.sleep(3)
    proc.wait()
    print("    ✅ end (4s)")
    
    print("\n  All scenes recorded!")
    
    # ── Post-production: add labels and assemble ──
    print("\n=== Post-production ===")
    
    labels = {
        '01_lobby': ('Island Directory', '36 islands to explore'),
        '02_neon': ('Neon Paradise', '246 items'),
        '03_genspark': ('Genspark', '3,194 items — Lv.29'),
        '04_golden': ('Golden Empire', '220 items'),
        '05_enchanted': ('Enchanted Kingdom', '193 items'),
        '06_cherry': ('Cherry Blossom Garden', 'Japanese zen'),
        '07_space': ('Space Station Claw', 'Sci-fi outpost'),
        '08_castle': ('Castle Fortress', 'Medieval realm'),
        '09_claw': ('Claw Island', 'Where it began'),
        '10_end': (None, None),  # No label for end
    }
    
    for scene, (label, sub) in labels.items():
        inp = os.path.join(DEMO_DIR, f'{scene}.mp4')
        out = os.path.join(DEMO_DIR, f'{scene}_labeled.mp4')
        
        if not os.path.exists(inp) or os.path.getsize(inp) < 10000:
            print(f"  ❌ {scene} missing or empty")
            continue
        
        if label:
            vf = (
                f"drawbox=x=0:y=ih-75:w=iw:h=75:color=black@0.5:t=fill,"
                f"drawtext=text='{label}':fontcolor=white:fontsize=30:x=35:y=h-58:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
                f"drawtext=text='{sub}':fontcolor=0xaaaaaa:fontsize=17:x=35:y=h-25:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
                f"fade=in:0:15,fade=out:st={4}:d=0.7"
            )
        else:
            vf = f"fade=in:0:15,fade=out:st=3:d=0.7"
        
        subprocess.run([
            'ffmpeg', '-y', '-i', inp, '-vf', vf,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', out
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  ✅ {scene}_labeled.mp4")
    
    # Title card
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=0x0a0e27:s=1920x1080:d=2.5',
        '-vf', (
            "drawtext=text='CLAWVERSE':fontcolor=white:fontsize=88:"
            "x=(w-text_w)/2:y=(h-text_h)/2-50:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            "drawtext=text='Build. Visit. Collect.':fontcolor=0x44ddff:fontsize=32:"
            "x=(w-text_w)/2:y=(h-text_h)/2+40:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            "fade=in:0:20,fade=out:st=2:d=0.5"
        ),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        os.path.join(DEMO_DIR, 'title.mp4')
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # End card
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=0x0a0e27:s=1920x1080:d=2.5',
        '-vf', (
            "drawtext=text='clawverse.com':fontcolor=white:fontsize=64:"
            "x=(w-text_w)/2:y=(h-text_h)/2-30:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            "drawtext=text='Open Source — Coming Soon':fontcolor=0x44ff88:fontsize=28:"
            "x=(w-text_w)/2:y=(h-text_h)/2+30:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            "fade=in:0:20,fade=out:st=2:d=0.5"
        ),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        os.path.join(DEMO_DIR, 'endcard.mp4')
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("  ✅ Cards done")
    
    # Assemble
    print("\n=== Final Assembly ===")
    concat = os.path.join(DEMO_DIR, 'concat.txt')
    with open(concat, 'w') as f:
        f.write("file 'title.mp4'\n")
        for scene in ['01_lobby', '02_neon', '03_genspark', '04_golden', '05_enchanted',
                       '06_cherry', '07_space', '08_castle', '09_claw', '10_end']:
            labeled = f'{scene}_labeled.mp4'
            raw = f'{scene}.mp4'
            if os.path.exists(os.path.join(DEMO_DIR, labeled)):
                f.write(f"file '{labeled}'\n")
            elif os.path.exists(os.path.join(DEMO_DIR, raw)):
                f.write(f"file '{raw}'\n")
        f.write("file 'endcard.mp4'\n")
    
    final = os.path.join(DEMO_DIR, 'clawverse_demo_live.mp4')
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', final
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(final) and os.path.getsize(final) > 500000:
        dur = subprocess.check_output([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final
        ]).decode().strip()
        sz = os.path.getsize(final) / (1024*1024)
        print(f"\n🎬 DONE: {final}")
        print(f"   Duration: {dur}s | Size: {sz:.1f}MB | 1920x1080")
    else:
        print(f"\n❌ Final assembly failed")

if __name__ == '__main__':
    main()
