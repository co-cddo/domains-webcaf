from playwright.sync_api import Page, expect


def test_sso_signin(page: Page):
    page.goto("http://localhost:8010/")
    expect(page).to_have_title("Start page  - Submit a CAF self-assessment for a system")

    page.get_by_text("Sign in").click()
    expect(page).to_have_title("dex")
    expect(page.get_by_role("heading")).to_contain_text("Log in to Your Account")

    page.get_by_placeholder("email address").fill("alice@example.gov.uk")
    page.get_by_placeholder("password").fill("password")
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_role("heading")).to_contain_text("Grant Access")

    page.get_by_role("button", name="Grant Access").click()
    expect(page).to_have_title("Select organisation type - alice")
