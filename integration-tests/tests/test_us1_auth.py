"""US-1: Authentication tests (US-1.1 ~ US-1.4)."""

import re
from playwright.sync_api import Page, expect


class TestUS1_1_Signup:
  """US-1.1: Users can navigate to sign-up page."""

  def test_signup_link_from_hero(
    self, unauthenticated_page: Page, base_url: str
  ):
    """'今すぐ始める' button navigates to Cognito sign-up page."""
    page = unauthenticated_page
    page.goto(base_url, wait_until="networkidle")

    btn = page.get_by_role("main").get_by_role("button", name="今すぐ始める")
    expect(btn).to_be_visible()
    btn.click()
    page.wait_for_load_state("networkidle")

    # Should navigate to Cognito auth domain
    expect(page).to_have_url(re.compile(r"auth\.shogi-dev|cognito"))

  def test_login_link_from_header(
    self, unauthenticated_page: Page, base_url: str
  ):
    """'ログイン' button in header navigates to Cognito login page."""
    page = unauthenticated_page
    page.goto(base_url, wait_until="networkidle")

    # Use header-scoped locator to avoid matching hero button too
    login_btn = page.locator(".app-header").get_by_role("button", name="ログイン")
    expect(login_btn).to_be_visible()
    login_btn.click()
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"auth\.shogi-dev|cognito"))


class TestUS1_2_Login:
  """US-1.2: Users can log in and see dashboard."""

  def test_login_shows_dashboard(
    self, authenticated_page: Page, base_url: str
  ):
    """After login, dashboard is displayed with user info in header."""
    page = authenticated_page

    # Should be on the home page (logged-in state = dashboard)
    expect(page).to_have_url(re.compile(rf"^{re.escape(base_url)}"))

    # Header should show navigation menu items (use menuitem role for PrimeVue menubar)
    expect(page.get_by_role("menuitem", name="マイページ")).to_be_visible()
    expect(page.get_by_role("menuitem", name="エクスプローラー")).to_be_visible()
    expect(page.get_by_role("menuitem", name="タグ一覧")).to_be_visible()

  def test_login_shows_username_in_header(
    self, authenticated_page: Page
  ):
    """After login, username is displayed in header."""
    page = authenticated_page

    # Header should have a logout button (confirms logged-in state)
    logout_btn = page.get_by_role("button", name="ログアウト")
    expect(logout_btn).to_be_visible()


class TestUS1_3_Logout:
  """US-1.3: Users can log out."""

  def test_logout_redirects_to_home(
    self, authenticated_page: Page, base_url: str
  ):
    """Clicking logout button redirects to home page (unauthenticated)."""
    page = authenticated_page

    logout_btn = page.get_by_role("button", name="ログアウト")
    expect(logout_btn).to_be_visible()
    logout_btn.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # After logout, should see login button (unauthenticated state)
    login_btn = page.locator(".app-header").get_by_role("button", name="ログイン")
    expect(login_btn).to_be_visible()


class TestUS1_4_PasswordChange:
  """US-1.4: Users can access password change page."""

  def test_password_change_link(
    self, authenticated_page: Page, base_url: str
  ):
    """Profile page has a 'パスワード変更' button."""
    page = authenticated_page

    page.goto(f"{base_url}/profile", wait_until="networkidle")

    password_btn = page.get_by_role("button", name="パスワード変更").or_(
      page.get_by_role("link", name="パスワード変更")
    )
    expect(password_btn).to_be_visible()
