"""US-8: Navigation tests (US-8.1 ~ US-8.2)."""

import re
from playwright.sync_api import Page, expect


class TestUS8_1_HeaderNavigation:
  """US-8.1: Header navigation for logged-in users."""

  def test_header_has_app_logo(self, authenticated_page: Page, base_url: str):
    """Header shows app logo '将棋棋譜管理' that links to home."""
    page = authenticated_page

    logo = page.locator(".app-header").get_by_text("将棋棋譜管理")
    expect(logo).to_be_visible()

  def test_header_has_mypage_link(self, authenticated_page: Page):
    """Header has 'マイページ' navigation link."""
    page = authenticated_page
    expect(page.get_by_role("menuitem", name="マイページ")).to_be_visible()

  def test_header_has_explorer_link(self, authenticated_page: Page):
    """Header has 'エクスプローラー' navigation link."""
    page = authenticated_page
    expect(page.get_by_role("menuitem", name="エクスプローラー")).to_be_visible()

  def test_header_has_tags_link(self, authenticated_page: Page):
    """Header has 'タグ一覧' navigation link."""
    page = authenticated_page
    expect(page.get_by_role("menuitem", name="タグ一覧")).to_be_visible()

  def test_header_has_logout_button(self, authenticated_page: Page):
    """Header has 'ログアウト' button."""
    page = authenticated_page
    expect(page.get_by_role("button", name="ログアウト")).to_be_visible()

  def test_mypage_navigation(self, authenticated_page: Page, base_url: str):
    """Clicking 'マイページ' navigates to my page."""
    page = authenticated_page
    page.get_by_role("menuitem", name="マイページ").click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/kifus$"))

  def test_explorer_navigation(self, authenticated_page: Page, base_url: str):
    """Clicking 'エクスプローラー' navigates to explorer page."""
    page = authenticated_page
    page.get_by_role("menuitem", name="エクスプローラー").click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/explorer"))

  def test_tags_navigation(self, authenticated_page: Page, base_url: str):
    """Clicking 'タグ一覧' navigates to tags page."""
    page = authenticated_page
    page.get_by_role("menuitem", name="タグ一覧").click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/tags"))

  def test_logo_navigates_to_home(
    self, authenticated_page: Page, base_url: str
  ):
    """Clicking app logo navigates to home."""
    page = authenticated_page

    # First navigate away from home
    page.get_by_role("menuitem", name="マイページ").click()
    page.wait_for_load_state("networkidle")

    # Click logo to go home
    page.locator(".app-header").get_by_text("将棋棋譜管理").click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(rf"^{re.escape(base_url)}/?$"))


class TestUS8_2_LandingPage:
  """US-8.2: Landing page for unauthenticated users."""

  def test_hero_section_title(
    self, unauthenticated_page: Page, base_url: str
  ):
    """Landing page shows hero section with title '将棋棋譜管理'."""
    page = unauthenticated_page
    page.goto(base_url, wait_until="networkidle")

    expect(page.get_by_role("main").get_by_text("将棋棋譜管理")).to_be_visible()

  def test_hero_section_description(
    self, unauthenticated_page: Page, base_url: str
  ):
    """Landing page shows description text."""
    page = unauthenticated_page
    page.goto(base_url, wait_until="networkidle")

    expect(
      page.get_by_text("あなたの棋譜を安全に保管・整理し、AI局面解析で棋力向上を支援します。")
    ).to_be_visible()

  def test_hero_has_login_button(
    self, unauthenticated_page: Page, base_url: str
  ):
    """Landing page has 'ログイン' button."""
    page = unauthenticated_page
    page.goto(base_url, wait_until="networkidle")

    login_btn = page.locator(".app-header").get_by_role("button", name="ログイン")
    expect(login_btn).to_be_visible()

  def test_hero_has_start_button(
    self, unauthenticated_page: Page, base_url: str
  ):
    """Landing page has '今すぐ始める' button."""
    page = unauthenticated_page
    page.goto(base_url, wait_until="networkidle")

    start_btn = page.get_by_role("main").get_by_role("button", name="今すぐ始める")
    expect(start_btn).to_be_visible()

  def test_unauthenticated_header_minimal(
    self, unauthenticated_page: Page, base_url: str
  ):
    """Unauthenticated header shows only logo and login button (no nav menu)."""
    page = unauthenticated_page
    page.goto(base_url, wait_until="networkidle")

    # Logo should be visible
    expect(page.locator(".app-header").get_by_text("将棋棋譜管理")).to_be_visible()

    # Nav menu items should NOT be visible
    expect(page.get_by_role("menuitem", name="マイページ")).not_to_be_visible()
    expect(page.get_by_role("menuitem", name="エクスプローラー")).not_to_be_visible()
