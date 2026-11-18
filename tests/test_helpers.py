def ev(page, js):
    return page.evaluate(f'(() => {{ const t = window.__t; return {js}; }})()')


def test_safe_file_name_cleans_accents_and_spaces(app):
    assert ev(app, "t.safeFileName('Catatan Aljabar Ü #1.md')") == 'Catatan-Aljabar-U-1.md'


def test_safe_file_name_limits_length_and_keeps_extension(app):
    name = ev(app, "t.safeFileName('a'.repeat(200) + '.pdf')")
    assert len(name) <= 80 and name.endswith('.pdf')


def test_safe_file_name_fallback(app):
    assert ev(app, "t.safeFileName('???')") == 'berkas'


def test_file_jenis(app):
    assert ev(app, "t.fileJenis('x.PDF', '')") == 'pdf'
    assert ev(app, "t.fileJenis('n.md', '')") == 'catatan'
    assert ev(app, "t.fileJenis('n', 'text/plain')") == 'catatan'
    assert ev(app, "t.fileJenis('a.docx', '')") == 'berkas'


def test_fmt_size(app):
    assert ev(app, "t.fmtSize(512)") == '512 B'
    assert ev(app, "t.fmtSize(1536)") == '1,5 KB'
    assert ev(app, "t.fmtSize(3.4 * 1048576)") == '3,4 MB'


def test_check_file(app):
    assert ev(app, "t.checkFile({name: 'a', size: 0})") == 'File ini kosong.'
    assert ev(app, "t.checkFile({name: 'a', size: 26214401})") == 'Ukuran file maksimal 25 MB.'
    assert ev(app, "t.checkFile({name: 'a', size: 10})") is None
    assert ev(app, "t.MAX_FILE") == 26214400


def test_title_from_file(app):
    assert ev(app, "t.titleFromFile('rumus_cepat-SPLTV.final.md')") == 'rumus cepat SPLTV.final'


def test_object_path(app):
    assert ev(app, "t.objectPath('u1', 's1', 'Bab 1.pdf')") == 'u1/s1/Bab-1.pdf'
