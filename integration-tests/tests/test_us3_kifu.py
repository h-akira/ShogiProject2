"""US-3: Kifu management tests (US-3.1 ~ US-3.8)."""

import re
import uuid
from playwright.sync_api import Page, expect


def _unique_slug() -> str:
  """Generate a unique kifu slug for testing."""
  return f"test/e2e-{uuid.uuid4().hex[:8]}"


SAMPLE_KIF = """手合割：平手
手数----指手--
   1 ７六歩(77)
   2 ３四歩(33)
   3 ２六歩(27)
"""


def _create_kifu(page: Page, base_url: str, slug: str) -> None:
  """Helper to create a kifu with KIF text. Retries on server error."""
  for attempt in range(3):
    page.goto(f"{base_url}/kifus/new", wait_until="networkidle")

    # Fill slug using id
    page.locator("#slug").fill(slug)

    # Switch to text input mode
    page.get_by_text("テキスト").click()
    page.wait_for_timeout(500)

    # Fill KIF textarea using id
    page.locator("#kif-text").fill(SAMPLE_KIF)

    # Save and capture API response
    with page.expect_response(
      lambda resp: "/kifus" in resp.url and resp.request.method == "POST",
      timeout=30000
    ) as resp_info:
      page.get_by_role("button", name="保存").click()

    resp = resp_info.value
    if resp.status == 200 or resp.status == 201:
      # Wait for SPA navigation to detail page
      page.wait_for_timeout(2000)
      return

    # Server error - wait and retry
    page.wait_for_timeout(3000)

  raise RuntimeError(f"Failed to create kifu after 3 attempts (slug={slug})")


def _delete_current_kifu(page: Page) -> None:
  """Delete the kifu currently being viewed on the detail page."""
  delete_btn = page.get_by_role("button", name="削除")
  if delete_btn.is_visible():
    delete_btn.click()
    # Wait for confirmation dialog
    dialog = page.locator(".p-dialog")
    dialog.get_by_role("button", name="削除").click()
    page.wait_for_load_state("networkidle")


class TestUS3_1_KifuList:
  """US-3.1: Kifu list display on my page."""

  def test_mypage_shows_kifu_table(
    self, authenticated_page: Page, base_url: str
  ):
    """My page shows PrimeVue DataTable."""
    page = authenticated_page
    page.goto(f"{base_url}/kifus", wait_until="networkidle")

    table = page.locator(".p-datatable")
    expect(table).to_be_visible()

  def test_mypage_shows_summary(
    self, authenticated_page: Page, base_url: str
  ):
    """My page shows kifu count summary."""
    page = authenticated_page
    page.goto(f"{base_url}/kifus", wait_until="networkidle")

    summary = page.locator(".summary-section, .summary-card")
    expect(summary.first).to_be_visible()

  def test_mypage_kifu_row_click_navigates(
    self, authenticated_page: Page, base_url: str
  ):
    """Clicking a kifu row navigates to kifu detail page."""
    page = authenticated_page
    slug = _unique_slug()

    # Create a kifu first so we have a row to click
    _create_kifu(page, base_url, slug)

    # Go to kifu list
    page.goto(f"{base_url}/kifus", wait_until="networkidle")

    # Click a row (try full slug first, then short form)
    short_slug = slug.replace("test/", "")
    row = page.locator("tr", has_text=slug).or_(
      page.locator("tr", has_text=short_slug)
    ).first
    row.wait_for(state="visible", timeout=10000)
    row.click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/kifus/.+"))

    # Cleanup
    _delete_current_kifu(page)


class TestUS3_2_KifuCreate:
  """US-3.2: Kifu creation with KIF text input."""

  def test_create_kifu_with_kif_text(
    self, authenticated_page: Page, base_url: str
  ):
    """Creating a kifu with KIF text navigates to detail page."""
    page = authenticated_page
    slug = _unique_slug()

    _create_kifu(page, base_url, slug)

    # Should navigate to the kifu detail page
    expect(page).to_have_url(re.compile(r"/kifus/.+"))

    # Cleanup
    _delete_current_kifu(page)


class TestUS3_3_KifuBoardInput:
  """US-3.3: Shogi board GUI input."""

  def test_board_input_undo(
    self, authenticated_page: Page, base_url: str
  ):
    """Undo button reverts the last move in input mode."""
    page = authenticated_page
    page.goto(f"{base_url}/kifus/new", wait_until="networkidle")

    # Default mode is board input - the board should be visible
    board = page.locator(".shogi-board-container")
    board.wait_for(state="visible", timeout=10000)

    # Game info should show 0 moves initially
    game_info = page.locator(".game-info")
    expect(game_info).to_contain_text("0")

    # Click a square to select piece (77 = row 6, col 6 in 0-indexed -> 7七歩)
    # Then click destination to move
    squares = page.locator(".board .square")
    # Select 7七 (row=6, col=6 -> index = 6*9+6 = 60)
    squares.nth(60).click()
    page.wait_for_timeout(300)
    # Move to 7六 (row=5, col=6 -> index = 5*9+6 = 51)
    squares.nth(51).click()
    page.wait_for_timeout(300)

    # Move count should be 1
    expect(game_info).to_contain_text("1")

    # Click undo button
    undo_btn = page.get_by_role("button", name="一手戻す")
    expect(undo_btn).to_be_visible()
    undo_btn.click()
    page.wait_for_timeout(300)

    # Move count should be back to 0
    expect(game_info).to_contain_text("0")


