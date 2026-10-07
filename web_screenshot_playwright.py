import asyncio
import os
from playwright.async_api import async_playwright

async def capture_web():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        
        file_path = os.path.abspath("web/index.html")
        url = f"file:///{file_path.replace(os.sep, '/')}"
        print(f"Opening: {url}")
        await page.goto(url)
        
        # Wait 3.5s for initial tiles and smooth animation to complete
        await page.wait_for_timeout(3500)
        
        out_dir = "results_harapan_indah"
        os.makedirs(out_dir, exist_ok=True)
        
        # 1. Full view showing bounding box and flat minimalist design
        snap1 = os.path.join(out_dir, "web_osm_simplistic_initial.png")
        await page.screenshot(path=snap1)
        print(f"Saved: {snap1}")
        
        # 2. Click Mulai Optimasi to capture mid-animation
        btn_run = await page.query_selector("#btnRunSim")
        if btn_run:
            print("Clicking Mulai Optimasi Real-Time...")
            await btn_run.click()
            # Wait for mid-generation animation
            await page.wait_for_timeout(800)
            snap2 = os.path.join(out_dir, "web_osm_simplistic_running.png")
            await page.screenshot(path=snap2)
            print(f"Saved: {snap2}")
            
        # 3. Wait for playback to reach end and scroll to lower grid
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 480)")
        snap3 = os.path.join(out_dir, "web_osm_simplistic_lower.png")
        await page.screenshot(path=snap3)
        print(f"Saved: {snap3}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_web())
