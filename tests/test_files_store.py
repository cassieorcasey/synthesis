def open_materi(page, title):
    page.fill('#q', title)
    page.keyboard.press('Enter')
    page.wait_for_selector(f'#panel h2:has-text("{title}")')


def seed(page, materi, name, text='# isi'):
    return page.evaluate('([m, n, t]) => window.__t.seed(m, n, t)', [materi, name, text])


def test_delete_source_removes_object(app):
    sid = seed(app, 'Determinan', 'catatan.md')
    assert app.evaluate('window.__t.files.size') == 1
    open_materi(app, 'Determinan')
    app.click(f'[data-act="src-edit"][data-id="{sid}"]')
    app.click('[data-act="src-delete"]')
    app.click('[data-act="src-delete"]')
    app.wait_for_function(f'!document.querySelector(\'[data-src-id="{sid}"]\')')
    assert app.evaluate('window.__t.files.size') == 0


def test_delete_materi_removes_objects(app):
    seed(app, 'Vektor', 'a.md')
    seed(app, 'Vektor', 'b.pdf')
    assert app.evaluate('window.__t.files.size') == 2
    open_materi(app, 'Vektor')
    app.click('#panel [data-act="delete"]')
    app.click('#panel [data-act="delete"]')
    app.wait_for_function('window.__t.files.size === 0', timeout=5000)
