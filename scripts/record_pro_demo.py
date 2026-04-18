#!/usr/bin/env python3
"""
Professional demo video recorder for Clawverse.
Uses CDP to navigate Chrome in kiosk mode, records via ffmpeg.
Output: individual scene clips ready for ffmpeg post-processing.
"""
import subprocess, time, json, os, sys

DEMO_DIR = '/opt/clawverse/demo/pro'
CDP_PORT = 9223
BASE_URL = 'https://ysnlpjle.gensparkclaw.com'

os.makedirs(DEMO_DIR, exist_ok=True)

def cdp_navigate(url):
    """Navigate via CDP HTTP API."""
    tabs = json.loads(subprocess.check_output(
        ['curl', '-s', f'http://127.0.0.1:{CDP_PORT}/json'], timeout=5
    ))
    target = None
    for t in tabs:
        if 'gensparkclaw' in t.get('url', '') or t.get('type') == 'page':
            target = t['id']
            break
    if not target:
        target = tabs[0]['id']
    
    # Use CDP websocket to navigate (HTTP API doesn't support PUT well)
    subprocess.run(
        ['curl', '-s', f'http://127.0.0.1:{CDP_PORT}/json/navigate/{target}?url={url}'],
        capture_output=True, timeout=5
    )

def cdp_evaluate(js):
    """Execute JS in page."""
    # Simple approach: use python websocket
    pass

