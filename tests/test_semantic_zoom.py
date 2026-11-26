"""Morfosis semantik kartu materi ↔ titik konstelasi (zoom far) dan peek saat hover."""
from conftest import _open, _route, ROOT

GEOM = '''id => {
  const el = [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === id);
  const s = el.querySelector('.shape'), i = el.querySelector('.ico'), t = el.querySelector('.t');
  const n = k => +s.getAttribute(k);
  return { x: n('x'), y: n('y'), w: n('width'), h: n('height'), rx: n('rx'),
           cx: +i.getAttribute('cx'), cy: +i.getAttribute('cy'), r: +i.getAttribute('r'),
           op: +getComputedStyle(t).opacity, dw: el.__data__.w, dh: el.__data__.h };
}'''


def ready(page):
    page.evaluate('window.__t.openAll()')
    page.wait_for_function('!window.__t.moving()')
    page.evaluate('window.__t.fitNow()')


def mat_ids(page):
    return [n['id'] for n in page.evaluate('window.__t.nodes()') if n['kind'] == 'mat']


def zoom_to(page, k):
    page.evaluate(f'''() => {{ const t = d3.zoomTransform(document.querySelector('#map'));
      window.__t.panTo(640 - ({k} / t.k) * (640 - t.x), 430 - ({k} / t.k) * (430 - t.y), {k}); }}''')


def test_far_menjadi_titik_konstelasi(app):
    ready(app)
    zoom_to(app, 0.3)
    app.wait_for_timeout(600)
    for mid in mat_ids(app):
        g = app.evaluate(GEOM, mid)
        assert (g['x'], g['y'], g['w'], g['h'], g['rx']) == (-9, -9, 18, 18, 9)
        assert (g['cx'], g['cy'], g['r']) == (0, 0, 7.5)
        assert g['op'] < 0.01


def test_kembali_ke_kartu(app):
    ready(app)
    zoom_to(app, 0.3)
    app.wait_for_timeout(600)
    zoom_to(app, 1)
    app.wait_for_timeout(600)
    for mid in mat_ids(app):
        g = app.evaluate(GEOM, mid)
        assert (g['w'], g['h']) == (g['dw'], g['dh'])
        assert g['r'] == 4 and g['op'] > 0.99


def test_morfosis_berjalan_bertahap(app):
    ready(app)
    mid = mat_ids(app)[0]
    zoom_to(app, 0.3)
    app.wait_for_timeout(60)
    g = app.evaluate(GEOM, mid)
    assert 18 < g['w'] < g['dw']


def test_kategori_tetap_kartu_di_far(app):
    ready(app)
    before = app.evaluate('''() => [...document.querySelectorAll('#nodes g.node.kat .shape')].map(s => s.getAttribute('width'))''')
    zoom_to(app, 0.3)
    app.wait_for_timeout(600)
    after = app.evaluate('''() => [...document.querySelectorAll('#nodes g.node.kat .shape')].map(s => s.getAttribute('width'))''')
    assert before == after
    assert app.evaluate('''() => [...document.querySelectorAll('#nodes g.node.kat .badge text')].every(t => getComputedStyle(t).display !== 'none')''')


def test_histeresis_ambang(app):
    ready(app)
    zoom_to(app, 0.48)
    assert app.evaluate('document.querySelector("#map").dataset.zoom') == 'mid'
    zoom_to(app, 0.44)
    assert app.evaluate('document.querySelector("#map").dataset.zoom') == 'far'
    zoom_to(app, 0.52)
    assert app.evaluate('document.querySelector("#map").dataset.zoom') == 'far'
    zoom_to(app, 0.56)
    assert app.evaluate('document.querySelector("#map").dataset.zoom') == 'mid'


def hover_point(page, mid):
    return page.evaluate('''id => { const el = [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === id);
      const r = el.querySelector('.ico').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }''', mid)


