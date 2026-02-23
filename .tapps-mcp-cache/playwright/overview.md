### Handle Page Navigation and Wait Conditions in Playwright

This section provides various examples for navigating web pages and controlling wait conditions using Playwright's synchronous API. It covers navigating with different `wait_until` states, setting navigation timeouts, waiting for specific URL patterns or load states, and managing back/forward navigation. It also shows how to wait for navigation triggered by user actions.

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    # Navigate with different wait conditions
    page.goto('https://example.com', wait_until='networkidle')
    page.goto('https://example.com', wait_until='domcontentloaded')
    page.goto('https://example.com', wait_until='load')

    # Navigation with timeout
    try:
        page.goto('https://slow-site.com', timeout=5000)
    except TimeoutError:
        print("Navigation timed out")

    # Wait for specific URL pattern
    page.wait_for_url('**/dashboard')
    page.wait_for_url('https://example.com/success')

    # Wait for load state
    page.wait_for_load_state('networkidle')

    # Back and forward navigation
    page.go_back()
    page.go_forward()
    page.reload()

    # Wait for navigation triggered by action
    with page.expect_navigation():
        page.click('a[href="/next-page"]')

    browser.close()
```

### Perform Assertions with Auto-Waiting in Playwright Python

This snippet illustrates how to use Playwright's assertion library in Python, leveraging its auto-waiting capabilities to verify various states of a web page and its elements. It covers assertions for page title and URL, element visibility (visible, hidden), element state (enabled, disabled, focused, editable, checked), text content, input values, element counts, attributes, and CSS properties. The example initializes a Chromium browser, navigates to 'https://example.com', and applies different assertions to validate the UI.

```python
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com')

    # Page assertions
    expect(page).to_have_title('My Page Title')
    expect(page).to_have_title('My Page', timeout=10000)
    expect(page).to_have_url('https://example.com/dashboard')
    expect(page).to_have_url('**/dashboard')

    # Visibility assertions
    expect(page.locator('button')).to_be_visible()
    expect(page.locator('.loading')).to_be_hidden()
    expect(page.locator('.modal')).not_to_be_visible()

    # State assertions
    expect(page.locator('button')).to_be_enabled()
    expect(page.locator('button.disabled')).to_be_disabled()
    expect(page.locator('input')).to_be_focused()
    expect(page.locator('input[readonly]')).to_be_editable()
    expect(page.locator('input[type="checkbox"]')).to_be_checked()
    expect(page.locator('input[type="checkbox"]')).not_to_be_checked()

    # Text assertions
    expect(page.locator('h1')).to_have_text('Welcome')
    expect(page.locator('.message')).to_contain_text('Success')
    expect(page.locator('h1')).to_have_text(['Item 1', 'Item 2', 'Item 3'])

    # Value assertions
    expect(page.locator('input')).to_have_value('test@example.com')
    expect(page.locator('input')).to_have_value('test', timeout=5000)

    # Count assertions
    expect(page.locator('.items')).to_have_count(5)

    # Attribute assertions
    expect(page.locator('img')).to_have_attribute('src', '/logo.png')
    expect(page.locator('a')).to_have_attribute('href', 'https://example.com')

    # CSS assertions
    expect(page.locator('.price')).to_have_css('color', 'rgb(255, 0, 0)')
    expect(page.locator('h1')).to_have_css('font-size', '24px')

    # Negations
    expect(page.locator('.error')).not_to_be_visible()
    expect(page.locator('button')).not_to_be_disabled()

    browser.close()
```

### Perform Basic Web Automation with Playwright Sync API

This example demonstrates the fundamental steps to launch a browser, navigate to a specified URL, capture a screenshot, and then close the browser using Playwright's synchronous Python API. It also illustrates common browser launch options such as headless mode, slow motion for debugging, and navigation timeouts.

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Launch browser (supports chromium, firefox, webkit)
    browser = p.chromium.launch(
        headless=False,          # Set to True for headless mode
        slow_mo=100,             # Slow down by 100ms for debugging
        timeout=30000            # Navigation timeout in ms
    )

    # Create page and navigate
    page = browser.new_page()
    page.goto('https://example.com')

    # Take screenshot
    page.screenshot(path='screenshot.png', full_page=True)

    # Close browser
    browser.close()
```

