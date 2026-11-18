import os, subprocess, uuid, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = os.environ.get('PGPORT_TEST', '5499')


def psql(db, sql):
    return subprocess.run(['su', 'postgres', '-c', f'psql -X -q -p {PORT} -d {db} -v ON_ERROR_STOP=1'],
                          input=sql, text=True, capture_output=True)


def fresh_db():
    name = 'synth_' + uuid.uuid4().hex[:8]
    subprocess.run(['su', 'postgres', '-c', f'createdb -p {PORT} {name}'], check=True)
    return name


def drop_db(name):
    subprocess.run(['su', 'postgres', '-c', f'dropdb -p {PORT} {name}'], check=False)


def test_schema_upload():
    schema = (ROOT / 'schema.sql').read_text()
    script = (ROOT / 'tests' / 'schema_upload.sql').read_text().replace('-- @SCHEMA@', schema)
    db = fresh_db()
    try:
        r = psql(db, script)
        assert r.returncode == 0, r.stderr
    finally:
        drop_db(db)


def test_schema_idempotent():
    schema = (ROOT / 'schema.sql').read_text()
    stub = (ROOT / 'tests' / 'schema_upload.sql').read_text().split('-- @SCHEMA@')[0]
    db = fresh_db()
    try:
        r = psql(db, stub + schema + schema)
        assert r.returncode == 0, r.stderr
    finally:
        drop_db(db)


def test_schema_upgrade_from_v11():
    """schema.sql v1.1 (sudah dijalankan pengguna, ada data) lalu v1.2 di atasnya."""
    old = subprocess.run(['git', '-C', str(ROOT), 'show', '00804b6:schema.sql'],
                         capture_output=True, text=True, check=True).stdout
    schema = (ROOT / 'schema.sql').read_text()
    stub = (ROOT / 'tests' / 'schema_upload.sql').read_text().split('-- @SCHEMA@')[0]
    seed = """
insert into auth.users values ('00000000-0000-0000-0000-00000000000a');
insert into public.peta_kategori (id, user_id, nama) values ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a', 'K');
insert into public.peta_materi (id, user_id, kategori_id, judul) values ('20000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a', '10000000-0000-0000-0000-000000000001', 'M');
insert into public.peta_sumber (user_id, materi_id, jenis, url) values ('00000000-0000-0000-0000-00000000000a', '20000000-0000-0000-0000-000000000001', 'youtube', 'https://youtu.be/x');
"""
    check = "do $$ begin assert (select count(*) from public.peta_sumber where url = 'https://youtu.be/x') = 1; end $$;"
    db = fresh_db()
    try:
        r = psql(db, stub + old + seed + schema + check)
        assert r.returncode == 0, r.stderr
    finally:
        drop_db(db)
