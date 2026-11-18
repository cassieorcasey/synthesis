from test_files_store import open_materi


def start_upload(page, materi='Determinan'):
    open_materi(page, materi)
    page.click('#panel [data-act="src-add"] >> nth=0')
    page.check('#srcform input[name="mode"][value="berkas"]', force=True)


def pick(page, name, data, mime='text/markdown'):
    page.set_input_files('#srcform input[name="berkas"]', files=[{'name': name, 'mimeType': mime, 'buffer': data}])


def test_upload_md_creates_source(app):
    start_upload(app)
    pick(app, 'catatan-aljabar.md', b'# Aljabar')
    assert app.input_value('#srcform input[name="judul"]') == 'catatan aljabar'
    app.click('#srcform button[type="submit"]')
    app.wait_for_selector('#panel .src:has-text("catatan aljabar")')
    keys = app.evaluate('[...window.__t.files.keys()]')
    assert len(keys) == 1 and keys[0].startswith('demo/') and keys[0].endswith('/catatan-aljabar.md')
    row = app.evaluate("JSON.parse(localStorage.getItem('synthesis:demo:v1')).src.find(s => s.berkas_nama)")
    assert row['jenis'] == 'catatan' and row['url'] is None and row['berkas_ukuran'] == 9


def test_upload_too_big_rejected(app):
    start_upload(app)
    pick(app, 'besar.pdf', b'0' * 26214401, 'application/pdf')
    app.click('#srcform button[type="submit"]')
    assert app.inner_text('#srcform [data-err="berkas"]') == 'Ukuran file maksimal 25 MB.'
    assert app.evaluate('window.__t.files.size') == 0


def test_upload_requires_file(app):
    start_upload(app)
    app.click('#srcform button[type="submit"]')
    assert app.inner_text('#srcform [data-err="berkas"]') == 'Pilih file dulu.'


def test_failed_save_cleans_object(app):
    start_upload(app)
    pick(app, 'a.md', b'# a')
    app.evaluate('window.__t.failNextSave()')
    app.click('#srcform button[type="submit"]')
    app.wait_for_selector('.toast:has-text("Gagal")')
    assert app.evaluate('window.__t.files.size') == 0
    assert app.locator('#panel .src:has-text("a.md")').count() == 0


def test_edit_file_source_keeps_file(app):
    sid = app.evaluate("window.__t.seed('Determinan', 'lama.md', '# x')")
    open_materi(app, 'Determinan')
    app.click(f'[data-act="src-edit"][data-id="{sid}"]')
    assert app.locator('#srcform input[name="mode"]').count() == 0
    app.fill('#srcform input[name="judul"]', 'Judul baru')
    app.click('#srcform button[type="submit"]')
    app.wait_for_selector('#panel .src:has-text("Judul baru")')
    row = app.evaluate(f"JSON.parse(localStorage.getItem('synthesis:demo:v1')).src.find(s => s.id === '{sid}')")
    assert row['berkas_path'] and row['url'] is None and row['berkas_nama'] == 'lama.md'


def test_demo_without_testfiles_disables_berkas(demo):
    open_materi(demo, 'Determinan')
    demo.click('#panel [data-act="src-add"] >> nth=0')
    assert demo.is_disabled('#srcform input[name="mode"][value="berkas"]')
    assert 'Unggah file butuh login' in demo.inner_text('#srcform')
