"""Regresi audit integrasi Synaptic Focus: hover basi, peek saat klik, impuls di lapisan redup, reduced-motion hidup,
rotasi dengan panel terbuka, log impuls terbatas, stepper diklik beruntun."""
from conftest import _route, ROOT
from test_semantic_zoom import ready, zoom_to, hover_point, mat_ids

NODE = '''id => [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === id)'''
CENTER = f'''id => {{ const r = ({NODE})(id).querySelector('.shape').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }}'''


def test_hover_dilepas_saat_simpulnya_keluar(app):
    ready(app)
    mid = mat_ids(app)[0]
    app.mouse.move(*app.evaluate(CENTER, mid))
    app.wait_for_timeout(120)
    assert app.evaluate('document.querySelector("#map").classList.contains("hovering")')
    kat = app.evaluate(f'window.__t.ancestorsOf("{mid}")')[0]
    app.evaluate(f'window.__t.collapse("{kat}")')
    app.wait_for_timeout(400)
    assert not app.evaluate('document.querySelector("#map").classList.contains("hovering")')
    assert app.evaluate('document.querySelectorAll("#nodes g.node.hot").length') == 0


def test_klik_titik_far_menutup_peek(app):
    ready(app)
    zoom_to(app, 0.35)
    app.wait_for_timeout(600)
    mid = mat_ids(app)[2]
    x, y = hover_point(app, mid)
    app.mouse.move(x, y)
    app.wait_for_timeout(400)
    assert app.evaluate('getComputedStyle(document.querySelector("#overlay .peek")).display') != 'none'
    app.mouse.click(x, y)
    assert app.evaluate('getComputedStyle(document.querySelector("#overlay .peek")).display') == 'none'
    assert app.evaluate(f'({NODE})("{mid}").classList.contains("selected")')


def test_impuls_ikut_lapisan_redup(app):
    ready(app)
    det = app.evaluate('window.__t.idByName("Determinan")')
    app.evaluate(f'window.__t.select(window.__t.idByName("Python"), false)')
    app.wait_for_timeout(300)
    app.evaluate(f'window.__t.addSrc("{det}", null)')
    app.wait_for_timeout(120)
    op = app.evaluate('''() => [...document.querySelectorAll('#impulses polyline')].map(p => +getComputedStyle(p).opacity)''')
    assert op and max(op) <= 0.5


def test_reduced_motion_berubah_di_tengah_sesi(app):
    ready(app)
    app.emulate_media(reduced_motion='reduce')
    app.wait_for_timeout(100)                                             # event 'change' datang di frame berikutnya
    kat = app.evaluate('window.__t.idByName("Aljabar")')
    app.evaluate(f'window.__t.collapse("{kat}")')
    assert not app.evaluate('window.__t.moving()')                       # settle langsung
    assert app.evaluate('document.querySelectorAll("#nodes g.node.exiting").length') == 0   # exit langsung
    app.evaluate('document.querySelector("#zoom-fit").click()')
    assert not app.evaluate('window.__t.camMoving()')                    # kamera instan


def test_log_impuls_terbatas(app):
    ready(app)
    mid = mat_ids(app)[0]
    chain = len(app.evaluate(f'window.__t.ancestorsOf("{mid}")'))
    for _ in range(64 // chain + 4):
        app.evaluate(f'window.__t.addSrc("{mid}", null)')
    app.wait_for_function('document.querySelectorAll("#impulses .impulse").length === 0', timeout=6000)
    assert app.evaluate('window.__t.ripples.length') <= 64


def test_rotasi_membingkai_ulang_simpul_terpilih(browser):
    ctx = browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    ready(page)
    mid = page.evaluate('window.__t.idByName("Determinan")')
    page.evaluate(f'window.__t.select("{mid}")')
    page.wait_for_timeout(1400)
    page.set_viewport_size({'width': 1024, 'height': 700})
    page.wait_for_timeout(1500)
    R = page.evaluate('window.__t.freeRect()')
    cx, cy = page.evaluate(CENTER, mid)
    assert abs(cx - (R['x0'] + R['x1']) / 2) < 3 and abs(cy - (R['y0'] + R['y1']) / 2) < 3
    ctx.close()


def test_stepper_klik_beruntun(app):
    ready(app)
    app.evaluate('window.__t.select(window.__t.idByName("Determinan"), false)')
    app.click('#panel nav.flow button >> nth=-1')
    app.wait_for_timeout(250)
    app.click('#panel nav.flow button >> nth=0')
    app.wait_for_timeout(1100)
    cur = app.evaluate('''() => [...document.querySelectorAll('#panel nav.flow button')].map(b => b.getAttribute('aria-current'))''')
    assert cur[0] == 'step' and cur.count('step') == 1
