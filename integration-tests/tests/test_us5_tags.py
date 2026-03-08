"""US-5: Tag management tests (US-5.1 ~ US-5.5)."""

import re
import uuid
from playwright.sync_api import Page, expect


def _unique_tag_name() -> str:
  """Generate a unique tag name for testing."""
  return f"test-tag-{uuid.uuid4().hex[:8]}"


def _create_tag(page: Page, base_url: str, tag_name: str) -> None:
  """Helper to create a tag. Retries on server error."""
  for attempt in range(3):
    page.goto(f"{base_url}/tags/new", wait_until="networkidle")
    page.locator('input[type="text"]').first.fill(tag_name)

    with page.expect_response(
      lambda resp: "/tags" in resp.url and resp.request.method == "POST",
      timeout=30000
    ) as resp_info:
      page.get_by_role("button", name=re.compile(r"保存|作成|追加")).click()

    resp = resp_info.value
    if resp.status == 200 or resp.status == 201:
      page.wait_for_load_state("networkidle")
      return

    page.wait_for_timeout(3000)

  raise RuntimeError(f"Failed to create tag after 3 attempts (name={tag_name})")


class TestUS5_1_TagList:
  """US-5.1: Tag list display."""

  def test_tag_list_page(self, authenticated_page: Page, base_url: str):
    """Tag list page shows a table with tag information."""
    page = authenticated_page
    page.goto(f"{base_url}/tags", wait_until="networkidle")

    # Should be on tags page
    expect(page).to_have_url(re.compile(r"/tags"))

    # PrimeVue DataTable always renders <table>; check it is visible
    table = page.locator(".p-datatable")
    expect(table).to_be_visible()


class TestUS5_2_TagCreate:
  """US-5.2: Tag creation."""

  def test_create_tag(self, authenticated_page: Page, base_url: str):
    """Creating a tag navigates to tag list page."""
    page = authenticated_page
    tag_name = _unique_tag_name()

    _create_tag(page, base_url, tag_name)

    # Should navigate to tags list
    expect(page).to_have_url(re.compile(r"/tags$"))

    # The created tag should appear in the list
    expect(page.get_by_text(tag_name)).to_be_visible()

    # Cleanup: delete the tag
    _delete_tag_by_name(page, tag_name)

  def test_create_tag_empty_name_disabled(
    self, authenticated_page: Page, base_url: str
  ):
    """Save button is disabled when tag name is empty."""
    page = authenticated_page
    page.goto(f"{base_url}/tags/new", wait_until="networkidle")

    # Ensure name input is empty
    name_input = page.locator('input[type="text"]').first
    name_input.fill("")

    save_btn = page.get_by_role("button", name=re.compile(r"保存|作成|追加"))
    expect(save_btn).to_be_disabled()


class TestUS5_3_TagDetail:
  """US-5.3: Tag detail with associated kifus."""

  def test_tag_detail_page(self, authenticated_page: Page, base_url: str):
    """Tag detail page shows tag name and associated kifu count."""
    page = authenticated_page
    tag_name = _unique_tag_name()

    _create_tag(page, base_url, tag_name)

    # Click the tag name cell to go to detail (PrimeVue DataTable row click)
    row = page.locator("tr", has_text=tag_name).first
    row.click()
    page.wait_for_load_state("networkidle")

    # Tag name should be visible on detail page
    expect(page.get_by_text(tag_name)).to_be_visible()

    # Should show empty message since no kifus are associated
    expect(page.locator(".empty-message")).to_be_visible()

    # Cleanup
    page.goto(f"{base_url}/tags", wait_until="networkidle")
    _delete_tag_by_name(page, tag_name)


class TestUS5_4_TagEdit:
  """US-5.4: Tag editing."""

  def test_edit_tag_name(self, authenticated_page: Page, base_url: str):
    """Editing a tag name updates it and navigates to tag list."""
    page = authenticated_page
    original_name = _unique_tag_name()
    updated_name = _unique_tag_name()

    _create_tag(page, base_url, original_name)

    # Find and click edit button (pencil icon) for the tag
    tag_row = page.locator("tr", has_text=original_name)
    edit_btn = tag_row.locator("button .pi-pencil").first
    edit_btn.click()
    page.wait_for_load_state("networkidle")

    # Update the name
    name_input = page.locator('input[type="text"]').first
    name_input.clear()
    name_input.fill(updated_name)

    # Save
    update_btn = page.get_by_role("button", name=re.compile(r"更新|保存"))
    update_btn.click()
    page.wait_for_load_state("networkidle")

    # Should navigate to tags list
    expect(page).to_have_url(re.compile(r"/tags$"))

    # Updated name should be visible
    expect(page.get_by_text(updated_name)).to_be_visible()

    # Cleanup
    _delete_tag_by_name(page, updated_name)


class TestUS5_5_TagDelete:
  """US-5.5: Tag deletion."""

  def test_delete_tag_from_list(
    self, authenticated_page: Page, base_url: str
  ):
    """Deleting a tag from list shows confirmation dialog and removes it."""
    page = authenticated_page
    tag_name = _unique_tag_name()

    _create_tag(page, base_url, tag_name)

    # Click delete button (trash icon) in the tag's row
    tag_row = page.locator("tr", has_text=tag_name)
    delete_btn = tag_row.locator("button .pi-trash").first
    delete_btn.click()

    # Confirmation dialog should appear
    dialog = page.locator(".p-dialog")
    expect(dialog).to_be_visible()

    # Confirm deletion
    confirm_btn = dialog.get_by_role("button", name=re.compile(r"削除"))
    confirm_btn.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Tag should be removed from the list
    expect(page.get_by_text(tag_name)).not_to_be_visible()


def _delete_tag_by_name(page: Page, tag_name: str):
  """Helper to delete a tag by name from the tag list page."""
  tag_row = page.locator("tr", has_text=tag_name)
  if tag_row.count() > 0:
    delete_btn = tag_row.locator("button .pi-trash").first
    delete_btn.click()
    # Confirm deletion in dialog
    dialog = page.locator(".p-dialog")
    dialog.get_by_role("button", name=re.compile(r"削除")).click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
