"""Tata letak pohon kiri-ke-kanan: deterministik, tanpa irisan, induk di tengah anak."""
from conftest import _open

OPEN_ALL = 'window.__t.openAll()'
NODES = 'window.__t.nodes()'


def overlaps(a, b):
    return (abs(a['x'] - b['x']) < (a['w'] + b['w']) / 2 and abs(a['y'] - b['y']) < (a['h'] + b['h']) / 2)


def test_tidak_ada_irisan(app):
    app.evaluate(OPEN_ALL)
    ns = app.evaluate(NODES)
    assert len(ns) > 10
    bad = [(a['id'], b['id']) for i, a in enumerate(ns) for b in ns[i + 1:] if overlaps(a, b)]
    assert bad == []


def test_anak_di_kanan_induk(app):
    app.evaluate(OPEN_ALL)
    ns = {n['id']: n for n in app.evaluate(NODES)}
    anak = [n for n in ns.values() if n['parent']]
    assert anak
    for n in anak:
        p = ns[n['parent']]
        assert n['x'] - n['w'] / 2 > p['x'] + p['w'] / 2, (n['id'], p['id'])


def test_urutan_anak_sesuai_data(app):
    app.evaluate(OPEN_ALL)
    ns = {n['id']: n for n in app.evaluate(NODES)}
    cek = 0
    for pid in [i for i, n in ns.items() if n['parent'] is None or True]:
        urut = app.evaluate('id => window.__t.order(id)', pid)
        if len(urut) < 2:
            continue
        ys = [ns[i]['y'] for i in urut]
        assert ys == sorted(ys), pid
        cek += 1
    assert cek >= 2


def test_induk_di_tengah_anak(app):
    app.evaluate(OPEN_ALL)
    ns = {n['id']: n for n in app.evaluate(NODES)}
    cek = 0
    for pid, p in ns.items():
        urut = app.evaluate('id => window.__t.order(id)', pid)
        if not urut:
            continue
        ys = [ns[i]['y'] for i in urut]
        assert abs(p['y'] - (min(ys) + max(ys)) / 2) < 0.5, pid
        cek += 1
    assert cek >= 2


def test_akar_ditumpuk_di_kolom_pertama(app):
    app.evaluate(OPEN_ALL)
    ns = app.evaluate(NODES)
    akar = sorted([n for n in ns if n['parent'] is None], key=lambda n: n['y'])
    assert len(akar) >= 1
    assert len({round(n['x'] - n['w'] / 2, 1) for n in akar}) == 1


def test_deterministik(browser):
    hasil = []
    for _ in range(2):
        ctx, page = _open(browser, 'demo&testfiles')
        page.wait_for_function('!!window.__t && !!window.__t.nodes')
        page.evaluate(OPEN_ALL)
        # id contoh dibuat acak tiap muat; yang harus sama adalah geometrinya
        hasil.append(sorted((n['x'], n['y'], n['w'], n['h']) for n in page.evaluate(NODES)))
        ctx.close()
    assert hasil[0] == hasil[1]