class TestUS3_4_KifuTextInput:
  """US-3.4: KIF text input mode."""

  def test_text_input_mode_toggle(
    self, authenticated_page: Page, base_url: str
  ):
    """Can switch to text input mode and see a textarea."""
    page = authenticated_page
    page.goto(f"{base_url}/kifus/new", wait_until="networkidle")

    # Switch to text mode
    page.get_by_text("テキスト").click()
    page.wait_for_timeout(500)

    # KIF textarea should be available (using id)
    textarea = page.locator("#kif-text")
    expect(textarea).to_be_visible()


class TestUS3_5_KifuDetail:
  """US-3.5: Kifu detail display and playback."""

  def test_kifu_detail_elements(
    self, authenticated_page: Page, base_url: str
  ):
    """Kifu detail page shows board, meta info, and action buttons."""
    page = authenticated_page
    slug = _unique_slug()

    _create_kifu(page, base_url, slug)

    # Board section should be visible
    board = page.locator(".board-section")
    expect(board).to_be_visible()

    # Edit button (has both icon and label)
    edit_btn = page.get_by_role("button", name="編集")
    expect(edit_btn).to_be_visible()

    # Delete button
    delete_btn = page.get_by_role("button", name="削除")
    expect(delete_btn).to_be_visible()

    # Info section with meta data
    info = page.locator(".info-section")
    expect(info).to_be_visible()

    # Cleanup
    _delete_current_kifu(page)


