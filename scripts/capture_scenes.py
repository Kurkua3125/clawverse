#!/usr/bin/env python3
"""Capture high-quality screenshots of each island via CDP, then build video."""
import websocket, json, base64, time, subprocess, os

CDP_PORT = 9223
DEMO_DIR = '/opt/clawverse/demo/pro'
BASE_URL = 'https://ysnlpjle.gensparkclaw.com'
os.makedirs(DEMO_DIR, exist_ok=True)

def get_ws_url():
    import urllib.request
    tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json').read())
    for t in tabs:
        if t.get('type') == 'page':
            return t['webSocketDebuggerUrl']
    return tabs[0]['webSocketDebuggerUrl']

def capture_screenshot(ws, url, output_path, wait=6):
    """Navigate and capture screenshot via CDP."""
    # Navigate
    ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": url}}))
    ws.recv()
    time.sleep(wait)
    
    # Capture screenshot
    ws.send(json.dumps({"id": 2, "method": "Page.captureScreenshot", "params": {"format": "jpeg", "quality": 95}}))
    resp = json.loads(ws.recv())
    if 'result' in resp and 'data' in resp['result']:
        img_data = base64.b64decode(resp['result']['data'])
        with open(output_path, 'wb') as f:
            f.write(img_data)
        print(f"  ✅ {os.path.basename(output_path)} ({len(img_data)//1024}KB)")
        return True
    else:
        print(f"  ❌ Failed: {resp.get('error', 'unknown')}")
        return False

def screenshot_to_clip(img_path, output_path, duration=4, label=None, sublabel=None):
    """Convert a screenshot to a video clip with subtle Ken Burns zoom and labels."""
    # Slight zoom: start at 100%, end at 103% (subtle push-in)
    vf_parts = [
        f"zoompan=z='min(zoom+0.0003,1.03)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={duration*30}:s=1920x1080:fps=30"
    ]
    
    if label:
        # Dark bar at bottom
        vf_parts.append(f"drawbox=x=0:y=ih-80:w=iw:h=80:color=black@0.5:t=fill")
        # Label text
        vf_parts.append(
            f"drawtext=text='{label}':"
            f"fontcolor=white:fontsize=32:"
            f"x=40:y=h-62:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        )
        if sublabel:
            vf_parts.append(
                f"drawtext=text='{sublabel}':"
                f"fontcolor=0xaaaaaa:fontsize=18:"
                f"x=40:y=h-28:"
                f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            )
    
    # Fade in/out
    vf_parts.append(f"fade=in:0:15,fade=out:st={duration-0.7}:d=0.7")
    
    vf = ','.join(vf_parts)
    
    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-i', img_path,
        '-vf', vf,
        '-t', str(duration),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"  ✅ Clip: {os.path.basename(output_path)}")
    else:
        print(f"  ❌ Failed: {os.path.basename(output_path)}")

def create_card(text, subtitle, duration, filename, bg_color='0x0a0e27'):
    output = os.path.join(DEMO_DIR, filename)
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi', '-i', f'color=c={bg_color}:s=1920x1080:d={duration}',
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

def main():
    print("🎬 Capturing high-quality screenshots via CDP")
    
    ws_url = get_ws_url()
    ws = websocket.create_connection(ws_url, timeout=30)
    
    # Enable Page events
    ws.send(json.dumps({"id": 0, "method": "Page.enable"}))
    ws.recv()
    
    scenes = [
        ('lobby', f'{BASE_URL}', 8, 'Island Directory', '36 unique islands to explore'),
        ('neon', f'{BASE_URL}/island/demo_neon_paradise', 7, 'Neon Paradise', '246 items | Casino & Entertainment'),
        ('genspark', f'{BASE_URL}/island/ac4163459b8f', 7, 'Genspark', '3,194 items | Lv.29 Mega-Build'),
        ('golden', f'{BASE_URL}/island/demo_golden_empire', 7, 'Golden Empire', '220 items | Pure Gold'),
        ('enchanted', f'{BASE_URL}/island/demo_enchanted_kingdom', 7, 'Enchanted Kingdom', '193 items | Fantasy Forest'),
        ('cherry', f'{BASE_URL}/island/ecddd6186a6c', 7, 'Cherry Blossom Garden', 'Japanese Zen Garden'),
        ('space', f'{BASE_URL}/island/78820b5f58a4', 7, 'Space Station Claw', 'Sci-Fi Outpost'),
        ('castle', f'{BASE_URL}/island/96bd33c64af9', 7, 'Castle Fortress', 'Medieval Stronghold'),
        ('tropical', f'{BASE_URL}/island/demo_tropical_resort', 7, 'Tropical Resort', 'Beach Paradise'),
        ('claw', f'{BASE_URL}/island/default', 7, 'Claw Island', 'Where It All Began'),
    ]
    
    # Take screenshots
    print("\n=== Capturing screenshots ===")
    for name, url, _, _, _ in scenes:
        img_path = os.path.join(DEMO_DIR, f'ss_{name}.jpg')
        capture_screenshot(ws, url, img_path, wait=7)
    
    ws.close()
    
    # Create video clips from screenshots with Ken Burns + labels
    print("\n=== Creating video clips ===")
    for name, _, dur, label, sublabel in scenes:
        img_path = os.path.join(DEMO_DIR, f'ss_{name}.jpg')
        clip_path = os.path.join(DEMO_DIR, f'clip_{name}.mp4')
        if os.path.exists(img_path):
            screenshot_to_clip(img_path, clip_path, dur, label, sublabel)
    
    # Create title and end cards
    print("\n=== Creating cards ===")
    create_card('Clawverse', 'Build Your Pixel Island. Visit Friends. Collect Everything.', 3, 'title.mp4')
    create_card('clawverse.com', 'Open Source - Coming Soon', 3, 'endcard.mp4')
    print("  ✅ Cards created")
    
    # Assemble
    print("\n=== Assembling final video ===")
    concat_path = os.path.join(DEMO_DIR, 'concat_final.txt')
    with open(concat_path, 'w') as f:
        f.write("file 'title.mp4'\n")
        for name, *_ in scenes:
            clip = f'clip_{name}.mp4'
            if os.path.exists(os.path.join(DEMO_DIR, clip)):
                f.write(f"file '{clip}'\n")
        f.write("file 'endcard.mp4'\n")
    
    final = os.path.join(DEMO_DIR, 'clawverse_demo_pro.mp4')
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_path,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        final
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(final):
        dur = subprocess.check_output([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final
        ]).decode().strip()
        sz = os.path.getsize(final) / (1024*1024)
        print(f"\n🎬 FINAL: {final}")
        print(f"   Duration: {dur}s | Size: {sz:.1f}MB")
    
    print("\nDone!")

if __name__ == '__main__':
    main()
