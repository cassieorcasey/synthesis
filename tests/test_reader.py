from test_files_store import open_materi, seed

MD = '# Bab 1\n\n- satu\n- dua\n\n[situs](https://example.com)'


def card(page, sid):
    return f'#panel article.src[data-src-id="{sid}"]'


def test_file_card_shows_name_and_size(app):
    sid = seed(app, 'Determinan', 'catatan-aljabar.md', '# Aljabar')
    open_materi(app, 'Determinan')
    c = card(app, sid)
    assert app.get_attribute(c, 'data-kind') == 'berkas'
    assert 'catatan-aljabar.md · 9 B' in app.inner_text(c)


def test_read_markdown_renders_and_toggles(app):
    sid = seed(app, 'Determinan', 'bab1.md', MD)
    open_materi(app, 'Determinan')
    app.click(f'{card(app, sid)} [data-act="read"]')
    app.wait_for_selector(f'{card(app, sid)} .reader h1')
    assert app.inner_text(f'{card(app, sid)} .reader h1') == 'Bab 1'
    assert app.locator(f'{card(app, sid)} .reader li').count() == 2
    a = app.locator(f'{card(app, sid)} .reader a')
    assert a.get_attribute('target') == '_blank' and 'noopener' in a.get_attribute('rel')
    app.click(f'{card(app, sid)} [data-act="read"]')
    assert app.locator(f'{card(app, sid)} .reader').count() == 0


def test_markdown_sanitized(app):
    bad = '<img src=x onerror="window.__pwned=1">\n\n[x](javascript:window.__pwned=2)\n\n<script>window.__pwned=3</script>'
    sid = seed(app, 'Determinan', 'jahat.md', bad)
    open_materi(app, 'Determinan')
    app.click(f'{card(app, sid)} [data-act="read"]')
    app.wait_for_selector(f'{card(app, sid)} .reader')
    app.wait_for_timeout(300)
    assert app.evaluate('window.__pwned') is None
    assert app.locator(f'{card(app, sid)} .reader script').count() == 0
    assert app.evaluate(f"[...document.querySelectorAll('{card(app, sid)} .reader a')].every(a => !/^javascript:/i.test(a.getAttribute('href') || ''))")


def test_pdf_opens_new_tab(app):
    sid = seed(app, 'Determinan', 'modul.pdf', '%PDF-1.4 kecil')
    open_materi(app, 'Determinan')
    with app.context.expect_page() as info:
        app.click(f'{card(app, sid)} [data-act="open-file"]')
    assert info.value.url.startswith('blob:')


def test_other_file_downloads(app):
    sid = seed(app, 'Determinan', 'tugas.docx', 'x')
    open_materi(app, 'Determinan')
    btn = app.locator(f'{card(app, sid)} [data-act="download-file"]')
    assert btn.inner_text().strip() == 'Unduh'
    with app.expect_download() as d:
        btn.click()
    assert d.value.suggested_filename == 'tugas.docx'


def test_search_finds_file_name(app):
    sid = seed(app, 'Vektor', 'ringkasan-vektor-ui.md', '# v')
    app.fill('#q', 'ringkasan-vektor')
    app.wait_for_selector(f'#side-list [data-src="{sid}"]')
    assert 'undefined' not in app.inner_text('#side-list')


def test_note_cannot_trigger_app_actions(app):
    victim = seed(app, 'Determinan', 'korban.md', '# korban')
    bad = (f'<a data-act="delete">Lihat jawaban</a>\n\n'
           f'<button data-act="src-delete" data-id="{victim}">klik</button>\n\n'
           f'<p style="position:fixed;inset:0">overlay</p>')
    sid = seed(app, 'Determinan', 'jebakan.md', bad)
    open_materi(app, 'Determinan')
    app.click(f'{card(app, sid)} [data-act="read"]')
    app.wait_for_selector(f'{card(app, sid)} .reader.md')
    reader = f'{card(app, sid)} .reader'
    assert app.locator(f'{reader} [data-act]').count() == 0
    assert app.locator(f'{reader} [style]').count() == 0
    assert app.locator(f'{reader} button').count() == 0
    app.click(f'{reader} >> text=Lihat jawaban')
    app.click(f'{reader} >> text=Lihat jawaban')
    app.wait_for_timeout(300)
    assert app.locator('#panel h2:has-text("Determinan")').count() == 1
    assert app.locator(card(app, victim)).count() == 1
