"""Pembaruan DOM berkunci (paintNode patch), siklus keluar 220 ms saat cabang dilipat, dan helper culling."""
from conftest import _open, _route, CHROME, ROOT

COUNT = '''() => ({
  nodes: document.querySelectorAll('#nodes g.node').length,
  links: document.querySelectorAll('#links path').length,
  exitingNodes: document.querySelectorAll('#nodes g.node.exiting').length,
  exitingLinks: document.querySelectorAll('#links path.exiting').length,
  ids: [...document.querySelectorAll('#nodes g.node')].map(e => e.__data__.id),
})'''


def settle(page):
    page.wait_for_function('!window.__t.moving()')


def opened(page):
    page.evaluate('window.__t.openAll()')
    settle(page)


def math_id(page):
    return page.evaluate('window.__t.idByName("Matematika")')


def test_refresh_memakai_ulang_elemen(app):
    opened(app)
    app.evaluate('''() => document.querySelectorAll('#nodes g.node, #nodes g.node *').forEach(e => { e.__keep = 1; })''')
    app.evaluate('window.__t.refreshNow()')
    hilang = app.evaluate('''() => [...document.querySelectorAll('#nodes g.node, #nodes g.node *')].filter(e => !e.__keep).length''')
    assert hilang == 0


def test_ganti_nama_mempatch_teks_dan_badge(app):
    opened(app)
    mid = app.evaluate('window.__t.idByName("Matriks dan Vektor")') or app.evaluate(
        '''() => window.__t.nodes().find(n => n.kind === 'mat').id''')
    app.evaluate(f'''() => {{ const el = [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === "{mid}"); el.__keep = 1; }}''')
    app.evaluate(f'window.__t.rename("{mid}", "Judul materi baru yang cukup panjang supaya teksnya terbungkus menjadi dua baris")')
    settle(app)
    hasil = app.evaluate(f'''() => {{
      const el = [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === "{mid}");
      return {{ keep: el.__keep, lines: [...el.querySelectorAll('text.t tspan')].map(t => t.textContent),
               expected: el.__data__.lines }};
    }}''')
    assert hasil['keep'] == 1
    assert hasil['lines'] == hasil['expected']
    assert len(hasil['lines']) >= 2


def test_badge_ikut_jumlah_materi(app):
    opened(app)
    kid = math_id(app)
    before = app.evaluate(f'''() => [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === "{kid}").querySelector('.badge text').textContent''')
    app.evaluate(f'window.__t.addMat("{kid}", "Materi tambahan")')
    settle(app)
    after = app.evaluate(f'''() => [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === "{kid}").querySelector('.badge text').textContent''')
    assert int(after) == int(before) + 1


def test_lipat_memicu_exit_lalu_dihapus(app):
    opened(app)
    awal = app.evaluate(COUNT)
    app.evaluate(f'window.__t.collapse("{math_id(app)}")')
    saat = app.evaluate(COUNT)
    assert saat['exitingNodes'] > 0 and saat['exitingLinks'] > 0
    pe = app.evaluate('''() => [...document.querySelectorAll('#nodes g.node.exiting')].every(e => getComputedStyle(e).pointerEvents === 'none')''')
    assert pe
    app.wait_for_function('document.querySelectorAll(".exiting").length === 0', timeout=2000)
    akhir = app.evaluate(COUNT)
    assert akhir['nodes'] == len(app.evaluate('window.__t.nodes()')) < awal['nodes']
    assert akhir['links'] == akhir['nodes'] - len(app.evaluate('window.__t.roots()'))


def test_buka_lagi_sebelum_exit_selesai(app):
    opened(app)
    awal = app.evaluate(COUNT)
    kid = math_id(app)
    app.evaluate(f'window.__t.collapse("{kid}")')
    app.wait_for_timeout(60)
    app.evaluate('window.__t.openAll()')
    settle(app)
    app.wait_for_timeout(350)
    akhir = app.evaluate(COUNT)
    assert akhir['exitingNodes'] == 0 and akhir['exitingLinks'] == 0
    assert akhir['nodes'] == awal['nodes'] and akhir['links'] == awal['links']
    assert len(set(akhir['ids'])) == len(akhir['ids'])
    gaya = app.evaluate('''() => [...document.querySelectorAll('#nodes g.node')].map(e => [e.style.opacity, e.style.pointerEvents, e.getAttribute('transform')])''')
    assert all(o == '' and p == '' and 'scale' not in t for o, p, t in gaya)


def test_lipat_berulang_cepat_tidak_menumpuk(app):
    opened(app)
    awal = app.evaluate(COUNT)
    kid = math_id(app)
    for _ in range(6):
        app.evaluate(f'window.__t.collapse("{kid}")')
        app.wait_for_timeout(40)
        app.evaluate('window.__t.openAll()')
        app.wait_for_timeout(40)
    settle(app)
    app.wait_for_timeout(350)
    akhir = app.evaluate(COUNT)
    assert akhir['nodes'] == awal['nodes'] and akhir['exitingNodes'] == 0
    assert len(set(akhir['ids'])) == len(akhir['ids'])


def test_reduced_motion_langsung_hapus(browser):
    ctx = browser.new_context(viewport={'width': 1280, 'height': 860}, reduced_motion='reduce')
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    page.evaluate('window.__t.openAll()')
    page.evaluate(f'window.__t.collapse(window.__t.idByName("Matematika"))')
    c = page.evaluate(COUNT)
    assert c['exitingNodes'] == 0 and c['nodes'] == len(page.evaluate('window.__t.nodes()'))
    ctx.close()


def test_is_in_viewport(app):
    opened(app)
    app.evaluate('window.__t.fitNow()')
    root = app.evaluate('window.__t.roots()[0]')
    assert app.evaluate(f'window.__t.inView("{root}")') is True
    app.evaluate('window.__t.panTo(50000, 50000, 1)')
    assert app.evaluate(f'window.__t.inView("{root}")') is False
    assert app.evaluate('window.__t.inViewIds().length') == 0
