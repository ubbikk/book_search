#!/usr/bin/env python3
"""
Capture screenshots of the 3 demo journeys using Playwright.

Takes screenshots at key moments during each scripted conversation,
producing images ready for the promo video gallery segments.

Usage:
    # Make sure Flask server is running first:
    python app.py

    # Then capture:
    python promo/capture_journeys.py

Output:
    promo/screenshots/
    ├── 00_bookstore_grid.png
    ├── 01_chat_open.png
    ├── j1_01_button_clicked.png
    ├── j1_02_user_martian.png
    ├── j1_03_ai_what_hooked.png
    ├── j1_04_user_humor.png
    ├── j1_05_ai_recommendations.png
    ├── j1_06_recs_closeup.png
    └── ... (similar for j2, j3)
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
BASE_URL = "http://localhost:5000"
VIEWPORT = {"width": 1920, "height": 1080}

# Scripted user inputs for each journey (matching docs/User journeys.md)
JOURNEY_SCRIPTS = {
    "book_i_loved": {
        "button_testid": "btn-book-i-loved",
        "inputs": [
            "The Martian",
            "The humor actually. And yeah it moved fast.",
            "Open to anything",
        ],
    },
    "gift": {
        "button_testid": "btn-gift",
        "inputs": [
            "My mom, she reads constantly",
            "She loved Where the Crawdads Sing",
            "Slower is fine, she likes to savor",
        ],
    },
    "surprise_me": {
        "button_testid": "btn-surprise-me",
        # Journey 3 uses buttons for first two inputs, then text for the third
        "button_clicks": [
            "😬 Keep me up at night",
            "🎭 Mind games",
        ],
        "inputs": [
            "Hate when the twist is 'it was all a dream' or some cop-out",
        ],
    },
}


def wait_for_new_message(page, previous_count, timeout=10):
    """Wait for a new assistant message to appear."""
    start = time.time()
    while time.time() - start < timeout:
        current = page.locator(".msg-assistant").count()
        if current > previous_count:
            time.sleep(0.5)  # Let animation complete
            return current
        time.sleep(0.2)
    return previous_count


def wait_for_recommendations(page, timeout=15):
    """Wait for recommendation cards to appear."""
    start = time.time()
    while time.time() - start < timeout:
        if page.locator(".rec-card").count() > 0:
            time.sleep(0.8)  # Let all cards animate in
            return True
        time.sleep(0.2)
    return False


def count_messages(page):
    """Count assistant messages currently visible."""
    return page.locator(".msg-assistant").count()


def screenshot(page, name, element=None):
    """Take a screenshot and save it."""
    path = SCREENSHOTS_DIR / f"{name}.png"
    if element:
        element.screenshot(path=str(path))
    else:
        page.screenshot(path=str(path))
    print(f"  📸 {name}.png")
    return str(path)


def capture_bookstore_intro(page):
    """Capture the bookstore grid and chat opening."""
    screenshots = []

    # Navigate to demo mode
    page.goto(f"{BASE_URL}/store?demo=1")
    page.wait_for_load_state("networkidle")

    # Wait for books to load
    page.wait_for_selector("[data-testid='chat-panel']:not(.hidden)", timeout=5000)
    time.sleep(1)  # Let grid images load

    # Screenshot: full page with chat open and greeting visible
    screenshots.append(screenshot(page, "00_bookstore_with_chat"))

    return screenshots


def capture_journey(page, journey_id, journey_num):
    """Capture a single demo journey with screenshots at key moments."""
    prefix = f"j{journey_num}"
    screenshots = []
    script = JOURNEY_SCRIPTS[journey_id]

    # Reset chat first
    page.goto(f"{BASE_URL}/store?demo=1")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("[data-testid='chat-panel']:not(.hidden)", timeout=5000)
    time.sleep(1.5)  # Let greeting + buttons appear

    msg_count = count_messages(page)

    # Click the journey button
    btn = page.locator(f"[data-testid='{script['button_testid']}']")
    btn.click()
    time.sleep(0.3)

    # Wait for first AI response
    msg_count = wait_for_new_message(page, msg_count)
    screenshots.append(screenshot(page, f"{prefix}_01_ai_question"))

    if journey_id == "surprise_me":
        # Journey 3: button clicks for first two, then text input
        button_clicks = script.get("button_clicks", [])
        text_inputs = script.get("inputs", [])

        for i, btn_text in enumerate(button_clicks):
            # Wait for buttons to appear
            time.sleep(0.5)
            page.locator(f".demo-btn:has-text('{btn_text}')").click()
            time.sleep(0.3)

            # Wait for AI response
            msg_count = wait_for_new_message(page, msg_count)
            screenshots.append(screenshot(page, f"{prefix}_{i+2:02d}_after_button"))

        # Text input for the last question
        for i, user_input in enumerate(text_inputs):
            time.sleep(0.3)
            input_el = page.locator("#chatInput")
            input_el.fill(user_input)
            page.locator("#sendBtn").click()
            time.sleep(0.3)

            # Wait for AI response
            msg_count = wait_for_new_message(page, msg_count)
            screenshots.append(screenshot(page, f"{prefix}_{len(button_clicks)+i+2:02d}_after_text"))

    else:
        # Journey 1 & 2: alternating text inputs and AI responses
        for i, user_input in enumerate(script["inputs"]):
            time.sleep(0.3)
            input_el = page.locator("#chatInput")
            input_el.fill(user_input)
            page.locator("#sendBtn").click()
            time.sleep(0.3)

            # Wait for AI response
            msg_count = wait_for_new_message(page, msg_count)
            screenshots.append(screenshot(page, f"{prefix}_{i+2:02d}_conversation"))

    # Wait for recommendations
    if wait_for_recommendations(page):
        time.sleep(1)  # Let images load
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        # Scroll chat to show the rec-cards (they get pushed up by the restart msg)
        page.evaluate("""() => {
            const container = document.getElementById('chatMessages');
            const firstCard = container.querySelector('.rec-card');
            if (firstCard) {
                firstCard.scrollIntoView({ block: 'start' });
            }
        }""")
        time.sleep(0.5)

        # Full page with recommendations visible
        screenshots.append(screenshot(page, f"{prefix}_recs_full"))

        # Tight crop of chat panel for recommendation close-up
        chat_panel = page.locator("[data-testid='chat-panel']")
        screenshots.append(screenshot(page, f"{prefix}_recs_closeup", element=chat_panel))

    return screenshots


def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    print("🎬 Capturing demo journey screenshots...")
    print(f"   Output: {SCREENSHOTS_DIR}/\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,  # Retina quality
        )
        page = context.new_page()

        # 1. Bookstore intro
        print("📖 Capturing bookstore intro...")
        intro_shots = capture_bookstore_intro(page)

        # 2. Journey 1: "A book I loved"
        print("\n📚 Journey 1: A book I loved")
        j1_shots = capture_journey(page, "book_i_loved", 1)

        # 3. Journey 2: "It's a gift"
        print("\n🎁 Journey 2: It's a gift")
        j2_shots = capture_journey(page, "gift", 2)

        # 4. Journey 3: "Surprise me"
        print("\n🎲 Journey 3: Surprise me")
        j3_shots = capture_journey(page, "surprise_me", 3)

        browser.close()

    all_shots = intro_shots + j1_shots + j2_shots + j3_shots
    print(f"\n✅ Captured {len(all_shots)} screenshots total")
    print(f"   Saved to: {SCREENSHOTS_DIR}/")


if __name__ == "__main__":
    main()
