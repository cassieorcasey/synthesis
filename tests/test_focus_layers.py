"""Fokus kognitif 3 lapis (in-lineage / is-sibling / is-distant) dan kamera asimetris ke pusat freeRect."""
from conftest import _open, _route, ROOT
from test_semantic_zoom import ready

LAYERS = '''() => {
  const out = {};
  for (const e of document.querySelectorAll('#nodes g.node')) {
    const c = e.classList;
    out[e.__data__.id] = c.contains('in-lineage') ? 'L' : c.contains('is-sibling') ? 'S' : c.contains('is-distant') ? 'D' : '-';
  }
  return out;
}'''
CENTER = '''id => { const e = [...document.querySelectorAll('#nodes g.node')].find(x => x.__data__.id === id).querySelector('.shape').getBoundingClientRect();
  return [e.x + e.width / 2, e.y + e.height / 2]; }'''


def sel(page, name):
    i = page.evaluate(f'window.__t.idByName("{name}")')
    page.evaluate(f'window.__t.select("{i}")')
    return i


def camera_done(page):
    page.wait_for_timeout(120)          # focusNode dijadwalkan 60 ms setelah select
    page.wait_for_function('!window.__t.camMoving()', timeout=4000)
    page.wait_for_timeout(380)


def test_lapisan_saat_materi_dipilih(app):
    ready(app)
    mid = sel(app, 'Determinan')
    app.wait_for_timeout(500)
    lay = app.evaluate(LAYERS)
    anc = app.evaluate(f'window.__t.ancestorsOf("{mid}")')
    nodes = app.evaluate('window.__t.nodes()')
    parent = next(n['parent'] for n in nodes if n['id'] == mid)
    for n in nodes:
        want = 'L' if n['id'] == mid or n['id'] in anc else 'S' if n['parent'] == parent else 'D'
        assert lay[n['id']] == want, n
    op = app.evaluate('''() => Object.fromEntries(['in-lineage', 'is-sibling', 'is-distant'].map(k =>
      [k, +getComputedStyle(document.querySelector('#nodes g.node.' + k)).opacity]))''')
    assert op == {'in-lineage': 1, 'is-sibling': 0.62, 'is-distant': 0.26}


def test_lapisan_saat_kategori_dipilih(app):
    ready(app)
    kid = sel(app, 'Aljabar Linear')
    lay = app.evaluate(LAYERS)
    nodes = {n['id']: n for n in app.evaluate('window.__t.nodes()')}
    kids = [i for i, n in nodes.items() if n['parent'] == kid]
    assert kids and all(lay[i] == 'L' for i in kids)
    sibs = [i for i, n in nodes.items() if n['parent'] == nodes[kid]['parent'] and i != kid]
    assert sibs and all(lay[i] == 'S' for i in sibs)
    assert lay[app.evaluate('window.__t.idByName("Pemrograman")')] == 'D'


def test_hover_tanpa_seleksi_tidak_meredupkan(app):
    ready(app)
    box = app.locator('g.node.mat .shape').first.bounding_box()
    app.mouse.move(box['x'] + 10, box['y'] + box['height'] / 2)
    app.wait_for_timeout(100)
    assert set(app.evaluate(LAYERS).values()) == {'-'}


def test_skala_di_body_tidak_menggeser_pusat(app):
    ready(app)
    target = app.evaluate('window.__t.idByName("Python")')
    app.evaluate('window.__t.panTo(0, 0, 1)')
    app.evaluate('window.__t.fitNow()')
    before = app.evaluate(CENTER, target)
    app.evaluate(f'window.__t.select(window.__t.idByName("Determinan"), false)')
    app.wait_for_timeout(500)
    info = app.evaluate(f'''id => {{ const e = [...document.querySelectorAll('#nodes g.node')].find(x => x.__data__.id === id);
      return [e.getAttribute('transform'), getComputedStyle(e.querySelector('.body')).transform, e.classList.contains('is-distant')]; }}''', target)
    assert info[2] and info[0].startswith('translate(') and 'scale' not in info[0]
    assert info[1].startswith('matrix(0.96')
    after = app.evaluate(CENTER, target)
    assert abs(after[0] - before[0]) < 1 and abs(after[1] - before[1]) < 1


