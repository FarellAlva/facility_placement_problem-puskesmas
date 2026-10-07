from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1600, 'height': 1050})
    page.goto('http://localhost:8000/web/index.html')
    time.sleep(2)

    # 1. Full dashboard screenshot
    page.screenshot(path='results_harapan_indah/doc_web_dashboard.png')
    print('Saved doc_web_dashboard.png')

    # 2. Map Card with all layers
    map_card = page.query_selector('.map-card')
    if map_card:
        map_card.screenshot(path='results_harapan_indah/doc_map_complete.png')
        print('Saved doc_map_complete.png')

    # 3. Capture RAW Map with Bounding Box only
    # Click toggle chips to turn off density, particles, lines, optimal
    for btn_id in ['#togDensity', '#togParticles', '#togLines', '#togOptimal']:
        page.click(btn_id)
        time.sleep(0.2)
    time.sleep(1)
    if map_card:
        map_card.screenshot(path='results_harapan_indah/doc_raw_map_box.png')
        print('Saved doc_raw_map_box.png')

    # 4. Turn back on for convergence and scorecard
    lower_grid = page.query_selector('.lower-grid')
    if lower_grid:
        lower_grid.screenshot(path='results_harapan_indah/doc_convergence_scorecard.png')
        print('Saved doc_convergence_scorecard.png')

    browser.close()
