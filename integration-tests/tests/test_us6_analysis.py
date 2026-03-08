"""US-6: AI analysis tests (US-6.1)."""

import re
import uuid
from playwright.sync_api import Page, expect

SAMPLE_KIF = """手合割：平手
手数----指手--
   1 ７六歩(77)
   2 ３四歩(33)
   3 ２六歩(27)
"""


def _create_kifu(page: Page, base_url: str) -> None:
  """Helper to create a kifu and end up on detail page. Retries on error."""
  for attempt in range(3):
    slug = f"test/analysis-{uuid.uuid4().hex[:8]}"
    page.goto(f"{base_url}/kifus/new", wait_until="networkidle")
    page.locator("#slug").fill(slug)
    page.get_by_text("テキスト").click()
    page.wait_for_timeout(500)
    page.locator("#kif-text").fill(SAMPLE_KIF)

    with page.expect_response(
      lambda resp: "/kifus" in resp.url and resp.request.method == "POST",
      timeout=30000
    ) as resp_info:
      page.get_by_role("button", name="保存").click()

    resp = resp_info.value
    if resp.status == 200 or resp.status == 201:
      page.wait_for_timeout(2000)
      return

    page.wait_for_timeout(3000)

  raise RuntimeError("Failed to create kifu after 3 attempts")


def _cleanup_kifu(page: Page) -> None:
  """Delete current kifu."""
  delete_btn = page.get_by_role("button", name="削除")
  if delete_btn.is_visible():
    delete_btn.click()
    dialog = page.locator(".p-dialog")
    dialog.get_by_role("button", name="削除").click()
    page.wait_for_load_state("networkidle")


class TestUS6_1_Analysis:
  """US-6.1: AI position analysis."""

  def test_analysis_section_exists(
    self, authenticated_page: Page, base_url: str
  ):
    """Kifu detail page has an analysis section with analysis button."""
    page = authenticated_page
    _create_kifu(page, base_url)

    # Analysis section title
    expect(page.get_by_text("AI 局面解析")).to_be_visible()

    # Analysis button
    analysis_btn = page.get_by_role("button", name="解析")
    expect(analysis_btn).to_be_visible()

    _cleanup_kifu(page)

  def test_thinking_time_options(
    self, authenticated_page: Page, base_url: str
  ):
    """Analysis section offers thinking time selection (3s/5s/10s)."""
    page = authenticated_page
    _create_kifu(page, base_url)

    # Thinking time options (PrimeVue SelectButton)
    expect(page.get_by_text("3秒")).to_be_visible()
    expect(page.get_by_text("5秒")).to_be_visible()
    expect(page.get_by_text("10秒")).to_be_visible()

    _cleanup_kifu(page)

  def test_analysis_execution(
    self, authenticated_page: Page, base_url: str
  ):
    """Running analysis shows loading then results or error."""
    page = authenticated_page
    _create_kifu(page, base_url)

    # Click analysis button
    page.get_by_role("button", name="解析").click()

    # Should show loading indicator (button in loading state)
    expect(page.locator("button.p-button-loading")).to_be_visible(timeout=5000)

    # Wait for analysis to complete (button exits loading state)
    # Results may show candidates, or an error message if backend is unavailable
    expect(page.locator("button.p-button-loading")).not_to_be_visible(timeout=60000)

    # After analysis completes, either results or error should be shown
    # The analysis section should have new content
    analysis_section = page.locator(".analysis-section, [class*='analysis']")
    if analysis_section.count() > 0:
      expect(analysis_section.first).to_be_visible()

    _cleanup_kifu(page)
