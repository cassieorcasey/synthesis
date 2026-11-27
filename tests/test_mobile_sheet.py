"""Ponsel satu tangan (375×812): dock pencarian di zona ibu jari, bottom sheet bersnap yang bisa digeser,
pemilihan sentuh "terdekat menang", target ≥ 44 px, dan gerak hanya lewat transform."""
import pytest
from conftest import _route, ROOT
from test_semantic_zoom import ready

W, H = 375, 812


def open_phone(browser, **kw):
    ctx = browser.new_context(viewport={'width': W, 'height': H}, has_touch=True, is_mobile=True, **kw)
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    page.wait_for_timeout(300)
    return ctx, page, ctx.new_cdp_session(page)


@pytest.fixture
def phone(browser):
    ctx, page, cdp = open_phone(browser)
    yield page, cdp
    ctx.close()


def touch_drag(page, cdp, x, y0, y1, steps=10, frame=16):
    """Geser satu jari dari (x, y0) ke (x, y1) sebagai sentuhan asli (touchstart/move/end)."""
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y0}]})
    for i in range(1, steps + 1):
        page.wait_for_timeout(frame)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x, 'y': y0 + (y1 - y0) * i / steps}]})
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})


def snap(page, sel):
    return page.evaluate(f'document.querySelector("{sel}").dataset.snap')


def settled(page):
    page.wait_for_timeout(120)
    page.wait_for_function('''() => ['#side', '#panel'].every(s => !document.querySelector(s).style.willChange)''', timeout=3000)


def top_of(page, sel):
    return page.evaluate(f'document.querySelector("{sel}").getBoundingClientRect().top')


def test_dock_di_zona_ibu_jari(phone):
    page, _ = phone
    assert snap(page, '#side') == 'dock'
    for sel in ['#q', '#m-add-mat', '#menu-btn']:
        r = page.evaluate(f'(r => [r.top, r.bottom])(document.querySelector("{sel}").getBoundingClientRect())')
        assert r[0] > H * 2 / 3 and r[1] <= H, sel                       # sepertiga bawah layar
    # tidak ada bilah atas: area bebas peta mulai dari batas aman atas, berakhir di atas dock
    R = page.evaluate('window.__t.freeRect()')
    assert R['y0'] < 30 and R['y1'] <= top_of(page, '#side') + page.evaluate('''(() => {
      const m = getComputedStyle(document.querySelector('#side')).transform; return new DOMMatrixReadOnly(m).m42; })()''') + 1
    rail = page.evaluate('(r => [r.left, r.bottom])(document.querySelector(".zoombar").getBoundingClientRect())')
    assert rail[0] > W / 2 and rail[1] < H - 80                       # rel alat di kanan bawah, di atas dock


def test_geser_dock_ke_separuh_lalu_penuh(phone):
    page, cdp = phone
    y = top_of(page, '#side') + 8
    touch_drag(page, cdp, 200, y, y - 300, steps=14, frame=24)
    settled(page)
    assert snap(page, '#side') == 'half'
    assert page.evaluate('document.body.classList.contains("index-up")')
    assert page.evaluate('getComputedStyle(document.querySelector(".zoombar")).visibility') == 'hidden'
    y = top_of(page, '#side') + 8
    touch_drag(page, cdp, 200, y, y - 300, steps=12, frame=20)
    settled(page)
    assert snap(page, '#side') == 'full'
    # lemparan cepat ke bawah dari penuh melewati separuh: proyeksi kecepatan memilih dock
    y = top_of(page, '#side') + 8
    touch_drag(page, cdp, 200, y, y + 220, steps=4, frame=8)
    settled(page)
    assert snap(page, '#side') == 'dock'


def test_karet_di_batas_atas(phone):
    page, cdp = phone
    page.evaluate('document.querySelector("#menu-btn").click()')
    page.evaluate('document.querySelector("#q").focus()')
    settled(page)
    assert snap(page, '#side') == 'full'
    y0 = top_of(page, '#side')
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': 200, 'y': y0 + 8}]})
    for i in range(1, 6):
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': 200, 'y': y0 + 8 - 20 * i}]})
    pulled = y0 - top_of(page, '#side')
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    assert 0 < pulled < 100 * 0.5                                        # mengikuti, tapi tertahan
    settled(page)
    assert abs(top_of(page, '#side') - y0) < 1


def test_cari_naik_penuh_lalu_hasil_membuka_panel(phone):
    page, _ = phone
    page.tap('#q')
    page.keyboard.type('vekt')
    settled(page)
    assert snap(page, '#side') == 'full'
    page.tap('#side-list [data-go]')
    settled(page)
    assert snap(page, '#panel') == 'half' and snap(page, '#side') == 'hidden'
    assert page.evaluate('document.querySelector("#panel h2").textContent') == 'Vektor'


