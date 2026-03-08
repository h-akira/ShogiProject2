"""Shared fixtures for integration tests."""

import os
import json
import pytest
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import Page, Browser, BrowserContext

load_dotenv()

BASE_URL = os.environ.get("BASE_URL")
TEST_EMAIL = os.environ.get("TEST_EMAIL")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD")

if not BASE_URL:
  raise ValueError("BASE_URL environment variable is required")
if not TEST_EMAIL:
  raise ValueError("TEST_EMAIL environment variable is required")
if not TEST_PASSWORD:
  raise ValueError("TEST_PASSWORD environment variable is required")

STORAGE_STATE_PATH = Path(__file__).parent / "auth_storage_state.json"


@pytest.fixture(scope="session")
def base_url() -> str:
  return BASE_URL


@pytest.fixture(scope="session")
def _auth_storage_state(browser: Browser) -> str:
  """Perform Cognito login once and save storage state for reuse."""
  context = browser.new_context()
  page = context.new_page()

  # Navigate to the site
  page.goto(BASE_URL, wait_until="networkidle")

  # Click login button
  login_btn = page.locator('button:has-text("ログイン"), a:has-text("ログイン")').first
  login_btn.click()
  page.wait_for_load_state("networkidle")

  # Fill Cognito Managed Login form
  # Two forms exist (hidden + visible), use .nth(1) for visible ones
  if "auth.shogi-dev" in page.url or "cognito" in page.url:
    page.wait_for_load_state("networkidle")
    page.locator('input[name="username"]').nth(1).fill(TEST_EMAIL)
    page.locator('input[name="password"]').nth(1).fill(TEST_PASSWORD)
    page.locator('input[name="signInSubmitButton"]').nth(1).click()
    page.wait_for_load_state("networkidle")

  # Wait for callback processing
  if "/callback" in page.url:
    page.wait_for_timeout(3000)

  # Wait for app to settle after login
  page.wait_for_timeout(2000)
  page.wait_for_load_state("networkidle")

  # Save storage state (cookies + localStorage/sessionStorage workaround)
  storage_state = context.storage_state(path=str(STORAGE_STATE_PATH))

  # Also capture sessionStorage (not included in Playwright storage_state)
  session_storage = page.evaluate("() => JSON.stringify(sessionStorage)")
  storage_state["sessionStorage"] = json.loads(session_storage)
  with open(STORAGE_STATE_PATH, "w") as f:
    json.dump(storage_state, f)

  context.close()
  return str(STORAGE_STATE_PATH)


@pytest.fixture(scope="function")
def authenticated_context(
  browser: Browser, _auth_storage_state: str
) -> BrowserContext:
  """Create a browser context with saved auth cookies."""
  # Load storage state for cookies
  context = browser.new_context(storage_state=_auth_storage_state)
  yield context
  context.close()


@pytest.fixture(scope="function")
def authenticated_page(
  authenticated_context: BrowserContext, _auth_storage_state: str
) -> Page:
  """Provide a logged-in page with sessionStorage restored."""
  page = authenticated_context.new_page()

  # Navigate to site first, then restore sessionStorage
  page.goto(BASE_URL, wait_until="networkidle")

  # Restore sessionStorage from saved state
  with open(_auth_storage_state) as f:
    state = json.load(f)
  session_data = state.get("sessionStorage", {})
  if session_data:
    page.evaluate(
      """(data) => {
        for (const [key, value] of Object.entries(data)) {
          sessionStorage.setItem(key, value);
        }
      }""",
      session_data,
    )
    # Reload to apply sessionStorage
    page.reload(wait_until="networkidle")

  yield page


@pytest.fixture(scope="function")
def unauthenticated_page(browser: Browser) -> Page:
  """Provide a clean page without any auth state."""
  context = browser.new_context()
  page = context.new_page()
  yield page
  context.close()
