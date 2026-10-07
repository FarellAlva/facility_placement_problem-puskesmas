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
        
        # Wait 3 seconds for Leaflet map tiles and initial simulation
        await page.wait_for_timeout(3500)
        
        out_dir = "results_harapan_indah"
        os.makedirs(out_dir, exist_ok=True)
        
        # 1. Initial Map View screenshot
        snap1 = os.path.join(out_dir, "web_osm_initial_view.png")
        await page.screenshot(path=snap1)
        print(f"Saved: {snap1}")
        
        # 2. Click on the map near Jl. Siliwangi / GrandLucky to trigger the inspector
        # Center of map element is around x=950, y=360
        map_el = await page.query_selector("#osmMap")
        box = await map_el.bounding_box()
        if box:
            click_x = box["x"] + box["width"] * 0.52
            click_y = box["y"] + box["height"] * 0.48
            print(f"Clicking map at: ({click_x}, {click_y})")
            await page.mouse.click(click_x, click_y)
            await page.wait_for_timeout(1000)
            
            snap2 = os.path.join(out_dir, "web_osm_inspector_clicked.png")
            await page.screenshot(path=snap2)
            print(f"Saved: {snap2}")
            
        # 3. Click 'Mulai Optimasi Real-Time'
        btn_run = await page.query_selector("#btnRunSim")
        if btn_run:
            print("Clicking Mulai Optimasi Real-Time...")
            await btn_run.click()
            await page.wait_for_timeout(1500)
            
            snap3 = os.path.join(out_dir, "web_osm_optimization_running.png")
            await page.screenshot(path=snap3)
            print(f"Saved: {snap3}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_web())