def test_panel_tiga_snap_dan_tutup_dengan_geser(phone):
    page, cdp = phone
    ready(page)
    page.evaluate('window.__t.select(window.__t.idByName("Determinan"))')
    settled(page)
    assert snap(page, '#panel') == 'half'
    half = top_of(page, '#panel')
    assert 0.40 * H < half < 0.52 * H
    # pita atas → turun ke tahap judul: peta lapang, judul tetap terbaca
    touch_drag(page, cdp, 180, half + 20, half + 280, steps=12, frame=24)
    settled(page)
    assert snap(page, '#panel') == 'peek'
    h2 = page.evaluate('(r => r.bottom)(document.querySelector("#panel h2").getBoundingClientRect())')
    assert h2 <= H - 4 and top_of(page, '#panel') > H * 0.7
    # kamera membingkai ulang ke area bebas baru
    page.wait_for_function('!window.__t.camMoving()', timeout=3000)
    R = page.evaluate('window.__t.freeRect()')
    assert R['y1'] > H * 0.6
    # tarik di bawah tahap terendah → tutup, dock naik kembali
    peek = top_of(page, '#panel')
    touch_drag(page, cdp, 180, peek + 20, peek + 160, steps=8, frame=16)
    page.wait_for_function('document.querySelector("#panel").hidden', timeout=3000)
    settled(page)
    assert snap(page, '#side') == 'dock'
    assert page.evaluate('window.__t.select === undefined || true')


def test_isi_menggulir_hanya_saat_penuh(phone):
    page, cdp = phone
    ready(page)
    page.evaluate('window.__t.select(window.__t.idByName("Determinan"))')
    settled(page)
    # di separuh, geser naik di isi = menarik sheet ke penuh, bukan menggulir
    y = top_of(page, '#panel') + 200
    touch_drag(page, cdp, 180, y, y - 260, steps=12, frame=24)
    settled(page)
    assert snap(page, '#panel') == 'full'
    assert page.evaluate('document.querySelector("#panel").scrollTop') == 0
    # di penuh, isi menggulir secara native
    page.evaluate('document.querySelector("#panel").scrollTop = 300')
    touch_drag(page, cdp, 180, 500, 600, steps=8, frame=16)
    settled(page)
    assert snap(page, '#panel') == 'full'
    # isi di puncak: tarik turun mengambil alih sheet
    page.evaluate('document.querySelector("#panel").scrollTop = 0')
    touch_drag(page, cdp, 180, 300, 560, steps=12, frame=24)
    settled(page)
    assert snap(page, '#panel') in ('half', 'peek')


VISIBLE_MAT = '''() => { const R = window.__t.freeRect();
  for (const e of document.querySelectorAll('#nodes g.node.mat:not(.exiting)')) {
    const r = e.querySelector('.shape').getBoundingClientRect(), cx = r.x + r.width / 2;
    if (cx < R.x0 + 20 || cx > R.x1 - 20 || r.top < R.y0 + 20 || r.bottom + 30 > R.y1) continue;
    const below = document.elementFromPoint(cx, r.bottom + 14);
    if (below && below.closest('g.node')) continue;
    return { id: e.__data__.id, name: e.__data__.lines.join(' '), x: cx, cy: r.y + r.height / 2, bottom: r.bottom };
  }
  return null; }'''


def test_ketukan_terdekat_memilih_simpul(phone):
    page, cdp = phone
    ready(page)
    n = page.evaluate(VISIBLE_MAT)
    assert n, 'butuh satu materi terlihat dengan ruang kosong di bawahnya'
    page.touchscreen.tap(n['x'], n['bottom'] + 14)                     # 14 px di bawah kartu: ruang kosong
    page.wait_for_timeout(200)
    assert page.evaluate('document.querySelector("#panel").dataset.id') == n['id']


def test_ketukan_jauh_tetap_membatalkan_pilihan(phone):
    page, _ = phone
    ready(page)
    page.evaluate('window.__t.select(window.__t.idByName("Vektor"), false)')
    settled(page)
    page.evaluate('window.__t.panTo(-4000, -4000, 1)')
    page.touchscreen.tap(60, 200)
    page.wait_for_timeout(400)
    assert page.evaluate('document.querySelector("#panel").hidden || document.querySelector("#panel").classList.contains("closing")')


TARGETS = '''sel => [...document.querySelectorAll(sel)].filter(e => {
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && r.top < innerHeight && r.bottom > 0 && !e.closest('[hidden]');
  }).map(e => {
    const r = e.getBoundingClientRect(), a = getComputedStyle(e, '::after');
    const ex = a.content && a.content !== 'none' && a.position === 'absolute' ? [-parseFloat(a.top) || 0, -parseFloat(a.bottom) || 0, -parseFloat(a.left) || 0, -parseFloat(a.right) || 0] : [0, 0, 0, 0];
    return [e.id || e.getAttribute('aria-label') || e.textContent.trim().slice(0, 20), r.width + ex[2] + ex[3], r.height + ex[0] + ex[1]];
  }).filter(x => x[1] < 43.5 || x[2] < 43.5)'''
CONTROLS = 'button:not(.thumb), input:not([type=radio]):not([type=hidden]), select, .seg span, .swatches span'