def test_garis_aktif_mengalir_dari_akar(app):
    ready(app)
    mid = sel(app, 'Determinan')
    camera_done(app)
    flow = app.evaluate('''() => [...document.querySelectorAll('#links path.flow')].map(p => p.__data__.target.id)''')
    chain = [mid] + app.evaluate(f'window.__t.ancestorsOf("{mid}")')
    assert flow and set(flow) <= set(chain) and mid in flow
    assert app.evaluate('getComputedStyle(document.querySelector("#links path.flow")).animationName') == 'flow'


def test_kamera_ke_pusat_area_bebas_desktop(app):
    ready(app)
    mid = sel(app, 'Determinan')
    camera_done(app)
    R = app.evaluate('window.__t.freeRect()')
    assert app.evaluate('!document.querySelector("#panel").hidden')
    assert R['x1'] < 1280 - 392
    cx, cy = app.evaluate(CENTER, mid)
    assert abs(cx - (R['x0'] + R['x1']) / 2) < 3 and abs(cy - (R['y0'] + R['y1']) / 2) < 3


def phone(browser, **kw):
    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True, **kw)
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    return ctx, page


def test_kamera_bottom_sheet_ponsel(browser):
    ctx, page = phone(browser)
    ready(page)
    kid = sel(page, 'Aljabar')
    camera_done(page)
    R = page.evaluate('window.__t.freeRect()')
    top = page.evaluate('document.querySelector("#panel").getBoundingClientRect().top')
    assert R['y1'] <= top - 8
    cx, cy = page.evaluate(CENTER, kid)
    assert abs(cx - (R['x0'] + R['x1']) / 2) < 3 and abs(cy - (R['y0'] + R['y1']) / 2) < 3
    op = page.evaluate('+getComputedStyle(document.querySelector("#nodes g.node.is-distant")).opacity')
    assert op >= 0.4
    ctx.close()


def test_gestur_membatalkan_kamera(app):
    ready(app)
    sel(app, 'Teori Graf')
    app.wait_for_timeout(150)
    assert app.evaluate('window.__t.camMoving()')
    app.mouse.move(700, 820)
    app.mouse.down()
    app.mouse.move(760, 780, steps=5)
    app.mouse.up()
    assert not app.evaluate('window.__t.camMoving()')
    t1 = app.evaluate('(t => [t.x, t.y, t.k])(d3.zoomTransform(document.querySelector("#map")))')
    app.wait_for_timeout(700)
    t2 = app.evaluate('(t => [t.x, t.y, t.k])(d3.zoomTransform(document.querySelector("#map")))')
    assert t1 == t2


def test_reduced_motion_kamera_instan(browser):
    ctx = browser.new_context(viewport={'width': 1280, 'height': 860}, reduced_motion='reduce')
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    ready(page)
    mid = page.evaluate('window.__t.idByName("Determinan")')
    page.evaluate(f'window.__t.select("{mid}")')
    page.wait_for_timeout(30)
    assert not page.evaluate('window.__t.camMoving()')
    R = page.evaluate('window.__t.freeRect()')
    cx, cy = page.evaluate(CENTER, mid)
    assert abs(cx - (R['x0'] + R['x1']) / 2) < 3 and abs(cy - (R['y0'] + R['y1']) / 2) < 3
    ctx.close()


def test_refresh_mempertahankan_kelas_garis(app):
    ready(app)
    sel(app, 'Determinan')
    camera_done(app)
    before = app.evaluate('''() => [...document.querySelectorAll('#links path')].map(p => p.getAttribute('class'))''')
    app.evaluate('window.__t.refreshNow()')
    after = app.evaluate('''() => [...document.querySelectorAll('#links path')].map(p => p.getAttribute('class'))''')
    assert before == after and any('flow' in c for c in after)