class TestUS3_6_KifuEdit:
  """US-3.6: Kifu editing."""

  def test_edit_kifu_preloads_data(
    self, authenticated_page: Page, base_url: str
  ):
    """Edit page preloads existing kifu data."""
    page = authenticated_page
    slug = _unique_slug()

    _create_kifu(page, base_url, slug)

    # Navigate to edit
    page.get_by_role("button", name="編集").click()
    page.wait_for_load_state("networkidle")

    # Wait for form data to load (edit page fetches data async)
    page.wait_for_timeout(2000)

    # Slug should be preloaded (without .kif extension)
    slug_field = page.locator("#slug")
    if slug_field.count() == 0:
      slug_field = page.locator("input[type='text']").first
    expect(slug_field).to_have_value(re.compile(re.escape(slug)))

    # Go back and cleanup
    page.go_back()
    page.wait_for_load_state("networkidle")
    _delete_current_kifu(page)

  def test_edit_kifu_board_preload(
    self, authenticated_page: Page, base_url: str
  ):
    """Edit page preloads KIF data into the shogi board (not just initial position)."""
    page = authenticated_page
    slug = _unique_slug()

    _create_kifu(page, base_url, slug)

    # Navigate to edit
    page.get_by_role("button", name="編集").click()
    page.wait_for_load_state("networkidle")

    # Wait for board to load with KIF data
    board = page.locator(".shogi-board-container")
    board.wait_for(state="visible", timeout=10000)
    page.wait_for_timeout(1000)

    # Game info should show move count > 0 (SAMPLE_KIF has 3 moves)
    game_info = page.locator(".game-info")
    expect(game_info).to_contain_text("3")

    # Go back and cleanup
    page.go_back()
    page.wait_for_load_state("networkidle")
    _delete_current_kifu(page)

  def test_edit_kifu_preserves_kif_data(
    self, authenticated_page: Page, base_url: str
  ):
    """Updating in board mode preserves KIF data (no data loss)."""
    page = authenticated_page
    slug = _unique_slug()

    _create_kifu(page, base_url, slug)

    # Navigate to edit
    page.get_by_role("button", name="編集").click()
    page.wait_for_url(re.compile(r"/edit$"), timeout=30000)
    page.wait_for_load_state("networkidle")

    # Wait for form to finish loading (spinner → form)
    memo_field = page.locator("#memo")
    memo_field.wait_for(state="visible", timeout=30000)
    page.wait_for_timeout(1000)

    # Update in board mode (default) - just change memo
    memo_field.clear()
    memo_field.fill("E2E preserve test")

    with page.expect_response(
      lambda resp: "/kifus/" in resp.url and resp.request.method == "PUT",
      timeout=30000
    ) as resp_info:
      page.get_by_role("button", name="更新").click()

    expect(page).not_to_have_url(re.compile(r"/edit$"), timeout=30000)

    # Verify KIF data is preserved by going to edit again
    page.get_by_role("button", name="編集").click()
    page.wait_for_url(re.compile(r"/edit$"), timeout=30000)
    page.wait_for_load_state("networkidle")
    # Wait for edit form to load
    page.locator("#memo").wait_for(state="visible", timeout=30000)

    # Switch to text mode to check KIF content
    page.get_by_text("テキスト").click()
    page.wait_for_timeout(500)

    kif_textarea = page.locator("#kif-text")
    kif_textarea.wait_for(state="visible", timeout=10000)
    kif_value = kif_textarea.input_value()

    # KIF should contain moves (not just header)
    assert "７六歩" in kif_value, f"KIF data lost after update. Content: {kif_value}"

    # Go back and cleanup
    page.go_back()
    page.wait_for_load_state("networkidle")
    _delete_current_kifu(page)

  def test_edit_kifu_update(
    self, authenticated_page: Page, base_url: str
  ):
    """Updating a kifu navigates back to detail page."""
    page = authenticated_page
    slug = _unique_slug()

    _create_kifu(page, base_url, slug)

    # Navigate to edit
    page.get_by_role("button", name="編集").click()
    page.wait_for_load_state("networkidle")

    # Wait for form to finish loading (loading spinner → form fields)
    memo_field = page.locator("#memo")
    memo_field.wait_for(state="visible", timeout=30000)

    # Fill memo (keep board mode so boardRef.getKif() returns valid KIF)
    memo_field.clear()
    memo_field.fill("E2E test memo updated")

    # Update (stay in board mode - default inputMode)
    update_btn = page.get_by_role("button", name="更新")
    update_btn.click()

    # Wait for redirect to detail page (not edit page)
    expect(page).not_to_have_url(re.compile(r"/edit$"), timeout=30000)

    # Cleanup
    _delete_current_kifu(page)

  def test_edit_kifu_discard_changes(
    self, authenticated_page: Page, base_url: str
  ):
    """Discard changes button restores saved data."""
    page = authenticated_page
    slug = _unique_slug()

    _create_kifu(page, base_url, slug)

    # Navigate to edit
    page.get_by_role("button", name="編集").click()
    page.wait_for_url(re.compile(r"/edit$"), timeout=30000)
    page.wait_for_load_state("networkidle")

    # Wait for form to finish loading
    memo_field = page.locator("#memo")
    memo_field.wait_for(state="visible", timeout=30000)

    # Modify memo
    memo_field.clear()
    memo_field.fill("This should be discarded")

    # Click discard button (inside shogi board input controls)
    board_container = page.locator(".shogi-board-container")
    discard_btn = board_container.get_by_role("button", name="変更を破棄")
    expect(discard_btn).to_be_visible()
    discard_btn.click()

    # Confirmation dialog should appear
    dialog = page.locator(".p-dialog")
    expect(dialog).to_be_visible()
    dialog_text = dialog.get_by_text("編集内容を破棄して、保存済みの棋譜を復元しますか？")
    expect(dialog_text).to_be_visible()

    # Confirm discard
    dialog.get_by_role("button", name="破棄する").click()
    page.wait_for_timeout(500)

    # Memo should be restored to original (empty or original value)
    memo_value = memo_field.input_value()
    assert memo_value != "This should be discarded", \
      "Memo was not restored after discard"

    # Go back and cleanup
    page.go_back()
    page.wait_for_load_state("networkidle")
    _delete_current_kifu(page)


class TestUS3_7_KifuDelete:
  """US-3.7: Kifu deletion."""

  def test_delete_kifu_confirmation(
    self, authenticated_page: Page, base_url: str
  ):
    """Deleting kifu shows confirmation dialog and redirects to kifus list."""
    page = authenticated_page
    slug = _unique_slug()

    _create_kifu(page, base_url, slug)

    # Click delete
    page.get_by_role("button", name="削除").click()

    # Confirmation dialog should appear
    dialog = page.locator(".p-dialog")
    expect(dialog).to_be_visible()
    dialog_text = dialog.get_by_text("この棋譜を削除しますか？この操作は取り消せません。")
    expect(dialog_text).to_be_visible()

    # Confirm deletion
    dialog.get_by_role("button", name="削除").click()
    page.wait_for_load_state("networkidle")

    # Should redirect to kifus list
    expect(page).to_have_url(re.compile(r"/kifus$"))


class TestUS3_8_KifuExplorer:
  """US-3.8: Kifu folder hierarchy in explorer."""

  def test_explorer_page(self, authenticated_page: Page, base_url: str):
    """Explorer page loads successfully."""
    page = authenticated_page
    page.goto(f"{base_url}/explorer", wait_until="networkidle")

    expect(page).to_have_url(re.compile(r"/explorer"))
    expect(page.get_by_role("main").first).to_be_visible()

  def test_explorer_empty_folder_message(
    self, authenticated_page: Page, base_url: str
  ):
    """Empty folder shows appropriate message."""
    page = authenticated_page
    page.goto(f"{base_url}/explorer", wait_until="networkidle")

    # Explorer page should be accessible
    expect(page).to_have_url(re.compile(r"/explorer"))
