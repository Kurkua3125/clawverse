#!/usr/bin/env python3
"""
Clawverse E2E Test Suite — Playwright
Run: python3 tests/e2e_test.py [--artifacts-dir /path/to/dir]

Returns JSON results to stdout for the evolution system to consume.
Exit code 0 = all pass, 1 = failures found.
"""

import json
import sys
import os
import time
import argparse
from urllib.parse import urljoin

BASE_URL = "http://127.0.0.1:19003"
EXTERNAL_URL = "https://ysnlpjle.gensparkclaw.com"

results = {"tests": [], "passed": 0, "failed": 0, "errors": [], "screenshots": []}


def record(name, passed, detail="", screenshot=None):
    results["tests"].append({"name": name, "passed": passed, "detail": detail})
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    if screenshot:
        results["screenshots"].append(screenshot)


def run_tests(artifacts_dir):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        results["errors"].append("Playwright not installed. Run: pip3 install playwright && playwright install chromium")
        print(json.dumps(results, indent=2))
        sys.exit(1)

    os.makedirs(artifacts_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

        def safe_context(**kwargs):
            """Create a new browser context, relaunching browser if it crashed."""
            nonlocal browser
            try:
                return browser.new_context(**kwargs)
            except Exception:
                # Browser may have crashed — relaunch
                try:
                    browser.close()
                except Exception:
                    pass
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                return browser.new_context(**kwargs)

        # ── Test 1: Lobby page loads ──
        try:
            ctx = safe_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            start = time.time()
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=10000)
            load_time = time.time() - start

            # Check title
            title = page.title()
            has_islands = page.query_selector("#island-grid") is not None or page.query_selector("#island-grids-container") is not None
            screenshot_path = os.path.join(artifacts_dir, "lobby_desktop.png")
            page.screenshot(path=screenshot_path, full_page=True)

            record("lobby_loads", has_islands,
                   f"Title: {title}, Islands grid: {has_islands}, Load: {load_time:.2f}s",
                   screenshot_path)

            # Test 1b: Load time
            record("lobby_load_time", load_time < 5.0,
                   f"Load time: {load_time:.2f}s (max 5s)")

            # Test 1c: Console errors
            record("lobby_no_console_errors", len(console_errors) == 0,
                   f"Console errors: {console_errors[:3]}" if console_errors else "No console errors")

            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("lobby_loads", False, f"Error: {str(e)}")

        # ── Test 2: Lobby mobile viewport ──
        try:
            ctx = safe_context(viewport={"width": 390, "height": 844})
            page = ctx.new_page()
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=10000)
            screenshot_path = os.path.join(artifacts_dir, "lobby_mobile.png")
            page.screenshot(path=screenshot_path, full_page=True)

            has_grid = page.query_selector("#island-grid") is not None or page.query_selector("#island-grids-container") is not None
            record("lobby_mobile", has_grid, "Mobile viewport renders", screenshot_path)
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("lobby_mobile", False, f"Error: {str(e)}")

        # ── Test 3: Island page loads ──
        try:
            ctx = safe_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            page.goto(f"{BASE_URL}/island/default", wait_until="domcontentloaded", timeout=15000)

            # Wait for canvas to be visible (game renderer)
            page.wait_for_selector("canvas", state="visible", timeout=15000)

            # Wait for loading screen to disappear (class name may vary)
            try:
                page.wait_for_selector(".loading-container", state="hidden", timeout=10000)
            except Exception:
                pass  # loading container class may differ or already gone

            # Give the canvas a moment to render the actual scene
            page.wait_for_timeout(2000)

            screenshot_path = os.path.join(artifacts_dir, "island_default.png")
            page.screenshot(path=screenshot_path)

            # Check canvas exists
            has_canvas = page.query_selector("canvas") is not None
            record("island_page_loads", has_canvas,
                   f"Canvas: {has_canvas}, Console errors: {len(console_errors)}",
                   screenshot_path)
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("island_page_loads", False, f"Error: {str(e)}")

        # ── Test 3b: Island page has no console JS errors ──
        try:
            ctx = safe_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            page.goto(f"{BASE_URL}/island/default", wait_until="domcontentloaded", timeout=15000)

            # Wait for canvas to be visible so the game has time to initialize
            page.wait_for_selector("canvas", state="visible", timeout=15000)
            page.wait_for_timeout(3000)  # extra time for async errors to surface

            record("island_no_console_errors", len(console_errors) == 0,
                   f"Console errors: {console_errors[:5]}" if console_errors else "No console errors")
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("island_no_console_errors", False, f"Error: {str(e)}")

        # ── Test 4: Login form visible on lobby ──
        try:
            ctx = safe_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=10000)

            email_input = page.query_selector('input[type="email"], input[placeholder*="email"]')
            send_btn = page.query_selector('button:has-text("Verification")')

            record("login_form_visible", email_input is not None,
                   f"Email input: {email_input is not None}, Send button: {send_btn is not None}")
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("login_form_visible", False, f"Error: {str(e)}")

        # ── Test 5: API endpoints ──
        import urllib.request
        import urllib.error

        api_endpoints = [
            ("/api/status", "GET"),
            ("/api/world", "GET"),
            ("/api/catalog", "GET"),
            ("/api/farm", "GET"),
            ("/api/islands", "GET"),
            ("/api/turnips", "GET"),
            ("/api/weather", "GET"),
            ("/api/progress", "GET"),
            ("/api/auth/me", "GET"),
        ]

        all_api_ok = True
        api_details = []
        for endpoint, method in api_endpoints:
            try:
                url = f"{BASE_URL}{endpoint}"
                req = urllib.request.Request(url, method=method)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    status = resp.status
                    data = json.loads(resp.read())
                    ok = status == 200
                    api_details.append(f"{endpoint}: {status}")
                    if not ok:
                        all_api_ok = False
            except Exception as e:
                api_details.append(f"{endpoint}: ERROR {str(e)}")
                all_api_ok = False

        record("api_endpoints_healthy", all_api_ok, "; ".join(api_details))

        # ── Test 6: Island cards have data ──
        try:
            import urllib.request
            url = f"{BASE_URL}/api/islands"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                islands = data.get("islands", [])
                has_islands = len(islands) > 0
                has_names = all(i.get("name") for i in islands[:5])
                record("islands_have_data", has_islands and has_names,
                       f"Count: {len(islands)}, All named: {has_names}")
        except Exception as e:
            record("islands_have_data", False, f"Error: {str(e)}")

        # ── Test 7: Pageview tracking works ──
        try:
            import urllib.request
            data = json.dumps({"world_id": "default"}).encode()
            req = urllib.request.Request(f"{BASE_URL}/api/pageview",
                                         data=data, method="POST",
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read())
                record("pageview_tracking", result.get("ok") == True,
                       f"Response: {result}")
        except Exception as e:
            record("pageview_tracking", False, f"Error: {str(e)}")

        # ── Test 8: Guestbook API ──
        try:
            import urllib.request
            import urllib.error

            # POST a guestbook message
            post_data = json.dumps({
                "name": "E2E Test",
                "message": "Automated test message"
            }).encode()
            post_req = urllib.request.Request(
                f"{BASE_URL}/api/island/default/guestbook",
                data=post_data, method="POST",
                headers={"Content-Type": "application/json"}
            )
            post_ok = False
            post_detail = ""
            post_was_rate_limited = False
            try:
                with urllib.request.urlopen(post_req, timeout=5) as resp:
                    post_status = resp.status
                    post_result = json.loads(resp.read())
                    post_ok = post_status == 200 and post_result.get("ok") == True
                    post_detail = f"POST status={post_status}, ok={post_result.get('ok')}"
            except urllib.error.HTTPError as he:
                # 429 = rate limited from previous run, treat as acceptable
                if he.code == 429:
                    post_ok = True
                    post_was_rate_limited = True
                    post_detail = "POST returned 429 (rate limited, acceptable)"
                else:
                    post_detail = f"POST error: {he.code} {he.reason}"

            # GET guestbook and verify it returns entries
            get_req = urllib.request.Request(
                f"{BASE_URL}/api/island/default/guestbook?limit=50",
                method="GET"
            )
            with urllib.request.urlopen(get_req, timeout=5) as resp:
                get_status = resp.status
                get_result = json.loads(resp.read())
                entries = get_result.get("entries", [])
                # If we successfully posted, verify our message is there
                # If rate-limited, just verify GET works and returns a list
                if post_was_rate_limited:
                    has_message = True  # skip message check when rate-limited
                else:
                    has_message = any(
                        e.get("message") == "Automated test message" or
                        e.get("author_name") == "E2E Test"
                        for e in entries
                    )
                get_detail = f"GET status={get_status}, entries={len(entries)}, found_msg={has_message}"

            passed = post_ok and get_status == 200 and has_message
            record("guestbook_api", passed, f"{post_detail}; {get_detail}")
        except Exception as e:
            record("guestbook_api", False, f"Error: {str(e)}")

        # ── Test 9: Lobby search filter ──
        try:
            ctx = safe_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=10000)

            # Count initial island cards
            initial_cards = page.query_selector_all(".island-card")
            initial_count = len(initial_cards)

            # Find search input and type into it
            search_input = page.query_selector("#island-search")
            assert search_input is not None, "Search input #island-search not found"
            search_input.fill("Test")
            # Trigger the oninput handler
            search_input.dispatch_event("input")
            page.wait_for_timeout(500)

            # Count filtered cards
            filtered_cards = page.query_selector_all(".island-card")
            filtered_count = len(filtered_cards)

            # Clear search and verify cards come back
            search_input.fill("")
            search_input.dispatch_event("input")
            page.wait_for_timeout(500)

            restored_cards = page.query_selector_all(".island-card")
            restored_count = len(restored_cards)

            screenshot_path = os.path.join(artifacts_dir, "lobby_search.png")
            page.screenshot(path=screenshot_path)

            # filtered should be fewer (or equal if all match "Test"), restored should match initial
            passed = (filtered_count <= initial_count) and (restored_count == initial_count) and (initial_count > 0)
            detail = f"Initial: {initial_count}, Filtered: {filtered_count}, Restored: {restored_count}"
            record("lobby_search_filter", passed, detail, screenshot_path)
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("lobby_search_filter", False, f"Error: {str(e)}")

        # ── Test 10: Lobby type filter ──
        try:
            ctx = safe_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=10000)

            # Count initial island cards
            initial_cards = page.query_selector_all(".island-card")
            initial_count = len(initial_cards)

            # Click the Farm filter button 🌾
            farm_btn = page.query_selector('#type-filters button[data-type="farm"]')
            assert farm_btn is not None, "Farm filter button not found"
            farm_btn.click()
            page.wait_for_timeout(500)

            # Count filtered cards
            filtered_cards = page.query_selector_all(".island-card")
            filtered_count = len(filtered_cards)

            # Click "All" to restore
            all_btn = page.query_selector('#type-filters button[data-type="all"]')
            assert all_btn is not None, "All filter button not found"
            all_btn.click()
            page.wait_for_timeout(500)

            restored_cards = page.query_selector_all(".island-card")
            restored_count = len(restored_cards)

            screenshot_path = os.path.join(artifacts_dir, "lobby_type_filter.png")
            page.screenshot(path=screenshot_path)

            # Farm filter should show subset (or all if all are farms), restored should match initial
            passed = (filtered_count <= initial_count) and (restored_count == initial_count) and (initial_count > 0)
            detail = f"Initial: {initial_count}, Farm filtered: {filtered_count}, Restored: {restored_count}"
            record("lobby_type_filter", passed, detail, screenshot_path)
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("lobby_type_filter", False, f"Error: {str(e)}")

        # ── Test 11: Login Flow ──
        try:
            ctx = safe_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=10000)

            # Click a login/CTA trigger to open the login form
            join_btn = page.query_selector('button:has-text("Join"), button:has-text("Login"), button:has-text("Join / Login"), a:has-text("Log in"), button:has-text("Create Your Island"), a:has-text("Create Your Island")')
            assert join_btn is not None, "Login/CTA trigger not found"
            join_btn.click()
            page.wait_for_timeout(1000)

            # Verify login form expanded — look for email input (the form uses email + verification code)
            email_input = page.query_selector('#login-email, input[type="email"], input[placeholder*="email" i]')
            form_visible = email_input is not None
            detail_parts = [f"Form visible: {form_visible}"]

            if email_input:
                email_input.fill("e2e_test@example.com")
                detail_parts.append("Typed email: e2e_test@example.com")

            # Check for the send verification code button
            send_btn = page.query_selector('#btn-send, button:has-text("Send"), button:has-text("Verification")')
            has_send_btn = send_btn is not None
            detail_parts.append(f"Send code button: {has_send_btn}")

            # Check page is still OK (don't actually submit — it would send a real email)
            page_ok = page.query_selector("body") is not None
            detail_parts.append(f"Page OK: {page_ok}")

            screenshot_path = os.path.join(artifacts_dir, "login_flow.png")
            page.screenshot(path=screenshot_path)

            # Pass if the form opened correctly with email input and send button
            passed = form_visible and has_send_btn and page_ok
            record("login_flow", passed, "; ".join(detail_parts), screenshot_path)
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("login_flow", False, f"Error: {str(e)}")

        # ── Test 12: Mobile Island Viewport ──
        try:
            ctx = safe_context(
                viewport={"width": 375, "height": 667},
                device_scale_factor=2,
                is_mobile=True
            )
            page = ctx.new_page()
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            page.goto(f"{BASE_URL}/island/default", wait_until="domcontentloaded", timeout=15000)

            # Wait for canvas to render
            page.wait_for_selector("canvas", state="visible", timeout=15000)
            page.wait_for_timeout(3000)

            # Verify canvas exists and has non-zero dimensions
            canvas = page.query_selector("canvas")
            has_canvas = canvas is not None
            canvas_width = 0
            canvas_height = 0
            if has_canvas:
                box = canvas.bounding_box()
                if box:
                    canvas_width = box["width"]
                    canvas_height = box["height"]
            canvas_ok = canvas_width > 0 and canvas_height > 0

            # Verify topbar is visible and doesn't overflow
            topbar = page.query_selector("#topbar, .topbar, header")
            topbar_visible = topbar is not None
            topbar_detail = ""
            if topbar:
                topbar_box = topbar.bounding_box()
                if topbar_box:
                    topbar_overflow = topbar_box["width"] > 375
                    topbar_detail = f"Topbar width: {topbar_box['width']:.0f}px, overflow: {topbar_overflow}"
                else:
                    topbar_overflow = False
                    topbar_detail = "Topbar box: None"
            else:
                topbar_overflow = False
                topbar_detail = "Topbar not found"

            # Check for JS console errors
            no_errors = len(console_errors) == 0

            screenshot_path = os.path.join(artifacts_dir, "island_mobile.png")
            page.screenshot(path=screenshot_path)

            passed = has_canvas and canvas_ok and topbar_visible and not topbar_overflow and no_errors
            detail = (
                f"Canvas: {has_canvas} ({canvas_width:.0f}x{canvas_height:.0f}), "
                f"{topbar_detail}, "
                f"Console errors: {console_errors[:3] if console_errors else 'none'}"
            )
            record("island_mobile_viewport", passed, detail, screenshot_path)
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("island_mobile_viewport", False, f"Error: {str(e)}")

        # ── Test 13: Activity Feed API ──
        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                f"{BASE_URL}/api/activity?limit=5",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                result = json.loads(resp.read())
                ok_field = result.get("ok")
                events = result.get("events", [])
                is_list = isinstance(events, list)

                detail_parts = [f"status={status}", f"ok={ok_field}", f"events_is_list={is_list}", f"count={len(events)}"]

                # If events exist, check first event has required fields
                fields_ok = True
                if events:
                    first = events[0]
                    has_type = "type" in first
                    has_text = "text" in first
                    has_time = "time" in first
                    fields_ok = has_type and has_text and has_time
                    detail_parts.append(f"first_event_fields: type={has_type}, text={has_text}, time={has_time}")

                passed = status == 200 and ok_field == True and is_list and fields_ok
                record("activity_feed_api", passed, "; ".join(detail_parts))
        except Exception as e:
            record("activity_feed_api", False, f"Error: {str(e)}")

        # ── Test 14: Leaderboard API ──
        try:
            import urllib.request

            # Default category (level)
            req = urllib.request.Request(f"{BASE_URL}/api/leaderboard", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                result = json.loads(resp.read())
                category = result.get("category")
                leaders = result.get("leaders")
                is_str = isinstance(category, str)
                is_list = isinstance(leaders, list)

                detail_parts = [f"status={status}", f"category={category}", f"is_str={is_str}", f"leaders_is_list={is_list}", f"count={len(leaders) if is_list else 'N/A'}"]

                fields_ok = True
                if leaders:
                    first = leaders[0]
                    required = ["name", "world_id", "rank", "level"]
                    for f in required:
                        if f not in first:
                            fields_ok = False
                    detail_parts.append(f"first_leader_fields: {', '.join(f'{f}={f in first}' for f in required)}")

                # Test with category=visits
                req2 = urllib.request.Request(f"{BASE_URL}/api/leaderboard?category=visits", method="GET")
                with urllib.request.urlopen(req2, timeout=5) as resp2:
                    result2 = json.loads(resp2.read())
                    cat2 = result2.get("category")
                    cat_changed = cat2 == "visits"
                    detail_parts.append(f"visits_category={cat2}, changed={cat_changed}")

                passed = status == 200 and is_str and is_list and fields_ok and cat_changed
                record("leaderboard_api", passed, "; ".join(detail_parts))
        except Exception as e:
            record("leaderboard_api", False, f"Error: {str(e)}")

        # ── Test 15: Leaderboard Lobby UI ──
        try:
            ctx = safe_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=10000)

            # Wait for leaderboard section to become visible (loaded async)
            page.wait_for_timeout(2000)

            # Check for leaderboard heading text
            lb_text = page.query_selector('text="Leaderboard"') or page.query_selector('#leaderboard-section')
            has_lb = lb_text is not None
            detail_parts = [f"Leaderboard section: {has_lb}"]

            # Check leaderboard tab buttons (Level, Visits, Objects)
            level_btn = page.query_selector('button[data-cat="level"], button:has-text("Level")')
            visits_btn = page.query_selector('button[data-cat="visits"], button:has-text("Visits")')
            objects_btn = page.query_selector('button[data-cat="objects"], button:has-text("Objects")')
            has_level = level_btn is not None
            has_visits = visits_btn is not None
            has_objects = objects_btn is not None
            detail_parts.append(f"Tabs: Level={has_level}, Visits={has_visits}, Objects={has_objects}")

            screenshot_path = os.path.join(artifacts_dir, "leaderboard_lobby.png")
            page.screenshot(path=screenshot_path, full_page=True)

            passed = has_lb and has_level and has_visits and has_objects
            record("leaderboard_lobby_ui", passed, "; ".join(detail_parts), screenshot_path)
            try:
                ctx.close()
            except Exception:
                pass
        except Exception as e:
            record("leaderboard_lobby_ui", False, f"Error: {str(e)}")

        try:
            browser.close()
        except Exception:
            pass

    return results


def main():
    parser = argparse.ArgumentParser(description="Clawverse E2E Tests")
    parser.add_argument("--artifacts-dir", default="/opt/clawverse/test-artifacts/latest")
    args = parser.parse_args()

    results = run_tests(args.artifacts_dir)

    # Summary
    results["summary"] = f"{results['passed']}/{results['passed'] + results['failed']} tests passed"
    results["all_passed"] = results["failed"] == 0

    print(json.dumps(results, indent=2))
    sys.exit(0 if results["all_passed"] else 1)


if __name__ == "__main__":
    main()
