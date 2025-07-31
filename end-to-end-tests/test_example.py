from playwright.sync_api import Page, expect


def test_has_title(page: Page):
    page.goto("http://localhost:8000/")

    # Expect a title "to contain" a substring.
    expect(page).to_have_title("Start page  - Submit a CAF self-assessment for a system")
