from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://nimbus-ssl.mcgill.ca/exsa/search/searchEquivalency")
    page.wait_for_timeout(3000)

    # --- show every text box on the page ---
    boxes = page.get_by_role("textbox")
    print(f"\n=== {boxes.count()} text boxes found ===")
    for i in range(boxes.count()):
        b = boxes.nth(i)
        print(f"[{i}] id={b.get_attribute('id')!r} "
              f"placeholder={b.get_attribute('placeholder')!r} "
              f"visible={b.is_visible()}")

    # --- do a search ---
    idx = int(input("\nWhich box number is the course field? "))
    boxes.nth(idx).fill("PSYC")
    page.get_by_role("button", name="Search").click()
    page.wait_for_timeout(5000)

    # --- dump whatever came back ---
    print("\n=== RESULTS ===")
    rows = page.locator("tr")
    print(f"{rows.count()} rows found\n")
    for i in range(min(rows.count(), 12)):
        text = rows.nth(i).inner_text().replace("\n", " | ")
        print(f"[{i}] {text[:160]}")

    input("\nPress Enter to close...")
    browser.close()
