#!/usr/bin/env python3
"""Record remaining gameplay scenes with Playwright."""
from playwright.sync_api import sync_playwright
import time, os, subprocess

DEMO_DIR = '/opt/clawverse/demo/gameplay'
BASE = 'http://127.0.0.1:19003'

def login(page):
    code = subprocess.check_output([
        'python3', '-c',
        "import sys,os; sys.path.insert(0,'/opt/clawverse/backend'); import auth; e=os.environ.get('ADMIN_EMAIL','admin@genclawverse.ai'); c=auth.generate_code(); auth.store_verification_code(e,c); print(c)"
    ]).decode().strip()
    page.evaluate(f"""
        fetch('/api/auth/verify-code', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{email: '{os.environ.get("ADMIN_EMAIL","admin@genclawverse.ai")}', code: '{code}'}})
        }})
    """)
    page.wait_for_timeout(1000)

def record(browser, name, fn):
    print(f"  🎬 {name}")
    ctx = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=DEMO_DIR,
        record_video_size={"width": 1920, "height": 1080},
    )
    page = ctx.new_page()
    try:
        fn(page)
    except Exception as e:
        print(f"    ⚠ {e}")
    vpath = page.video.path()
    ctx.close()
    final = os.path.join(DEMO_DIR, f'{name}.webm')
    if os.path.exists(vpath):
        os.rename(vpath, final)
        print(f"    ✅ done")

def scene_farm(page):
    login(page)
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(3000)
    # Click farm button
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Farm') && b.offsetHeight>0) b.click() })")
    page.wait_for_timeout(2000)
    # Click plant
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Plant') && b.offsetHeight>0) b.click() })")
    page.wait_for_timeout(1500)
    # Select carrot
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Carrot') && b.offsetHeight>0) b.click() })")
    page.wait_for_timeout(1000)
    # Click on farm area
    page.click('canvas', position={"x": 600, "y": 600})
    page.wait_for_timeout(500)
    page.click('canvas', position={"x": 650, "y": 620})
    page.wait_for_timeout(500)
    page.click('canvas', position={"x": 700, "y": 640})
    page.wait_for_timeout(2000)

def scene_spin(page):
    login(page)
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(3000)
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('🎰') && b.offsetHeight>0) b.click() })")
    page.wait_for_timeout(1000)
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('SPIN') && b.offsetHeight>0) b.click() })")
    page.wait_for_timeout(3000)

def scene_shop(page):
    login(page)
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(3000)
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Shop') && b.offsetHeight>0) b.click() })")
    page.wait_for_timeout(3000)

def scene_enchanted(page):
    page.goto(f'{BASE}/island/demo_enchanted_kingdom')
    page.wait_for_timeout(4000)
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Exploring')) b.click() })")
    page.wait_for_timeout(2000)

def scene_space(page):
    page.goto(f'{BASE}/island/78820b5f58a4')
    page.wait_for_timeout(4000)
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Exploring')) b.click() })")
    page.wait_for_timeout(2000)

def scene_castle(page):
    page.goto(f'{BASE}/island/96bd33c64af9')
    page.wait_for_timeout(4000)
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Exploring')) b.click() })")
    page.wait_for_timeout(2000)

def scene_tropical(page):
    page.goto(f'{BASE}/island/demo_tropical_resort')
    page.wait_for_timeout(4000)
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Exploring')) b.click() })")
    page.wait_for_timeout(2000)

def scene_claw(page):
    page.goto(f'{BASE}/island/default')
    page.wait_for_timeout(4000)
    page.evaluate("document.querySelectorAll('button').forEach(b => { if(b.textContent.includes('Exploring')) b.click() })")
    page.wait_for_timeout(2000)

def main():
    print("🎬 Recording remaining scenes\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        
        for name, fn in [
            ('05_farm', scene_farm),
            ('06_spin', scene_spin),
            ('07_shop', scene_shop),
            ('08_enchanted', scene_enchanted),
            ('09_space', scene_space),
            ('10_castle', scene_castle),
            ('11_tropical', scene_tropical),
            ('12_claw', scene_claw),
        ]:
            record(browser, name, fn)
        
        browser.close()
    
    # Now assemble everything
    print("\n=== Assembling final video ===")
    
    all_scenes = ['01_lobby', '02_neon', '03_genspark', '04_build_raw',
                   '05_farm', '06_spin', '07_shop',
                   '08_enchanted', '09_space', '10_castle', '11_tropical', '12_claw']
    
    labels = {
        '01_lobby': ('Island Directory', '36 islands'),
        '02_neon': ('Neon Paradise', '246 items'),
        '03_genspark': ('Genspark', '3,194 items'),
        '04_build_raw': ('Build Mode', 'Place objects'),
        '05_farm': ('Farm', 'Plant & harvest'),
        '06_spin': ('Daily Spin', 'Win rewards'),
        '07_shop': ('Shop', 'Buy & trade'),
        '08_enchanted': ('Enchanted Kingdom', '193 items'),
        '09_space': ('Space Station', 'Sci-fi'),
        '10_castle': ('Castle Fortress', 'Medieval'),
        '11_tropical': ('Tropical Resort', 'Beach'),
        '12_claw': ('Claw Island', 'Home base'),
    }
    
    mp4_files = []
    for name in all_scenes:
        webm = os.path.join(DEMO_DIR, f'{name}.webm')
        mp4 = os.path.join(DEMO_DIR, f'{name}.mp4')
        
        if not os.path.exists(webm):
            continue
        
        label, sub = labels.get(name, (name, ''))
        
        # Convert + trim to 6s max + add label
        subprocess.run([
            'ffmpeg', '-y', '-i', webm,
            '-t', '6',
            '-vf', (
                f"drawbox=x=0:y=ih-75:w=iw:h=75:color=black@0.5:t=fill,"
                f"drawtext=text='{label}':fontcolor=white:fontsize=30:x=35:y=h-58:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
                f"drawtext=text='{sub}':fontcolor=0xaaaaaa:fontsize=17:x=35:y=h-25:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
                f"fade=in:0:15,fade=out:st=5.3:d=0.7"
            ),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', mp4
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(mp4) and os.path.getsize(mp4) > 10000:
            mp4_files.append(mp4)
            dur = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4]).decode().strip()
            print(f"  ✅ {name}.mp4 ({dur}s)")
    
    # Cards
    for cn, t, s, c in [('title','CLAWVERSE','Build. Visit. Collect.','0x44ddff'),
                          ('endcard','clawverse.com','Open Source — Coming Soon','0x44ff88')]:
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=0x0a0e27:s=1920x1080:d=2.5',
            '-vf', f"drawtext=text='{t}':fontcolor=white:fontsize=88:x=(w-text_w)/2:y=(h-text_h)/2-40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,drawtext=text='{s}':fontcolor={c}:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,fade=in:0:20,fade=out:st=2:d=0.5",
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
            os.path.join(DEMO_DIR, f'{cn}.mp4')
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Concat
    concat = os.path.join(DEMO_DIR, 'concat.txt')
    with open(concat, 'w') as f:
        f.write("file 'title.mp4'\n")
        for mp4 in mp4_files:
            f.write(f"file '{os.path.basename(mp4)}'\n")
        f.write("file 'endcard.mp4'\n")
    
    final = os.path.join(DEMO_DIR, 'clawverse_gameplay_demo.mp4')
    subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', final
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(final):
        dur = subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', final]).decode().strip()
        sz = os.path.getsize(final) / (1024*1024)
        print(f"\n🎬 FINAL: {final}")
        print(f"   Duration: {dur}s | Size: {sz:.1f}MB")

if __name__ == '__main__':
    main()
