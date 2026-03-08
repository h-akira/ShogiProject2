"""US-4: Kifu sharing tests (US-4.1 ~ US-4.2)."""

import re
import uuid
from playwright.sync_api import Page, expect


SAMPLE_KIF = """手合割：平手
手数----指手--
   1 ７六歩(77)
   2 ３四歩(33)
"""


def _unique_slug() -> str:
  return f"test/share-{uuid.uuid4().hex[:8]}"


class TestUS4_1_ShareSettings:
  """US-4.1: Kifu sharing settings."""

  def test_share_toggle_and_code(
    self, authenticated_page: Page, base_url: str
  ):
    """Creating a shared kifu shows share code on detail page."""
    page = authenticated_page
    slug = _unique_slug()

    # Create a kifu with sharing enabled
    page.goto(f"{base_url}/kifus/new", wait_until="networkidle")
    slug_input = page.locator('input[name="slug"], input[placeholder*="スラグ"]').first
    if slug_input.count() == 0:
      slug_input = page.locator('input[type="text"]').first
    slug_input.fill(slug)

    text_mode = page.get_by_text("テキスト").first
    if text_mode.is_visible():
      text_mode.click()
    page.locator("textarea").first.fill(SAMPLE_KIF)

    # Enable sharing
    share_toggle = page.locator(
      'input[name="shared"], [class*="switch"], [class*="Switch"], [role="switch"]'
    ).first
    if share_toggle.is_visible():
      share_toggle.click()

    page.get_by_role("button", name=re.compile(r"保存|作成")).click()
    page.wait_for_load_state("networkidle")

    # Detail page should show share code or share link
    share_section = page.get_by_text(re.compile(r"共有|share")).first
    expect(share_section).to_be_visible()

    # Cleanup
    _delete_current_kifu(page)


class TestUS4_2_SharedView:
  """US-4.2: Viewing shared kifu."""

  def test_shared_kifu_viewable_without_login(
    self, authenticated_page: Page, unauthenticated_page: Page, base_url: str
  ):
    """Shared kifu can be viewed via share link without login."""
    auth_page = authenticated_page
    slug = _unique_slug()

    # Create a shared kifu
    auth_page.goto(f"{base_url}/kifus/new", wait_until="networkidle")
    slug_input = auth_page.locator(
      'input[name="slug"], input[placeholder*="スラグ"]'
    ).first
    if slug_input.count() == 0:
      slug_input = auth_page.locator('input[type="text"]').first
    slug_input.fill(slug)

    text_mode = auth_page.get_by_text("テキスト").first
    if text_mode.is_visible():
      text_mode.click()
    auth_page.locator("textarea").first.fill(SAMPLE_KIF)

    # Enable sharing
    share_toggle = auth_page.locator(
      'input[name="shared"], [class*="switch"], [class*="Switch"], [role="switch"]'
    ).first
    if share_toggle.is_visible():
      share_toggle.click()

    auth_page.get_by_role("button", name=re.compile(r"保存|作成")).click()
    auth_page.wait_for_load_state("networkidle")

    # Get share URL from the detail page
    share_link_el = auth_page.locator(
      'input[readonly], [class*="share-link"], a[href*="/shared/"]'
    ).first

    if share_link_el.is_visible():
      share_url = share_link_el.get_attribute("value") or share_link_el.get_attribute("href") or ""

      if share_url:
        # View with unauthenticated page
        unauth_page = unauthenticated_page
        if not share_url.startswith("http"):
          share_url = f"{base_url}{share_url}"
        unauth_page.goto(share_url, wait_until="networkidle")

        # Board should be visible (read-only playback)
        board = unauth_page.locator(
          'canvas, [class*="board"], [class*="Board"]'
        )
        expect(board.first).to_be_visible()

        # Edit/delete buttons should NOT be visible
        edit_btn = unauth_page.get_by_role("button", name="編集")
        expect(edit_btn).not_to_be_visible()

    # Cleanup
    _delete_current_kifu(auth_page)

  def test_invalid_share_code(
    self, unauthenticated_page: Page, base_url: str
  ):
    """Invalid share code shows 'not found' message."""
    page = unauthenticated_page
    page.goto(
      f"{base_url}/shared/invalid-code-{uuid.uuid4().hex[:8]}",
      wait_until="networkidle",
    )

    not_found = page.get_by_text("共有棋譜が見つかりません")
    expect(not_found).to_be_visible()


def _delete_current_kifu(page: Page):
  """Delete the kifu currently being viewed on the detail page."""
  delete_btn = page.get_by_role("button", name="削除")
  if delete_btn.is_visible():
    delete_btn.click()
    confirm_btn = page.get_by_role("button", name="削除")
    confirm_btn.click()
    page.wait_for_load_state("networkidle")