def record_scene(scene_name, url, duration=5, scroll_js=None):
    """Record a single scene clip."""
    output = os.path.join(DEMO_DIR, f'{scene_name}.mp4')
    
    print(f"  🎬 Scene: {scene_name} ({duration}s)")
    
    # Navigate
    cdp_navigate(url)
    time.sleep(3)  # Wait for page load
    
    # Start recording this scene
    proc = subprocess.Popen([
        'ffmpeg', '-y',
        '-f', 'x11grab', '-video_size', '1920x1080', '-framerate', '30',
        '-i', ':99',
        '-t', str(duration),
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
        output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # If scroll animation needed
    if scroll_js:
        time.sleep(1)
        # Execute scroll via xdotool
        subprocess.run(['xdotool', 'mousemove', '960', '540'], env={**os.environ, 'DISPLAY': ':99'})
        for _ in range(8):
            subprocess.run(['xdotool', 'click', '5'], env={**os.environ, 'DISPLAY': ':99'})
            time.sleep(0.4)
        time.sleep(1)
        for _ in range(12):
            subprocess.run(['xdotool', 'click', '4'], env={**os.environ, 'DISPLAY': ':99'})
            time.sleep(0.3)
    
    proc.wait()
    
    if os.path.exists(output):
        sz = os.path.getsize(output)
        print(f"    ✅ {output} ({sz//1024}KB)")
    else:
        print(f"    ❌ Failed")

def create_title_card(text, subtitle, duration=3, filename='title'):
    """Create a title card with the game's dark theme."""
    output = os.path.join(DEMO_DIR, f'{filename}.mp4')
    
    # Dark navy background matching Clawverse theme
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', f'color=c=0x0a0e27:s=1920x1080:d={duration}',
        '-vf', (
            f"drawtext=text='{text}':"
            f"fontcolor=white:fontsize=72:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-50:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            f"drawtext=text='{subtitle}':"
            f"fontcolor=0x888888:fontsize=28:"
            f"x=(w-text_w)/2:y=(h-text_h)/2+40:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            f"fade=in:0:20,fade=out:st={duration-0.7}:d=0.7"
        ),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        output
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"  ✅ Title card: {filename}")

def add_label_overlay(input_path, label, sublabel, output_path):
    """Add a subtle label overlay to a clip."""
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-vf', (
            # Semi-transparent dark bar at bottom
            f"drawbox=x=0:y=ih-80:w=iw:h=80:color=black@0.5:t=fill,"
            # Island name
            f"drawtext=text='{label}':"
            f"fontcolor=white:fontsize=32:"
            f"x=40:y=h-65:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            # Subtitle
            f"drawtext=text='{sublabel}':"
            f"fontcolor=0xaaaaaa:fontsize=18:"
            f"x=40:y=h-30:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            # Fade in/out
            f"fade=in:0:15,fade=out:st=4.3:d=0.7"
        ),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("🎬 Recording professional Clawverse demo")
    print(f"   Output: {DEMO_DIR}")
    print()

    # ── Record all scenes ──────────────────────────────────
    scenes = [
        ('01_lobby', f'{BASE_URL}', 10, True),  # Lobby with scroll
        ('02_neon', f'{BASE_URL}/island/demo_neon_paradise', 5, False),
        ('03_genspark', f'{BASE_URL}/island/ac4163459b8f', 5, False),
        ('04_golden', f'{BASE_URL}/island/demo_golden_empire', 5, False),
        ('05_enchanted', f'{BASE_URL}/island/demo_enchanted_kingdom', 5, False),
        ('06_cherry', f'{BASE_URL}/island/ecddd6186a6c', 5, False),
        ('07_space', f'{BASE_URL}/island/78820b5f58a4', 5, False),
        ('08_castle', f'{BASE_URL}/island/96bd33c64af9', 5, False),
        ('09_tropical', f'{BASE_URL}/island/demo_tropical_resort', 5, False),
        ('10_claw', f'{BASE_URL}/island/default', 5, False),
    ]

    print("=== Recording scenes ===")
    for name, url, dur, scroll in scenes:
        record_scene(name, url, dur, 'scroll' if scroll else None)
    
    # ── Create title and end cards ─────────────────────────
    print("\n=== Creating cards ===")
    create_title_card('Clawverse', 'Build Your Pixel Island. Visit Friends. Collect Everything.', 3, 'title')
    create_title_card('clawverse.com', 'Open Source - Coming Soon', 3, 'endcard')

    # ── Add labels to each scene ──────────────────────────
    print("\n=== Adding labels ===")
    labels = {
        '01_lobby': ('Island Directory', '36 unique islands to explore'),
        '02_neon': ('Neon Paradise', '246 items | Casino & Entertainment'),
        '03_genspark': ('Genspark', '3,194 items | Lv.29 Mega-Build'),
        '04_golden': ('Golden Empire', '220 items | Pure Gold'),
        '05_enchanted': ('Enchanted Kingdom', '193 items | Fantasy Forest'),
        '06_cherry': ('Cherry Blossom Garden', 'Japanese Zen Garden'),
        '07_space': ('Space Station Claw', 'Sci-Fi Outpost'),
        '08_castle': ('Castle Fortress', 'Medieval Stronghold'),
        '09_tropical': ('Tropical Resort', 'Beach Paradise'),
        '10_claw': ('Claw Island', 'Where It All Began'),
    }
    
    for scene, (label, sublabel) in labels.items():
        inp = os.path.join(DEMO_DIR, f'{scene}.mp4')
        out = os.path.join(DEMO_DIR, f'{scene}_labeled.mp4')
        if os.path.exists(inp):
            add_label_overlay(inp, label, sublabel, out)
            print(f"  ✅ {scene}_labeled.mp4")

    # ── Assemble final video ──────────────────────────────
    print("\n=== Assembling final video ===")
    
    concat_list = os.path.join(DEMO_DIR, 'concat.txt')
    parts = ['title.mp4']
    for scene in ['01_lobby', '02_neon', '03_genspark', '04_golden', '05_enchanted',
                   '06_cherry', '07_space', '08_castle', '09_tropical', '10_claw']:
        labeled = f'{scene}_labeled.mp4'
        raw = f'{scene}.mp4'
        if os.path.exists(os.path.join(DEMO_DIR, labeled)):
            parts.append(labeled)
        elif os.path.exists(os.path.join(DEMO_DIR, raw)):
            parts.append(raw)
    parts.append('endcard.mp4')
    
    with open(concat_list, 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    
    final_output = os.path.join(DEMO_DIR, 'clawverse_demo_pro.mp4')
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        final_output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(final_output):
        sz = os.path.getsize(final_output) / (1024*1024)
        dur = subprocess.check_output([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0',
            final_output
        ]).decode().strip()
        print(f"\n🎬 DONE: {final_output}")
        print(f"   Duration: {dur}s | Size: {sz:.1f}MB | Resolution: 1920x1080")
    else:
        print("\n❌ Failed to create final video")

if __name__ == '__main__':
    main()
