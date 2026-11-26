"""Spektrum kesiapan .ico, impuls sinaptik mundur sepanjang garis, dan odometer badge kategori."""
from conftest import _route, ROOT
from test_semantic_zoom import ready, zoom_to

EL = '''id => [...document.querySelectorAll('#nodes g.node')].find(e => e.__data__.id === id)'''


def state(page, mid):
    return page.evaluate(f'''id => {{ const el = ({EL})(id), ico = el.querySelector('.ico'), halo = el.querySelector('.halo');
      return {{ nosrc: el.classList.contains('nosrc'), ripe: el.classList.contains('ripe'),
        dash: getComputedStyle(ico).strokeDasharray, fill: getComputedStyle(ico).fill,
        halo: getComputedStyle(halo).display, haloR: +halo.getAttribute('r'), icoR: +ico.getAttribute('r') }}; }}''', mid)


def empty_mat(page):
    kid = page.evaluate('window.__t.idByName("Aljabar")')
    page.evaluate(f'window.__t.addMat("{kid}", "Materi Uji")')
    page.wait_for_function('!window.__t.moving()')
    return page.evaluate('window.__t.idByName("Materi Uji")')


def test_tiga_tingkat_kesiapan(app):
    ready(app)
    mid = empty_mat(app)
    s = state(app, mid)
    assert s['nosrc'] and not s['ripe'] and s['dash'] != 'none' and s['halo'] == 'none'
    app.evaluate(f'window.__t.addSrc("{mid}", null)')
    s = state(app, mid)
    assert not s['nosrc'] and not s['ripe'] and s['dash'] == 'none' and s['halo'] == 'none'
    app.evaluate(f'window.__t.addSrc("{mid}", null)')
    assert not state(app, mid)['ripe']
    app.evaluate(f'window.__t.addSrc("{mid}", null)')
    s = state(app, mid)
    assert s['ripe'] and s['halo'] != 'none' and s['haloR'] > s['icoR']


def test_dua_kelompok_sudah_matang(app):
    ready(app)
    mid = empty_mat(app)
    app.evaluate(f'window.__t.addSrc("{mid}", "Penjelasan")')
    app.evaluate(f'window.__t.addSrc("{mid}", "penjelasan ")')
    assert not state(app, mid)['ripe']          # kelompok sama (beda huruf/spasi) tetap satu
    app.evaluate(f'window.__t.addSrc("{mid}", "Latihan soal")')
    assert state(app, mid)['ripe']


def test_kesiapan_di_far(app):
    ready(app)
    mid = empty_mat(app)
    for g in ['A', 'B']:
        app.evaluate(f'window.__t.addSrc("{mid}", "{g}")')
    zoom_to(app, 0.3)
    app.wait_for_timeout(600)
    s = state(app, mid)
    assert s['ripe'] and s['icoR'] == 7.5 and s['haloR'] > 9


def test_ripple_merambat_sampai_akar(app):
    ready(app)
    mid = empty_mat(app)
    app.evaluate('window.__t.ripples.length = 0')
    app.evaluate(f'window.__t.addSrc("{mid}", null)')
    app.wait_for_timeout(120)
    flying = app.evaluate('document.querySelectorAll("#impulses .impulse").length')
    assert flying >= 1
    assert app.evaluate('document.querySelector("#impulses .impulse").classList.contains("pos")')
    app.wait_for_function('document.querySelectorAll("#impulses .impulse").length === 0', timeout=4000)
    ticks = app.evaluate('window.__t.ripples.map(r => r.id)')
    chain = app.evaluate(f'window.__t.ancestorsOf("{mid}")')
    assert ticks == list(reversed(chain))         # induk terdekat dulu, akar terakhir
    assert all(app.evaluate('window.__t.ripples.map(r => r.animated)'))


def test_hapus_sumber_pulsa_redup(app):
    ready(app)
    mid = empty_mat(app)
    a = app.evaluate(f'window.__t.addSrc("{mid}", null)')
    app.evaluate(f'window.__t.addSrc("{mid}", null)')
    app.wait_for_timeout(1800)
    assert app.evaluate('document.querySelectorAll("#impulses .impulse").length') == 0
    app.evaluate(f'window.__t.delSrc("{a}")')
    app.wait_for_timeout(100)
    kelas = app.evaluate('[...document.querySelectorAll("#impulses .impulse")].map(e => e.classList.contains("neg"))')
    assert kelas and all(kelas)
    assert not state(app, mid)['nosrc']
    rest = app.evaluate(f'window.__t.srcIds("{mid}")')
    app.evaluate(f'window.__t.delSrc("{rest[0]}")')
    assert state(app, mid)['nosrc']


def test_ripple_dilewati_di_luar_layar(app):
    ready(app)
    mid = empty_mat(app)
    app.evaluate('window.__t.panTo(60000, 60000, 1)')
    app.evaluate('window.__t.ripples.length = 0')
    app.evaluate(f'window.__t.addSrc("{mid}", null)')
    app.wait_for_timeout(80)
    assert app.evaluate('document.querySelectorAll("#impulses .impulse").length') == 0
    assert app.evaluate('window.__t.ripples.length') == len(app.evaluate(f'window.__t.ancestorsOf("{mid}")'))
    assert not any(app.evaluate('window.__t.ripples.map(r => r.animated)'))


def badge(page, kid):
    return page.evaluate(f'''id => {{ const el = ({EL})(id), b = el.querySelector('.badge');
      const roll = b.querySelector('.roll'), clip = roll.getAttribute('clip-path');
      const ref = clip && document.getElementById(clip.slice(5, -1));
      return {{ texts: [...roll.querySelectorAll('text')].map(t => t.textContent), clip: !!ref,
               clipW: ref ? +ref.firstElementChild.getAttribute('width') : 0, w: +b.querySelector('rect').getAttribute('width') }}; }}''', kid)


def test_odometer_berguling_saat_jumlah_berubah(app):
    ready(app)
    kid = app.evaluate('window.__t.idByName("Aljabar")')
    n0 = int(badge(app, kid)['texts'][0])
    app.evaluate(f'window.__t.addMat("{kid}", "Odometer satu")')
    b = badge(app, kid)
    assert b['clip'] and b['clipW'] == b['w']
    assert len(b['texts']) == 2 and b['texts'][-1] == str(n0 + 1)
    app.wait_for_timeout(600)
    assert badge(app, kid)['texts'] == [str(n0 + 1)]


def test_odometer_update_beruntun(app):
    ready(app)
    kid = app.evaluate('window.__t.idByName("Aljabar")')
    n0 = int(badge(app, kid)['texts'][0])
    for i in range(4):
        app.evaluate(f'window.__t.addMat("{kid}", "Cepat {i}")')
        app.wait_for_timeout(40)
    assert len(badge(app, kid)['texts']) <= 2
    app.wait_for_timeout(700)
    assert badge(app, kid)['texts'] == [str(n0 + 4)]


def test_reduced_motion_tanpa_animasi(browser):
    ctx = browser.new_context(viewport={'width': 1280, 'height': 860}, reduced_motion='reduce')
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    ready(page)
    mid = empty_mat(page)
    page.evaluate(f'window.__t.addSrc("{mid}", null)')
    page.wait_for_timeout(50)
    assert page.evaluate('document.querySelectorAll("#impulses .impulse").length') == 0
    assert not state(page, mid)['nosrc']
    kid = page.evaluate('window.__t.idByName("Aljabar")')
    page.evaluate(f'window.__t.addMat("{kid}", "RM")')
    assert len(badge(page, kid)['texts']) == 1
    ctx.close()
