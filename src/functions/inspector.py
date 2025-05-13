# inspector.py
import asyncio
from playwright.async_api import async_playwright
import os
import json

async def inspect_login_page():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Use non-headless for visibility
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        # Navigate to login page
        print("Navigating to login page...")
        await page.goto("https://customer-cc36.clubcaddie.com/login?clubid=103412")
        
        # Take screenshot of login page
        os.makedirs("screenshots", exist_ok=True)
        await page.screenshot(path="screenshots/login_page.png")
        print(f"Login page screenshot saved to screenshots/login_page.png")
        
        # Extract form elements
        print("\nAnalyzing login form...")
        form_elements = await page.evaluate("""() => {
            const inputs = Array.from(document.querySelectorAll('input')).map(el => ({
                type: el.type,
                id: el.id,
                name: el.name,
                placeholder: el.placeholder,
                selector: getSelector(el)
            }));
            
            const buttons = Array.from(document.querySelectorAll('button')).map(el => ({
                text: el.innerText,
                id: el.id,
                class: el.className,
                selector: getSelector(el)
            }));
            
            // Helper function to get a unique selector
            function getSelector(el) {
                if (el.id) return `#${el.id}`;
                if (el.name) return `[name="${el.name}"]`;
                
                // Try to build a unique selector
                let selector = el.tagName.toLowerCase();
                if (el.className) {
                    const classes = el.className.split(' ').filter(c => c);
                    if (classes.length > 0) {
                        selector += '.' + classes.join('.');
                    }
                }
                return selector;
            }
            
            return { inputs, buttons };
        }""")
        
        # Output found elements
        print("\nFound input elements:")
        for i, input_el in enumerate(form_elements["inputs"]):
            print(f"{i+1}. Type: {input_el.get('type')}, ID: {input_el.get('id')}, Name: {input_el.get('name')}")
            print(f"   Placeholder: {input_el.get('placeholder')}")
            print(f"   Selector: {input_el.get('selector')}\n")
        
        print("\nFound button elements:")
        for i, button in enumerate(form_elements["buttons"]):
            print(f"{i+1}. Text: {button.get('text')}, ID: {button.get('id')}")
            print(f"   Class: {button.get('class')}")
            print(f"   Selector: {button.get('selector')}\n")
        
        # Save detailed HTML structure to file
        html_structure = await page.content()
        with open("login_page_structure.html", "w", encoding="utf-8") as f:
            f.write(html_structure)
        print(f"Complete HTML structure saved to login_page_structure.html")
        
        # Wait for user input before closing
        print("\nPress Enter to continue to next step or Ctrl+C to exit...")
        await asyncio.sleep(2)  # Give time to see the page
        
        # Save selectors to a JSON file for future use
        with open("selectors.json", "w") as f:
            json.dump(form_elements, f, indent=2)
        print("Selectors saved to selectors.json")
        
        # Close the browser
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_login_page())