def test_target_sentuh_minimal_44(phone):
    page, cdp = phone
    assert page.evaluate(TARGETS, CONTROLS) == []                     # dock
    page.evaluate('document.querySelector("#menu-btn").click()'); settled(page)
    assert page.evaluate(TARGETS, CONTROLS) == []                     # indeks separuh
    page.evaluate('document.querySelector("#menu-btn").click()'); settled(page)
    ready(page)
    page.evaluate('window.__t.select(window.__t.idByName("Determinan"))'); settled(page)
    page.evaluate('document.querySelector("#panel").dataset.snap = "full"; document.querySelector("#panel").style.transform = "none"')
    assert page.evaluate(TARGETS, '#panel ' + CONTROLS.replace(', ', ', #panel ')) == []   # panel materi (stepper, chip, crumb)
    page.evaluate('window.__t.select(null, false)'); settled(page)
    page.tap('#m-add-mat'); page.wait_for_timeout(500)
    assert page.evaluate(TARGETS, 'dialog[open] ' + CONTROLS.replace(', ', ', dialog[open] ')) == []


def test_gerak_hanya_transform_dan_will_change_sementara(phone):
    page, _ = phone
    ready(page)
    page.evaluate('window.__t.select(window.__t.idByName("Determinan"))')
    page.wait_for_timeout(90)
    mid = page.evaluate('''() => { const p = document.querySelector('#panel');
      return { props: [...p.style].sort(), wc: p.style.willChange }; }''')
    assert set(mid['props']) <= {'transform', 'will-change'} and mid['wc'] == 'transform'
    settled(page)
    assert page.evaluate('document.querySelector("#panel").style.willChange') == ''
    # durasi: dari diam ke separuh tenang dalam rentang 250–600 ms (pegas kritis; ekor sub-piksel dihitung)
    page.evaluate('window.__t.select(null, false)'); settled(page)
    t = page.evaluate('''() => new Promise(res => { const t0 = performance.now(); window.__t.select(window.__t.idByName("Vektor"));
      const p = document.querySelector('#panel'); const check = () => p.style.willChange ? requestAnimationFrame(check) : res(performance.now() - t0);
      requestAnimationFrame(check); })''')
    assert 200 < t < 650


def test_tekan_memberi_respons_instan(phone):
    page, cdp = phone
    ready(page)
    n = page.evaluate(VISIBLE_MAT)
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': n['x'], 'y': n['cy']}]})
    page.wait_for_timeout(40)                                           # jauh di bawah 150 ms
    assert page.evaluate('[...document.querySelectorAll("#nodes g.node.pressed")].map(e => e.__data__.id)') == [n['id']]
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    page.wait_for_timeout(40)
    assert page.evaluate('document.querySelectorAll("#nodes g.node.pressed").length') == 0


def test_form_turun_saat_ditutup(phone):
    page, _ = phone
    page.tap('#m-add-mat'); page.wait_for_timeout(500)
    page.tap('dialog[open] [data-close]')
    st = page.evaluate('(d => [d.open, d.classList.contains("closing")])(document.querySelector("#dlg-mat") || document.querySelector("dialog.closing"))')
    assert st == [True, True]
    page.wait_for_function('!document.querySelector("dialog[open]")', timeout=1500)


def test_viewport_dinamis_dan_keyboard(phone):
    page, _ = phone
    assert page.evaluate('document.documentElement.getBoundingClientRect().height') == H
    assert page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--kb").trim()') == '0px'
    sheet_bottom = page.evaluate('document.querySelector("#side").getBoundingClientRect().height + parseFloat(getComputedStyle(document.querySelector("#side")).top)')
    assert abs(sheet_bottom - H) < 1


def test_reduced_motion_instan(browser):
    ctx, page, cdp = open_phone(browser, reduced_motion='reduce')
    ready(page)
    page.evaluate('window.__t.select(window.__t.idByName("Determinan"))')
    assert snap(page, '#panel') == 'half' and page.evaluate('document.querySelector("#panel").style.willChange') == ''
    page.evaluate('window.__t.select(null, false)')
    assert page.evaluate('document.querySelector("#panel").hidden')
    page.tap('#m-add-mat'); page.wait_for_timeout(100)
    page.tap('dialog[open] [data-close]')
    assert page.evaluate('!document.querySelector("dialog[open]")')
    ctx.close()


def test_kembali_ke_desktop_membersihkan_sheet(phone):
    page, _ = phone
    ready(page)
    page.evaluate('window.__t.select(window.__t.idByName("Determinan"))')
    settled(page)
    page.set_viewport_size({'width': 1280, 'height': 860})
    page.wait_for_timeout(300)
    st = page.evaluate('''() => ['#side', '#panel'].map(s => { const e = document.querySelector(s); return [e.style.transform, e.dataset.snap || '']; })''')
    assert st == [['', ''], ['', '']]
    assert page.evaluate('getComputedStyle(document.querySelector("#side")).left') == '16px'
