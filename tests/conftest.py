"""Fixture Playwright untuk Synthesis: halaman ?demo&testfiles dengan pustaka CDN dilayani dari salinan lokal."""
import pathlib
import pytest
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = pathlib.Path('/opt/npm-tools/node_modules')
LOCAL = {
    'd3.min.js': NODE / 'd3/dist/d3.min.js',
    'marked.umd.js': NODE / 'marked/lib/marked.umd.js',
    'purify.min.js': NODE / 'dompurify/dist/purify.min.js',
}
CHROME = '/usr/bin/google-chrome'


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
        yield b
        b.close()


def _open(browser, query, viewport=None):
    ctx = browser.new_context(viewport=viewport or {'width': 1280, 'height': 860})

    def route(r):
        u = r.request.url
        for name, path in LOCAL.items():
            if u.split('?')[0].endswith(name):
                return r.fulfill(path=str(path), content_type='application/javascript')
        if u.startswith('file://') or u.startswith('blob:') or u.startswith('data:'):
            return r.continue_()
        return r.abort()

    ctx.route('**/*', route)
    page = ctx.new_page()
    page.errors = []
    page.on('pageerror', lambda e: page.errors.append(str(e)))
    page.add_init_script('try { localStorage.clear() } catch (e) {}')
    page.goto(f'file://{ROOT}/index.html?{query}')
    page.wait_for_function('document.querySelectorAll("g.node").length > 0')
    return ctx, page


@pytest.fixture
def app(browser):
    """Mode contoh dengan penyimpanan file tiruan di memori (window.__t)."""
    ctx, page = _open(browser, 'demo&testfiles')
    page.wait_for_function('!!window.__t')
    yield page
    assert page.errors == [], page.errors
    ctx.close()


@pytest.fixture
def demo(browser):
    """Mode contoh biasa, tanpa penyimpanan file."""
    ctx, page = _open(browser, 'demo')
    yield page
    assert page.errors == [], page.errors
    ctx.close()
