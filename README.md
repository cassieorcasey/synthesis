# Synthesis

Peta materi belajar dalam bentuk graf yang bergerak. Kategori bersarang bebas (Matematika → Aljabar Linear → …), materi di dalamnya, dan sumber belajar (YouTube, web, PDF) di panel samping.

## File

- `index.html` berisi seluruh app (D3-force, tanpa build step) dan siap untuk GitHub Pages.
- `schema.sql` berisi tabel `peta_kategori`, `peta_materi`, `peta_sumber` beserta RLS untuk Supabase.

## Setup sekali

Tabel menumpang di project Supabase **StudyO**. Awalan `peta_` membuatnya tidak bentrok dengan tabel StudyO (`categories`, `sessions`, dst.).

1. **SQL Editor** → tempel isi `schema.sql` → Run. Aman dijalankan ulang.
2. **Authentication → URL Configuration → Redirect URLs**: tambahkan `https://cassieorcasey.github.io/synthesis/`. Biarkan *Site URL* tetap milik StudyO.
3. **Authentication → Sign In / Providers**: matikan *Allow new users to sign up*. Akun StudyO yang sudah ada tetap bisa masuk.
4. Repo → **Settings → Pages** → Deploy from branch `main`, folder `/ (root)`.

Login memakai akun StudyO (magic link). Di iPhone, link dari email terbuka di Safari, jadi buka Synthesis dari Safari, atau login dari Safari dulu sebelum menambahkannya ke Home Screen.

## Mode contoh

Tambahkan `?demo` di URL untuk mencoba dengan data contoh. Data mode ini tersimpan di browser saja dan tidak menyentuh Supabase.

## Cara pakai

- **Klik kategori** untuk membuka cabangnya. Klik lagi saat terpilih untuk melipatnya. Lingkaran putus-putus dan tanda + menandakan cabang yang masih terlipat.
- **Klik materi** untuk membuka panel sumber. Video YouTube bisa diputar langsung di panel, dan link `?t=` ikut menentukan detik mulai.
- **Tambah sumber**: tempel link, lalu jenis dan judul terisi otomatis bila bisa.
- **Kelompok sumber**: beri kelompok seperti Penjelasan, Latihan soal, atau Pembahasan. Panel lalu menampilkan sumber per kelompok, dan tombol "+ Tambah" di tiap kelompok langsung mengisi kelompoknya.
- **Jadikan subkategori**: kalau satu materi ternyata perlu dipecah menjadi sub-topik, tombol ini mengubahnya menjadi subkategori di tempat yang sama. Sumber dan catatannya pindah ke materi pertama di dalamnya (default "Pengantar").
- **Cari** dengan tombol `/` di laptop. Pencarian mencakup kategori, materi, dan judul sumber.
- **Hapus subkategori**: isinya naik ke induknya. Kategori utama hanya bisa dihapus kalau sudah kosong.
- Materi berbentuk lingkaran pudar artinya belum punya sumber.

## Model data

| Tabel | Isi |
|---|---|
| `peta_kategori` | `nama`, `parent_id` (null = kategori utama), `warna` (null = ikut induk) |
| `peta_materi` | `judul`, `catatan`, `kategori_id` |
| `peta_sumber` | `url`, `judul`, `jenis` (`youtube` / `web` / `pdf` / `lainnya`), `kelompok` (opsional), `materi_id` |

Database menolak siklus antar-kategori, menolak penghapusan kategori yang masih berisi, dan menghapus sumber bersama materinya.
