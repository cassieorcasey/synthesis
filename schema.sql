-- Synthesis · skema Supabase v1
-- Jalankan sekali di Supabase → SQL Editor, di project StudyO (bukan Wishmap).
-- Aman dijalankan ulang. Tidak menyentuh tabel StudyO (categories, sessions, settings, active_timer).
--
-- Model: pohon murni.
--   peta_kategori : kategori bersarang bebas lewat parent_id (Matematika → Aljabar → ...)
--   peta_materi   : materi, selalu di dalam satu kategori (level mana pun)
--   peta_sumber   : link belajar per materi (youtube | web | pdf | lainnya)

create extension if not exists pgcrypto;

-- updated_at otomatis untuk semua tabel
create or replace function public.peta_touch() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

-- ───────────────────────── kategori ─────────────────────────
create table if not exists public.peta_kategori (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
  parent_id   uuid references public.peta_kategori(id) on delete restrict,
  nama        text not null check (length(trim(nama)) > 0),
  warna       text,   -- null = ikut warna induk
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint peta_kategori_no_self check (parent_id is null or parent_id <> id)
);
create index if not exists peta_kategori_user_idx   on public.peta_kategori (user_id);
create index if not exists peta_kategori_parent_idx on public.peta_kategori (parent_id);

alter table public.peta_kategori drop constraint if exists peta_kategori_warna_check;
alter table public.peta_kategori add constraint peta_kategori_warna_check check (
  warna is null
  or warna in ('pink','orange','yellow','green','teal','blue','indigo','purple')
  or warna ~ '^#[0-9A-Fa-f]{6}$'
);

-- Tolak siklus: kategori tidak boleh berada di dalam keturunannya sendiri
create or replace function public.peta_kategori_check() returns trigger
language plpgsql as $$
begin
  if new.parent_id is not null and exists (
    with recursive leluhur(id, langkah) as (
      select new.parent_id, 0
      union all
      select k.parent_id, l.langkah + 1
      from public.peta_kategori k join leluhur l on k.id = l.id
      where k.parent_id is not null and l.langkah < 64
    )
    select 1 from leluhur where id = new.id
  ) then
    raise exception 'kategori tidak boleh berada di dalam keturunannya sendiri';
  end if;
  return new;
end $$;

drop trigger if exists peta_kategori_check on public.peta_kategori;
create trigger peta_kategori_check before insert or update on public.peta_kategori
for each row execute function public.peta_kategori_check();

drop trigger if exists peta_kategori_touch on public.peta_kategori;
create trigger peta_kategori_touch before update on public.peta_kategori
for each row execute function public.peta_touch();

-- ───────────────────────── materi ─────────────────────────
-- on delete restrict: menghapus kategori yang masih berisi materi ditolak database.
-- App memindahkan isinya ke kategori induk dulu sebelum menghapus.
create table if not exists public.peta_materi (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null default auth.uid() references auth.users(id) on delete cascade,
  kategori_id  uuid not null references public.peta_kategori(id) on delete restrict,
  judul        text not null check (length(trim(judul)) > 0),
  catatan      text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists peta_materi_user_idx     on public.peta_materi (user_id);
create index if not exists peta_materi_kategori_idx on public.peta_materi (kategori_id);

drop trigger if exists peta_materi_touch on public.peta_materi;
create trigger peta_materi_touch before update on public.peta_materi
for each row execute function public.peta_touch();

-- ───────────────────────── sumber ─────────────────────────
create table if not exists public.peta_sumber (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
  materi_id   uuid not null references public.peta_materi(id) on delete cascade,
  jenis       text not null default 'web' check (jenis in ('youtube', 'web', 'pdf', 'lainnya')),
  url         text not null check (url ~* '^https?://'),
  judul       text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
-- v1.1: kelompok sumber dalam satu materi (Penjelasan, Latihan soal, Pembahasan, ...). null = tanpa kelompok.
alter table public.peta_sumber add column if not exists kelompok text;
alter table public.peta_sumber drop constraint if exists peta_sumber_kelompok_check;
alter table public.peta_sumber add constraint peta_sumber_kelompok_check
  check (kelompok is null or length(trim(kelompok)) between 1 and 40);

create index if not exists peta_sumber_user_idx   on public.peta_sumber (user_id);
create index if not exists peta_sumber_materi_idx on public.peta_sumber (materi_id);

drop trigger if exists peta_sumber_touch on public.peta_sumber;
create trigger peta_sumber_touch before update on public.peta_sumber
for each row execute function public.peta_touch();

-- ─────────────────── Row Level Security ───────────────────
-- Setiap akun hanya melihat dan mengubah barisnya sendiri,
-- dan hanya boleh menempel ke induk miliknya sendiri.
alter table public.peta_kategori enable row level security;
alter table public.peta_materi   enable row level security;
alter table public.peta_sumber   enable row level security;

-- Pengecek kepemilikan induk. security definer supaya policy kategori
-- tidak membaca tabelnya sendiri lewat RLS (itu memicu rekursi tak hingga).
create or replace function public.peta_milik_kategori(kid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.peta_kategori where id = kid and user_id = auth.uid())
$$;
create or replace function public.peta_milik_materi(mid uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.peta_materi where id = mid and user_id = auth.uid())
$$;
revoke all on function public.peta_milik_kategori(uuid), public.peta_milik_materi(uuid) from public;
grant execute on function public.peta_milik_kategori(uuid), public.peta_milik_materi(uuid) to authenticated;

drop policy if exists "peta_kategori: milik sendiri" on public.peta_kategori;
create policy "peta_kategori: milik sendiri" on public.peta_kategori
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid() and (parent_id is null or public.peta_milik_kategori(parent_id)));

drop policy if exists "peta_materi: milik sendiri" on public.peta_materi;
create policy "peta_materi: milik sendiri" on public.peta_materi
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid() and public.peta_milik_kategori(kategori_id));

drop policy if exists "peta_sumber: milik sendiri" on public.peta_sumber;
create policy "peta_sumber: milik sendiri" on public.peta_sumber
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid() and public.peta_milik_materi(materi_id));

-- ───────────────────── Izin Data API ─────────────────────
grant usage on schema public to authenticated;
grant select, insert, update, delete on public.peta_kategori, public.peta_materi, public.peta_sumber to authenticated;