### Handle Select Element Events and Bubbling in JavaScript

This JavaScript code initializes a global 'result' object to store captured event data. It defines functions to clear all options from a 'select' element and to set the 'multiple' attribute. Event listeners are attached to a 'select' element for 'input' and 'change' events, and also to the document body to test event bubbling, storing the currently selected option values into the 'result' object.

```javascript
window.result = {
  onInput: null,
  onChange: null,
  onBubblingChange: null,
  onBubblingInput: null,
};
let select = document.querySelector('select');
function makeEmpty() {
  for (let i = select.options.length - 1; i >= 0; --i) {
    select.remove(i);
  }
}
function makeMultiple() {
  select.setAttribute('multiple', true);
}
select.addEventListener('input', () => {
  result.onInput = Array.from(select.querySelectorAll('option:checked')).map((option) => {
    return option.value;
  });
}, false);
select.addEventListener('change', () => {
  result.onChange = Array.from(select.querySelectorAll('option:checked')).map((option) => {
    return option.value;
  });
}, false);
document.body.addEventListener('input', () => {
  result.onBubblingInput = Array.from(select.querySelectorAll('option:checked')).map((option) => {
    return option.value;
  });
}, false);
document.body.addEventListener('change', () => {
  result.onBubblingChange = Array.from(select.querySelectorAll('option:checked')).map((option) => {
    return option.value;
  });
}, false);
```

### Handle errors and timeouts in Playwright sync tests

This synchronous Python example illustrates robust error and timeout handling within Playwright tests. It shows how to set default timeouts for page operations and navigation, catch `TimeoutError` during navigation or selector interactions, and handle general Playwright `Error` exceptions. It also demonstrates a pattern for graceful degradation when optional elements might not be present. Dependencies: `playwright.sync_api.TimeoutError`, `playwright.sync_api.Error`.

```python
from playwright.sync_api import sync_playwright, TimeoutError, Error

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    # Set default timeout for all operations
    page.set_default_timeout(10000)  # 10 seconds
    page.set_default_navigation_timeout(30000)  # 30 seconds for navigation

    # Handle navigation timeout
    try:
        page.goto('https://slow-site.com', timeout=5000)
    except TimeoutError:
        print("Navigation timed out")

    # Handle selector not found
    try:
        page.click('button#missing', timeout=2000)
    except TimeoutError:
        print("Button not found")

    # Wait for selector with timeout
    try:
        page.wait_for_selector('.modal', timeout=5000)
    except TimeoutError:
        print("Modal did not appear")

    # Handle errors
    try:
        page.goto('https://invalid-url')
    except Error as e:
        print(f"Error: {e}")

    # Graceful degradation
    if page.locator('.optional-element').count() > 0:
        page.locator('.optional-element').click()

    browser.close()
```

### Locate Web Elements using Playwright Python

This snippet demonstrates a variety of methods to locate web elements in Playwright for Python. It covers CSS selectors, text-based, role-based, test ID, label, placeholder, text content, alt text, and title attribute locators. Additionally, it shows how to filter, chain, and iterate through locators, as well as count and select specific elements. The code initializes a Chromium browser, navigates to 'https://example.com', and interacts with elements using different locator strategies.

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com')

    # CSS selector locators
    button = page.locator('button#submit')
    button.click()

    # Text-based locators
    page.locator('text=Click here').click()
    page.locator('text="Exact match"').click()

    # Role-based selectors (accessible)
    page.get_by_role('button', name='Submit').click()
    page.get_by_role('textbox', name='Email').fill('test@example.com')
    page.get_by_role('checkbox', name='Accept terms').check()

    # Test ID selector (recommended for stable tests)
    page.get_by_test_id('username').fill('john')

    # Label selector
    page.get_by_label('Email address').fill('user@example.com')
    page.get_by_label('Password').fill('secret')

    # Placeholder selector
    page.get_by_placeholder('Enter your name').fill('John Doe')

    # Text content selector
    page.get_by_text('Welcome back').click()

    # Alt text for images
    page.get_by_alt_text('Company logo').click()

    # Title attribute
    page.get_by_title('More information').click()

    # Filter locators
    rows = page.locator('tr')
    row_with_text = rows.filter(has_text='John')
    row_with_badge = rows.filter(has=page.locator('.badge'))

    # Chain locators
    product = page.locator('.product')
    price = product.locator('.price')
    print(price.text_content())

    # Get nth element
    page.locator('li').first.click()
    page.locator('li').last.click()
    page.locator('li').nth(2).click()

    # Count elements
    count = page.locator('.item').count()
    print(f"Found {count} items")

    # Iterate over all matching elements
    for item in page.locator('.item').all():
        print(item.text_content())

    browser.close()
