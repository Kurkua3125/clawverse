#!/usr/bin/env python3
"""Capture clean product screenshots via CDP and build professional demo video."""
import websocket, json, base64, time, subprocess, os, urllib.request

CDP_PORT = 9223
DEMO_DIR = '/opt/clawverse/demo/pro'
BASE_URL = 'https://ysnlpjle.gensparkclaw.com'
os.makedirs(DEMO_DIR, exist_ok=True)

def get_ws_url():
    tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json').read())
    for t in tabs:
        if t.get('type') == 'page':
            return t['webSocketDebuggerUrl']
    return tabs[0]['webSocketDebuggerUrl']

def cdp_send(ws, method, params=None, msg_id=None):
    """Send CDP command and wait for matching response, draining events."""
    if msg_id is None:
        msg_id = int(time.time() * 1000) % 100000
    payload = {"id": msg_id, "method": method}
    if params:
        payload["params"] = params
    ws.send(json.dumps(payload))
    
    for _ in range(100):
        try:
            msg = json.loads(ws.recv())
            if msg.get('id') == msg_id:
                return msg
        except websocket.WebSocketTimeoutException:
            break
    return None

def capture(ws_url_unused, url, output_path, wait=7):
    """Navigate + wait + screenshot. Reconnects WS each time for stability."""
    try:
        ws_url = get_ws_url()
        ws = websocket.create_connection(ws_url, timeout=15)
        
        cdp_send(ws, "Page.navigate", {"url": url}, 1)
        time.sleep(wait)
        
        resp = cdp_send(ws, "Page.captureScreenshot", {"format": "jpeg", "quality": 95}, 2)
        if resp and 'result' in resp and 'data' in resp['result']:
            img = base64.b64decode(resp['result']['data'])
            with open(output_path, 'wb') as f:
                f.write(img)
            print(f"  ✅ {os.path.basename(output_path)} ({len(img)//1024}KB)")
            ws.close()
            return True
        ws.close()
    except Exception as e:
        print(f"  ⚠ Error: {e}")
    print(f"  ❌ {os.path.basename(output_path)}")
    return False

def img_to_clip(img, out, dur=4, label=None, sublabel=None):
    """Image → video clip with Ken Burns zoom + label overlay."""
    vf = [
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
        f"zoompan=z='min(zoom+0.00025,1.025)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={dur*30}:s=1920x1080:fps=30"
    ]
    if label:
        vf.append(f"drawbox=x=0:y=ih-80:w=iw:h=80:color=black@0.5:t=fill")
        vf.append(f"drawtext=text='{label}':fontcolor=white:fontsize=32:x=40:y=h-62:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    if sublabel:
        vf.append(f"drawtext=text='{sublabel}':fontcolor=0xaaaaaa:fontsize=18:x=40:y=h-28:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    vf.append(f"fade=in:0:15,fade=out:st={dur-0.7}:d=0.7")
    
    subprocess.run([
        'ffmpeg', '-y', '-loop', '1', '-i', img,
        '-vf', ','.join(vf),
        '-t', str(dur),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        out
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def make_card(text, sub, dur, out, bg='0x0a0e27'):
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c={bg}:s=1920x1080:d={dur}',
        '-vf', (
            f"drawtext=text='{text}':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2-50:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            f"drawtext=text='{sub}':fontcolor=0x888888:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
            f"fade=in:0:20,fade=out:st={dur-0.7}:d=0.7"
        ),
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', out
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    print("🎬 Professional Clawverse Demo — CDP Screenshot Method\n")
    
    scenes = [
        ('lobby',     f'{BASE_URL}',                                  5, 'Island Directory',       '36 unique islands to explore'),
        ('neon',      f'{BASE_URL}/island/demo_neon_paradise',        4, 'Neon Paradise',          '246 items | Casino & Entertainment'),
        ('genspark',  f'{BASE_URL}/island/ac4163459b8f',              4, 'Genspark',               '3,194 items | Lv.29 Mega-Build'),
        ('golden',    f'{BASE_URL}/island/demo_golden_empire',        4, 'Golden Empire',          '220 items | Pure Gold'),
        ('enchanted', f'{BASE_URL}/island/demo_enchanted_kingdom',    4, 'Enchanted Kingdom',      '193 items | Fantasy Forest'),
        ('cherry',    f'{BASE_URL}/island/ecddd6186a6c',              4, 'Cherry Blossom Garden',  'Japanese Zen Garden'),
        ('space',     f'{BASE_URL}/island/78820b5f58a4',              4, 'Space Station Claw',     'Sci-Fi Outpost'),
        ('castle',    f'{BASE_URL}/island/96bd33c64af9',              4, 'Castle Fortress',        'Medieval Stronghold'),
        ('tropical',  f'{BASE_URL}/island/demo_tropical_resort',      4, 'Tropical Resort',        'Beach Paradise'),
        ('claw',      f'{BASE_URL}/island/default',                   4, 'Claw Island',            'Where It All Began'),
    ]
    
    # 1. Capture screenshots (reconnects WS each time)
    print("=== Step 1: Capturing screenshots ===")
    for name, url, *_ in scenes:
        capture(None, url, os.path.join(DEMO_DIR, f'ss_{name}.jpg'), wait=7)
    
    # 2. Build clips
    print("\n=== Step 2: Building video clips ===")
    for name, _, dur, label, sub in scenes:
        img = os.path.join(DEMO_DIR, f'ss_{name}.jpg')
        clip = os.path.join(DEMO_DIR, f'clip_{name}.mp4')
        if os.path.exists(img) and os.path.getsize(img) > 10000:
            img_to_clip(img, clip, dur, label, sub)
            print(f"  ✅ clip_{name}.mp4")
        else:
            print(f"  ❌ Skipped {name} (no screenshot)")
    
    # 3. Cards
    print("\n=== Step 3: Title & end cards ===")
    make_card('Clawverse', 'Build Your Pixel Island. Visit Friends. Collect Everything.', 3, os.path.join(DEMO_DIR, 'title.mp4'))
    make_card('clawverse.com', 'Open Source - Coming Soon', 3, os.path.join(DEMO_DIR, 'endcard.mp4'))
    print("  ✅ Cards done")
    
    # 4. Assemble
    print("\n=== Step 4: Final assembly ===")
    concat = os.path.join(DEMO_DIR, 'concat.txt')
    with open(concat, 'w') as f:
        f.write("file 'title.mp4'\n")
        for name, *_ in scenes:
            clip = f'clip_{name}.mp4'
            if os.path.exists(os.path.join(DEMO_DIR, clip)):
                f.write(f"file '{clip}'\n")
        f.write("file 'endcard.mp4'\n")
    
    final = os.path.join(DEMO_DIR, 'clawverse_demo_pro.mp4')
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
        final
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(final) and os.path.getsize(final) > 100000:
        dur = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final]).decode().strip()
        sz = os.path.getsize(final) / (1024*1024)
        print(f"\n🎬 DONE: {final}")
        print(f"   Duration: {dur}s | Size: {sz:.1f}MB | 1920x1080")
    else:
        print("\n❌ Final video failed")

if __name__ == '__main__':
    main()
