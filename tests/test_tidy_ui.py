"""Perilaku peta rapi: animasi ke target pohon, seret sementara, tombol Rapikan."""
from conftest import _open

NODES = 'window.__t.nodes()'


def settle(page):
    page.wait_for_function('!window.__t.moving()')


def pos(page):
    return {n['id']: (round(n['x'], 1), round(n['y'], 1)) for n in page.evaluate(NODES)}


def overlaps(a, b):
    return abs(a['x'] - b['x']) < (a['w'] + b['w']) / 2 and abs(a['y'] - b['y']) < (a['h'] + b['h']) / 2


def drag_first(page, dx=220, dy=140):
    box = page.locator('g.node.root .shape').first.bounding_box()
    cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + dx / 2, cy + dy / 2, steps=4)
    page.mouse.move(cx + dx, cy + dy, steps=4)
    page.mouse.up()


def test_posisi_awal_sama_dengan_target(app):
    app.evaluate('window.__t.openAll()')
    settle(app)
    sekarang = pos(app)
    target = {k: (round(v['x'], 1), round(v['y'], 1)) for k, v in app.evaluate('window.__t.target()').items()}
    assert sekarang == target


def test_buka_tutup_kembali_ke_posisi_semula(app):
    app.evaluate('window.__t.openAll()')
    settle(app)
    awal = pos(app)
    kat = app.locator('g.node.kat').first
    kat.click()      # kategori yang terbuka: klik pertama memilih
    kat.click()      # klik kedua menutup cabang
    settle(app)
    assert len(pos(app)) < len(awal)
    app.evaluate('window.__t.openAll()')
    settle(app)
    assert pos(app) == awal


def test_seret_lalu_rapikan(app):
    settle(app)
    awal = pos(app)
    drag_first(app)
    assert pos(app) != awal
    app.click('#tidy')
    settle(app)
    assert pos(app) == awal


def test_seret_lalu_buka_cabang_merapikan(app):
    app.evaluate('window.__t.openAll()')
    settle(app)
    drag_first(app)
    app.evaluate('window.__t.openAll()')
    app.evaluate('window.__t.refreshNow()')
    settle(app)
    target = {k: (round(v['x'], 1), round(v['y'], 1)) for k, v in app.evaluate('window.__t.target()').items()}
    assert pos(app) == target


def test_tanpa_irisan_setelah_banyak_klik(app):
    app.evaluate('window.__t.openAll()')
    for _ in range(5):
        app.locator('g.node.kat').nth(1).click()
        settle(app)
    ns = app.evaluate(NODES)
    assert not [1 for i, a in enumerate(ns) for b in ns[i + 1:] if overlaps(a, b)]


def test_tanpa_animasi_bila_reduced_motion(browser):
    import conftest
    ctx = browser.new_context(reduced_motion='reduce', viewport={'width': 1280, 'height': 860})
    ctx.route('**/*', conftest._route)
    page = ctx.new_page()
    page.goto(f'file://{conftest.ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && !!window.__t.moving')
    page.evaluate('window.__t.openAll()')
    assert page.evaluate('window.__t.moving()') is False
    ctx.close()


def test_data_kosong(browser):
    ctx, page = _open(browser, 'demo&testfiles')
    page.evaluate('window.__t.clearAll()')
    assert page.evaluate(NODES) == []
    assert page.is_visible('#empty')
    page.click('#tidy')
    assert page.errors == []
    ctx.close()


def test_klik_kartu_saat_animasi_tidak_membekukan_peta(app):
    """Temuan peninjau: mousedown memicu 'start' drag; itu tidak boleh menghentikan animasi ke target."""
    app.evaluate("""() => {
      window.__t.openAll();
      const el = document.querySelector('g.node.mat');
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0, clientX: 10, clientY: 10, view: window }));
      window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: 10, clientY: 10, view: window }));
    }""")
    app.wait_for_timeout(900)
    target = {k: (round(v['x'], 1), round(v['y'], 1)) for k, v in app.evaluate('window.__t.target()').items()}
    assert pos(app) == target