```

### Format Playwright Python code with pre-commit

These commands install `pre-commit` hooks and then run them across all files in the repository. This ensures consistent code formatting according to project standards and helps maintain a clean codebase.

```sh
pre-commit install
pre-commit run --all-files
```

### Style Box Grid Container and Elements

Provides CSS styling for the page body and box elements to create a compact grid layout. Sets up flexbox properties for box alignment, removes default margins and padding, and hides scrollbars for a clean presentation. Each box is 50x50 pixels with a dark gray border.

```css
body {
  margin: 0;
  padding: 0;
}
.box {
  font-family: arial;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0;
  width: 50px;
  height: 50px;
  box-sizing: border-box;
  border: 1px solid darkgray;
}
::-webkit-scrollbar {
  display: none;
}
```

### Interact with Elements and Fill Forms using Playwright Sync API

This comprehensive example demonstrates various ways to interact with web page elements and fill out forms using Playwright's synchronous Python API. It covers clicking, double-clicking, right-clicking, filling text inputs, typing with simulated delays, pressing keys, checking/unchecking checkboxes, selecting options from dropdowns, handling multiple selections, uploading files, hovering, dragging, and focusing on elements.

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://example.com/form')

    # Click elements
    page.click('button#submit')
    page.click('text=Sign In')
    page.dblclick('.item')
    page.click('button', modifiers=['Shift'])
    page.click('button', button='right')  # Right click

    # Fill inputs (clears and types)
    page.fill('input[name="email"]', 'user@example.com')
    page.fill('#password', 'secret123')

    # Type with delay (simulates human typing)
    page.type('textarea', 'Hello World', delay=100)

    # Press keys
    page.press('input', 'Enter')
    page.press('input', 'Control+A')
    page.keyboard.press('Tab')

    # Checkboxes and radio buttons
    page.check('input[type="checkbox"]')
    page.uncheck('input[type="checkbox"]')

    # Select dropdowns
    page.select_option('select#country', 'US')
    page.select_option('select', label='United States')
    page.select_option('select', value='us')
    page.select_option('select', index=2)

    # Multiple selection
    page.select_option('select[multiple]', ['red', 'blue', 'green'])

    # File upload
    page.set_input_files('input[type="file"]', '/path/to/file.pdf')
    page.set_input_files('input[type="file"]', ['/file1.pdf', '/file2.pdf'])

    # Hover and drag
    page.hover('.menu-item')
    page.drag_and_drop('#source', '#target')

    # Focus element
    page.focus('input')

    browser.close()
```

### Interstitial Test Page CSS Styling

Defines visual styling for interstitial overlay test page including target button states (normal, hidden, removed), hover effects, and absolute-positioned semi-transparent overlay. Uses CSS classes for visibility toggling and state management.

```css
body { position: relative; }
#target.removed { display: none; }
#target.hidden { visibility: hidden; }
#target:hover { background: yellow; }
#interstitial { position: absolute; top: 0; left: 0; width: 300px; height: 300px; border: 1px solid black; background: rgba(255, 180, 180); display: none; }
#interstitial.visible { display: block; }
#close { margin: 50px; }
```