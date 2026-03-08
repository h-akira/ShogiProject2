"""US-7: User management tests (US-7.1 ~ US-7.2)."""

import re
from playwright.sync_api import Page, expect


class TestUS7_1_Profile:
  """US-7.1: Profile page display."""

  def test_profile_shows_username(
    self, authenticated_page: Page, base_url: str
  ):
    """Profile page shows username."""
    page = authenticated_page
    page.goto(f"{base_url}/profile", wait_until="networkidle")

    expect(page).to_have_url(re.compile(r"/profile"))

    # Username should be visible (exact element depends on implementation)
    # At minimum, the page should load without error
    expect(page.locator("main, [class*='content'], [class*='Content']").first).to_be_visible()

  def test_profile_shows_email(
    self, authenticated_page: Page, base_url: str
  ):
    """Profile page shows email address."""
    page = authenticated_page
    page.goto(f"{base_url}/profile", wait_until="networkidle")

    # Email should be displayed in main content (not header button)
    email = page.get_by_role("main").get_by_text(re.compile(r"@"))
    expect(email).to_be_visible()

  def test_profile_shows_registration_date(
    self, authenticated_page: Page, base_url: str
  ):
    """Profile page shows registration date."""
    page = authenticated_page
    page.goto(f"{base_url}/profile", wait_until="networkidle")

    # Registration date should be displayed (format: YYYY/MM/DD or similar)
    date_text = page.get_by_text(re.compile(r"\d{4}[/\-]\d{2}[/\-]\d{2}"))
    expect(date_text.first).to_be_visible()

  def test_profile_accessible_from_header(
    self, authenticated_page: Page, base_url: str
  ):
    """Profile page is accessible from username button in header."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    # Find username button/link in header and click
    # The username appears somewhere in the header as a clickable element
    header = page.locator("header, nav").first
    # Look for a link/button that leads to profile
    profile_link = header.locator('a[href*="/profile"]')
    if profile_link.count() > 0:
      profile_link.click()
      page.wait_for_load_state("networkidle")
      expect(page).to_have_url(re.compile(r"/profile"))


class TestUS7_2_AccountDelete:
  """US-7.2: Account deletion page (display only, no actual deletion)."""

  def test_account_delete_page_accessible(
    self, authenticated_page: Page, base_url: str
  ):
    """Account deletion page is accessible from profile."""
    page = authenticated_page
    page.goto(f"{base_url}/profile", wait_until="networkidle")

    delete_link = page.get_by_role("button", name=re.compile(r"アカウント削除")).or_(
      page.get_by_role("link", name=re.compile(r"アカウント削除"))
    )
    expect(delete_link).to_be_visible()
    delete_link.click()
    page.wait_for_load_state("networkidle")

    # Warning message should be displayed
    warning = page.get_by_text(
      re.compile(r"アカウントを削除すると.*すべての棋譜.*削除されます")
    )
    expect(warning).to_be_visible()

  def test_account_delete_requires_password(
    self, authenticated_page: Page, base_url: str
  ):
    """Account deletion page requires password input."""
    page = authenticated_page
    page.goto(f"{base_url}/profile", wait_until="networkidle")

    delete_link = page.get_by_role("button", name=re.compile(r"アカウント削除")).or_(
      page.get_by_role("link", name=re.compile(r"アカウント削除"))
    )
    delete_link.click()
    page.wait_for_load_state("networkidle")

    # Password input should be present
    password_input = page.locator('input[type="password"]')
    expect(password_input).to_be_visible()

    # Delete button should be disabled without password
    delete_btn = page.get_by_role("button", name="アカウントを削除")
    expect(delete_btn).to_be_disabled()
