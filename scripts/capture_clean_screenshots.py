#!/usr/bin/env python3
"""
Capture clean game screenshots using Playwright with VISIBLE browser (not headless).
Uses Xvfb display :99 so the canvas renders properly.
Dismisses all overlays before capturing.
"""
from playwright.sync_api import sync_playwright
import os, time

DEMO = '/opt/clawverse/demo/clean_shots'
BASE = 'https://ysnlpjle.gensparkclaw.com'
os.makedirs(DEMO, exist_ok=True)

def dismiss_and_screenshot(page, name, wait=6):
    """Wait for load, dismiss overlays, then screenshot."""
    page.wait_for_timeout(wait * 1000)
    
    # Dismiss all overlays aggressively
    page.evaluate("""
        // Hide onboarding overlay
        const onb = document.getElementById('onboarding-overlay');
        if (onb) onb.style.display = 'none';
        
        // Hide welcome overlay  
        const wel = document.getElementById('welcome-overlay');
        if (wel) wel.style.display = 'none';
        
        // Hide any visitor overlay
        const vis = document.getElementById('visitor-overlay');
        if (vis) vis.style.display = 'none';
        
        // Click any "Start Exploring" or close buttons
        document.querySelectorAll('button').forEach(b => {
            const t = b.textContent.trim();
            if (t.includes('Start Exploring') || t.includes('✕') || t === '×') {
                try { b.click(); } catch(e) {}
            }
        });
        
        // Hide all overlays with class
        document.querySelectorAll('[class*=overlay], [class*=popup], [class*=modal]').forEach(el => {
            if (el.style.position === 'fixed' || el.style.position === 'absolute') {
                el.style.display = 'none';
            }
        });
        
        // Close the bottom explore bar too (cleaner screenshot)
        const bottomBar = document.getElementById('explore-bar');
        if (bottomBar) bottomBar.style.display = 'none';
        
        // Hide the island type label (e.g., "MINE > Dig for ore")
        document.querySelectorAll('.zone-label, .island-type-label, [class*=zone]').forEach(el => {
            el.style.display = 'none';
        });
    """)
    page.wait_for_timeout(1000)
    
    # Take screenshot
    path = os.path.join(DEMO, f'{name}.png')
    page.screenshot(path=path, type='png')
    sz = os.path.getsize(path) // 1024
    print(f"  ✅ {name}: {sz}KB")
    return path

def main():
    print("🎬 Capturing clean game screenshots (non-headless Playwright)")
    
    with sync_playwright() as p:
        # Launch with DISPLAY=:99 so canvas renders on Xvfb
        browser = p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080', '--start-maximized'],
        )
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            no_viewport=False,
        )
        page = ctx.new_page()
        
        islands = [
            ('01_neon', f'{BASE}/island/demo_neon_paradise'),
            ('02_genspark', f'{BASE}/island/ac4163459b8f'),
            ('03_golden', f'{BASE}/island/demo_golden_empire'),
            ('04_enchanted', f'{BASE}/island/demo_enchanted_kingdom'),
            ('05_cherry', f'{BASE}/island/ecddd6186a6c'),
            ('06_castle', f'{BASE}/island/96bd33c64af9'),
            ('07_space', f'{BASE}/island/78820b5f58a4'),
            ('08_tropical', f'{BASE}/island/demo_tropical_resort'),
            ('09_luck', f'{BASE}/island/60dd3f3795ee'),
            ('10_claw', f'{BASE}/island/default'),
            ('11_lobby', f'{BASE}'),
        ]
        
        for name, url in islands:
            print(f"  📸 {name}")
            page.goto(url, timeout=30000)
            dismiss_and_screenshot(page, name, wait=8)
        
        ctx.close()
        browser.close()
    
    print("\n✅ All screenshots captured!")
    print(f"   Directory: {DEMO}")

if __name__ == '__main__':
    main()
