"""Koreografi panel: arah slide sesuai hierarki, animasi tutup, Study-Flow Stepper, dan FLIP untuk Baca/Putar."""
from conftest import _route, ROOT
from test_semantic_zoom import ready

BODY_CLS = '() => document.querySelector("#panel .panel-body")?.className'


def pick(page, name, focus=False):
    i = page.evaluate(f'window.__t.idByName("{name}")')
    page.evaluate(f'window.__t.select("{i}", {str(focus).lower()})')
    return i


def test_arah_slide_mengikuti_hierarki(app):
    ready(app)
    pick(app, 'Matematika')
    assert 'enter-' not in app.evaluate(BODY_CLS)          # pembukaan awal: panel sendiri yang beranimasi
    pick(app, 'Aljabar')
    assert 'enter-down' in app.evaluate(BODY_CLS)
    pick(app, 'Fungsi Kuadrat')
    assert 'enter-down' in app.evaluate(BODY_CLS)
    app.click('#panel .crumbs button[data-id]')               # crumb pertama = akar
    assert 'enter-up' in app.evaluate(BODY_CLS)
    pick(app, 'Python')
    assert 'enter-fade' in app.evaluate(BODY_CLS)
    app.evaluate('window.__t.refreshNow()')
    assert 'enter-' not in app.evaluate(BODY_CLS)            # render ulang simpul yang sama: diam


def test_tutup_beranimasi_lalu_hidden(app):
    ready(app)
    pick(app, 'Aljabar')
    app.evaluate('window.__t.select(null, false)')
    st = app.evaluate('[document.querySelector("#panel").hidden, document.querySelector("#panel").classList.contains("closing")]')
    assert st == [False, True]
    app.wait_for_function('document.querySelector("#panel").hidden', timeout=1500)
    assert app.evaluate('document.querySelector("#panel").innerHTML') == ''


def test_buka_lagi_saat_menutup(app):
    ready(app)
    pick(app, 'Aljabar')
    app.evaluate('window.__t.select(null, false)')
    app.wait_for_timeout(40)
    pick(app, 'Python')
    app.wait_for_timeout(600)
    st = app.evaluate('''() => { const p = document.querySelector('#panel');
      return [p.hidden, p.classList.contains('closing'), p.querySelector('h2')?.textContent, +getComputedStyle(p).opacity]; }''')
    assert st == [False, False, 'Python', 1]


def test_stepper_alur_belajar(app):
    ready(app)
    pick(app, 'Determinan')
    steps = app.evaluate('''() => [...document.querySelectorAll('#panel nav.flow button')].map(b => b.textContent.replace(/\\s+/g, ' ').trim())''')
    groups = app.evaluate('''() => [...document.querySelectorAll('#panel .grp-h h4:not(.none)')].map(h => h.textContent)''')
    assert len(steps) == len(groups) >= 2
    assert all(g in s for s, g in zip(steps, groups))
    cam = app.evaluate('(t => [t.x, t.y, t.k])(d3.zoomTransform(document.querySelector("#map")))')
    app.click('#panel nav.flow button >> nth=-1')
    app.wait_for_timeout(900)
    res = app.evaluate('''() => { const p = document.querySelector('#panel'), nav = p.querySelector('nav.flow');
      const last = [...p.querySelectorAll('.grp[data-step]')].pop();
      return { cur: [...nav.querySelectorAll('button')].map(b => b.getAttribute('aria-current')),
               gap: last.getBoundingClientRect().top - nav.getBoundingClientRect().bottom, scrolled: p.scrollTop }; }''')
    assert res['cur'][-1] == 'step' and res['cur'].count('step') == 1
    assert res['scrolled'] > 0 or res['gap'] >= 0
    assert -2 <= res['gap'] <= 40 or res['scrolled'] == app.evaluate('(p => p.scrollHeight - p.clientHeight)(document.querySelector("#panel"))')
    assert app.evaluate('(t => [t.x, t.y, t.k])(d3.zoomTransform(document.querySelector("#map")))') == cam


def test_tanpa_stepper_bila_kurang_dua_kelompok(app):
    ready(app)
    pick(app, 'Fungsi Kuadrat')
    assert app.evaluate('document.querySelectorAll("#panel nav.flow").length') == 0


INLINE = '''() => [...document.querySelectorAll('#panel .panel-body *')].filter(e => e.style.transform || e.style.clipPath || e.style.transition || e.style.height).length'''


def test_putar_youtube_flip_tanpa_render_ulang(app):
    ready(app)
    pick(app, 'Determinan')
    app.evaluate('''() => { const p = document.querySelector('#panel'); p.__keepH2 = p.querySelector('h2'); }''')
    app.click('#panel button.thumb')
    info = app.evaluate('''() => { const f = document.querySelector('#panel article.src iframe'); window.__ifr = f;
      return { iframe: !!f, sameH2: document.querySelector('#panel').__keepH2 === document.querySelector('#panel h2') }; }''')
    assert info == {'iframe': True, 'sameH2': True}
    app.wait_for_timeout(700)
    assert app.evaluate('window.__ifr.isConnected && window.__ifr === document.querySelector("#panel article.src iframe")')
    assert app.evaluate(INLINE) == 0


def seed_note(page, materi='Fungsi Kuadrat'):
    text = '# Catatan\\n\\n' + '\\n\\n'.join(f'Paragraf {i} tentang bentuk kuadrat dan grafiknya.' for i in range(14))
    return page.evaluate(f'window.__t.seed("{materi}", "catatan.md", "{text}")')


def test_baca_markdown_flip_mendorong_kartu(app):
    ready(app)
    seed_note(app)
    app.evaluate(f'window.__t.addSrc(window.__t.idByName("Fungsi Kuadrat"), null)')
    pick(app, 'Fungsi Kuadrat')
    app.wait_for_timeout(400)
    btn = app.locator('#panel button[data-act="read"]')
    btn.click()
    app.wait_for_selector('#panel .reader.md', timeout=4000)
    moving = app.evaluate('''() => [...document.querySelectorAll('#panel .panel-body *')].some(e => /translateY/.test(e.style.transform) || e.style.clipPath)''')
    assert moving
    app.wait_for_timeout(700)
    assert app.evaluate(INLINE) == 0
    assert app.evaluate('document.querySelector("#panel button[data-act=read]").textContent') == 'Tutup'
    app.locator('#panel button[data-act="read"]').click()
    app.wait_for_timeout(700)
    assert app.evaluate('document.querySelectorAll("#panel .reader").length') == 0
    assert app.evaluate(INLINE) == 0


def test_reduced_motion(browser):
    ctx = browser.new_context(viewport={'width': 1280, 'height': 860}, reduced_motion='reduce')
    ctx.route('**/*', _route)
    page = ctx.new_page()
    page.goto(f'file://{ROOT}/index.html?demo&testfiles')
    page.wait_for_function('!!window.__t && document.querySelectorAll("g.node").length > 0')
    ready(page)
    pick(page, 'Matematika'); pick(page, 'Aljabar')
    assert 'enter-' not in page.evaluate(BODY_CLS)
    page.evaluate('window.__t.select(null, false)')
    assert page.evaluate('document.querySelector("#panel").hidden')
    pick(page, 'Determinan')
    page.click('#panel button.thumb')
    assert page.evaluate(INLINE) == 0
    ctx.close()
