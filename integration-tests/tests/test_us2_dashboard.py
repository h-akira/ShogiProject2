"""US-2: Dashboard tests (US-2.1)."""

import re
from playwright.sync_api import Page, expect


class TestUS2_1_Dashboard:
  """US-2.1: Dashboard display after login."""

  def test_dashboard_has_mypage_card(
    self, authenticated_page: Page, base_url: str
  ):
    """Dashboard shows 'マイページ' card."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    # Scope to main content area to avoid matching header nav items
    expect(page.get_by_role("main").get_by_text("マイページ")).to_be_visible()

  def test_dashboard_has_explorer_card(
    self, authenticated_page: Page, base_url: str
  ):
    """Dashboard shows 'エクスプローラー' card."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    expect(page.get_by_role("main").get_by_text("エクスプローラー")).to_be_visible()

  def test_dashboard_has_tags_card(
    self, authenticated_page: Page, base_url: str
  ):
    """Dashboard shows 'タグ一覧' card."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    expect(page.get_by_role("main").get_by_text("タグ一覧")).to_be_visible()

  def test_dashboard_has_create_kifu_card(
    self, authenticated_page: Page, base_url: str
  ):
    """Dashboard shows '棋譜作成' card."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    expect(page.get_by_role("main").get_by_text("棋譜作成")).to_be_visible()

  def test_mypage_card_navigation(
    self, authenticated_page: Page, base_url: str
  ):
    """Clicking 'マイページ' card navigates to kifus page."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    # PrimeVue Card: find the link inside the card
    main = page.get_by_role("main")
    card = main.locator(".p-card").filter(has_text="マイページ").first
    link = card.locator("a").first
    if link.count() > 0:
      link.click()
    else:
      card.click()
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"/kifus$"))

  def test_explorer_card_navigation(
    self, authenticated_page: Page, base_url: str
  ):
    """Clicking 'エクスプローラー' card navigates to explorer page."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    main = page.get_by_role("main")
    card = main.locator(".p-card").filter(has_text="エクスプローラー").first
    link = card.locator("a").first
    if link.count() > 0:
      link.click()
    else:
      card.click()
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"/explorer"))

  def test_tags_card_navigation(
    self, authenticated_page: Page, base_url: str
  ):
    """Clicking 'タグ一覧' card navigates to tags page."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    main = page.get_by_role("main")
    card = main.locator(".p-card").filter(has_text="タグ一覧").first
    link = card.locator("a").first
    if link.count() > 0:
      link.click()
    else:
      card.click()
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"/tags"))

  def test_create_kifu_card_navigation(
    self, authenticated_page: Page, base_url: str
  ):
    """Clicking '棋譜作成' card navigates to kifu creation page."""
    page = authenticated_page
    page.goto(base_url, wait_until="networkidle")

    main = page.get_by_role("main")
    card = main.locator(".p-card").filter(has_text="棋譜作成").first
    link = card.locator("a").first
    if link.count() > 0:
      link.click()
    else:
      card.click()
    page.wait_for_load_state("networkidle")

    expect(page).to_have_url(re.compile(r"/kifus/new|/kifus/create"))