def test_peek_saat_hover_di_far(app):
    ready(app)
    zoom_to(app, 0.4)
    app.wait_for_timeout(600)
    mid = mat_ids(app)[0]
    k0 = app.evaluate('d3.zoomTransform(document.querySelector("#map")).k')
    order0 = app.evaluate('''() => [...document.querySelectorAll('#nodes g.node')].map(e => e.__data__.id)''')
    x, y = hover_point(app, mid)
    app.mouse.move(x, y)
    app.wait_for_timeout(500)
    peek = app.evaluate('''() => { const g = document.querySelector('#overlay .peek'); if (!g) return null;
      const r = g.querySelector('.shape').getBoundingClientRect();
      return { open: g.classList.contains('open'), text: g.querySelector('.t').textContent, h: r.height,
               display: getComputedStyle(g).display, op: +getComputedStyle(g.querySelector('.t')).opacity }; }''')
    assert peek and peek['open'] and peek['display'] != 'none'
    assert peek['text'] and peek['op'] > 0.99
    assert 26 <= peek['h'] <= 30                     # ukuran layar tetap, tidak ikut skala peta
    assert app.evaluate('d3.zoomTransform(document.querySelector("#map")).k') == k0
    assert app.evaluate('''() => [...document.querySelectorAll('#nodes g.node')].map(e => e.__data__.id)''') == order0
    app.mouse.move(5, 845)
    app.wait_for_timeout(500)
    assert app.evaluate('''() => { const g = document.querySelector('#overlay .peek'); return !g || getComputedStyle(g).display === 'none'; }''')


def test_hover_cepat_antar_titik(app):
    ready(app)
    zoom_to(app, 0.4)
    app.wait_for_timeout(600)
    ids = mat_ids(app)[:4]
    for mid in ids:
        x, y = hover_point(app, mid)
        app.mouse.move(x, y, steps=3)
        app.wait_for_timeout(30)
    app.wait_for_timeout(500)
    assert app.evaluate('document.querySelectorAll("#overlay .peek").length') == 1
    title = app.evaluate('document.querySelector("#overlay .peek .t").textContent')
    last = app.evaluate(f'window.__t.nodes().find(n => n.id === "{ids[-1]}")') and app.evaluate(
        f'''() => [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === "{ids[-1]}").__data__.lines.join(' ')''')
    assert title.rstrip('…') and last.startswith(title.rstrip('…'))


def test_tanpa_peek_di_perangkat_sentuh(browser):
    ctx = browser.new_context(viewport={'width': 1280, 'height': 860}, has_touch=True, is_mobile=True)
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    ready(page)
    zoom_to(page, 0.4)
    page.wait_for_timeout(600)
    mid = mat_ids(page)[0]
    page.evaluate('''id => { const el = [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === id);
      el.dispatchEvent(new MouseEvent('mouseenter')); }''', mid)
    page.wait_for_timeout(400)
    assert page.evaluate('''() => { const g = document.querySelector('#overlay .peek'); return !g || getComputedStyle(g).display === 'none'; }''')
    ctx.close()


def test_reduced_motion_langsung(browser):
    ctx = browser.new_context(viewport={'width': 1280, 'height': 860}, reduced_motion='reduce')
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    ready(page)
    zoom_to(page, 0.3)
    g = page.evaluate(GEOM, mat_ids(page)[0])
    assert (g['w'], g['r']) == (18, 7.5)
    ctx.close()


def test_garis_menempel_ke_titik(app):
    ready(app)
    zoom_to(app, 0.3)
    app.wait_for_timeout(600)
    gap = app.evaluate('''() => {
      const out = [];
      for (const p of document.querySelectorAll('#links path')) {
        const l = p.__data__; if (l.target.kind !== 'mat') continue;
        const end = p.getAttribute('d').trim().split(/[ ,]/).slice(-2).map(Number);
        out.push(Math.abs(end[0] - (l.target.x - 9)));
      }
      return Math.max(...out);
    }''')
    assert gap < 0.5
