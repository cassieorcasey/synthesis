-- Uji skema v1.2 (berkas). Dijalankan oleh tests/test_schema.py di database baru.
-- Stub minimal untuk fitur Supabase yang dipakai schema.sql.
\set ON_ERROR_STOP 1
create schema if not exists auth;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('test.uid', true), '')::uuid $$;
do $$ begin create role authenticated; exception when duplicate_object then null; end $$;
grant usage on schema auth to authenticated;
grant execute on function auth.uid() to authenticated;

create schema storage;
create table storage.buckets (id text primary key, name text not null, public boolean default false,
  file_size_limit bigint, allowed_mime_types text[]);
create table storage.objects (id uuid primary key default gen_random_uuid(), bucket_id text references storage.buckets(id),
  name text not null, owner uuid default auth.uid());
create function storage.foldername(name text) returns text[] language sql immutable as
  $$ select (string_to_array(name, '/'))[1:array_length(string_to_array(name, '/'), 1) - 1] $$;
alter table storage.objects enable row level security;
grant usage on schema storage to authenticated;
grant select, insert, update, delete on storage.objects to authenticated;
create extension if not exists pgcrypto;

-- @SCHEMA@

insert into auth.users values ('00000000-0000-0000-0000-00000000000a'), ('00000000-0000-0000-0000-00000000000b');
insert into public.peta_kategori (id, user_id, nama) values ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a', 'K');
insert into public.peta_materi (id, user_id, kategori_id, judul) values ('20000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a', '10000000-0000-0000-0000-000000000001', 'M');

do $$
declare ok boolean;
begin
  -- sumber berkas tanpa url diterima, jenis baru diterima
  insert into public.peta_sumber (user_id, materi_id, jenis, url, berkas_path, berkas_nama, berkas_tipe, berkas_ukuran)
  values ('00000000-0000-0000-0000-00000000000a', '20000000-0000-0000-0000-000000000001', 'catatan', null,
          '00000000-0000-0000-0000-00000000000a/s/a.md', 'a.md', 'text/markdown', 9);
  insert into public.peta_sumber (user_id, materi_id, jenis, url, berkas_path)
  values ('00000000-0000-0000-0000-00000000000a', '20000000-0000-0000-0000-000000000001', 'berkas', null, 'x/y/z.docx');

  -- url dan berkas_path keduanya kosong ditolak
  ok := false;
  begin
    insert into public.peta_sumber (user_id, materi_id, jenis, url) values ('00000000-0000-0000-0000-00000000000a', '20000000-0000-0000-0000-000000000001', 'web', null);
  exception when check_violation then ok := true; end;
  assert ok, 'sumber tanpa url dan tanpa berkas harus ditolak';

  -- url bukan http(s) ditolak
  ok := false;
  begin
    insert into public.peta_sumber (user_id, materi_id, jenis, url) values ('00000000-0000-0000-0000-00000000000a', '20000000-0000-0000-0000-000000000001', 'web', 'ftp://x');
  exception when check_violation then ok := true; end;
  assert ok, 'url ftp harus ditolak';

  -- jenis asing ditolak
  ok := false;
  begin
    insert into public.peta_sumber (user_id, materi_id, jenis, berkas_path) values ('00000000-0000-0000-0000-00000000000a', '20000000-0000-0000-0000-000000000001', 'video', 'a/b/c');
  exception when check_violation then ok := true; end;
  assert ok, 'jenis asing harus ditolak';

  -- bucket privat dengan batas 25 MB
  assert exists (select 1 from storage.buckets where id = 'peta-berkas' and public = false and file_size_limit = 26214400),
    'bucket peta-berkas privat 25 MB harus ada';
end $$;

-- RLS storage: pengguna A hanya boleh di foldernya sendiri
set role authenticated;
select set_config('test.uid', '00000000-0000-0000-0000-00000000000a', false);
insert into storage.objects (bucket_id, name) values ('peta-berkas', '00000000-0000-0000-0000-00000000000a/s1/a.md');
do $$
declare ok boolean := false;
begin
  begin
    insert into storage.objects (bucket_id, name) values ('peta-berkas', '00000000-0000-0000-0000-00000000000b/s1/a.md');
  exception when insufficient_privilege then ok := true; end;
  assert ok, 'insert ke folder orang lain harus ditolak RLS';
  assert (select count(*) from storage.objects) = 1, 'A harus melihat objeknya sendiri';
end $$;
select set_config('test.uid', '00000000-0000-0000-0000-00000000000b', false);
do $$ begin
  assert (select count(*) from storage.objects) = 0, 'B tidak boleh melihat objek A';
  delete from storage.objects;
end $$;
reset role;
do $$ begin assert (select count(*) from storage.objects) = 1, 'B tidak boleh menghapus objek A'; end $$;
