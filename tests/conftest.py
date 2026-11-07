import os
import sys

import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))
from harness import MockSupabase, Server  # noqa: E402


@pytest.fixture(scope='session')
def server():
    s = Server()
    yield s
    s.close()


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=os.environ.get('CHROME_PATH') or None)
        yield b
        b.close()


@pytest.fixture
def mock():
    return MockSupabase()
