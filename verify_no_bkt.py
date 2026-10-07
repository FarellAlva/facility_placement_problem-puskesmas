import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def verify():
    target_path = os.path.abspath("web/index.html")
    file_url = f"file:///{target_path.replace(os.sep, '/')}"
    print(f"Testing URL: {file_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("console", lambda msg: print(f"Browser console [{msg.type}]: {msg.text}") if msg.type in ['error', 'warn'] else None)
        
        await page.goto(file_url, wait_until="networkidle")
        await asyncio.sleep(1.0)
        
        # 1. Verify togRiver button is gone
        tog_river_count = await page.locator("#togRiver").count()
        print(f"togRiver button count: {tog_river_count} (expected 0)")
        assert tog_river_count == 0, "togRiver button should be removed"
        
        # 2. Verify 'BKT' is not in layer toggles
        footer_text = await page.locator(".map-layer-footer").inner_text()
        print(f"Layer footer text: '{footer_text}'")
        assert "bkt" not in footer_text.lower(), "BKT should not be in layer footer"
        assert "kanal" not in footer_text.lower(), "Kanal should not be in layer footer"
        
        # 3. Take screenshot
        os.makedirs("results_harapan_indah", exist_ok=True)
        screenshot_path = "results_harapan_indah/web_no_bkt_river.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"Saved screenshot to {screenshot_path}")
        
        # 4. Run an optimization step to ensure everything runs smoothly
        await page.locator("#btnRunSim").click()
        await asyncio.sleep(1.5)
        
        await browser.close()
        
        if errors:
            print("Errors encountered:", errors)
            sys.exit(1)
        print("SUCCESS: Sungai BKT successfully removed with 0 errors!")

if __name__ == "__main__":
    asyncio.run(verify())
