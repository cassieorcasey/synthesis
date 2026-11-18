# Unggah materi sendiri (PDF, MD, dan file lain): desain

Status: menunggu persetujuan. Belum ada kode yang ditulis.

## Maksud

Sumber belajar di Synthesis sekarang hanya berupa link. Catatan dan file milik sendiri
(Markdown buatan sendiri, PDF, dan jenis lain) ada di perangkat, bukan di internet, jadi
tidak bisa ditempel sebagai link. Fitur ini membuat file bisa diunggah ke sebuah materi dan
muncul sebagai sumber biasa di panel, lalu dibaca di dalam app.

## Tujuan

- Unggah file dari perangkat ke sebuah materi, lewat form sumber yang sudah ada.
- Markdown dibaca langsung di panel, tampil rapi.
- PDF dibuka di tab baru (pembaca bawaan browser).
- File jenis lain bisa diunduh.
- File hanya terlihat oleh akunnya sendiri.

## Bukan tujuan

- Mencari isi file lewat kotak pencarian (hanya judul, kelompok, dan nama file yang dicari).
- Mengedit Markdown di dalam app.
- Pembaca PDF buatan sendiri di panel.
- Mengganti isi file yang sudah diunggah (hapus lalu unggah ulang).
- Berbagi file ke orang lain.

## Batasan

- Satu file HTML tanpa build. Pustaka baru hanya dari CDN dengan versi dipatok.
- Supabase paket gratis: batas global 50 MB per file (dokumentasi Supabase, Storage file limits).
  Kuota total Storage belum diverifikasi.
- Tabel berbagi project dengan StudyO; skema tidak boleh menyentuh tabel StudyO.
- Mode contoh (`?demo`) menyimpan data di localStorage, tidak cocok untuk file.

## Pendekatan yang dipertimbangkan

- **A. Supabase Storage + metadata di `peta_sumber` (dipilih).** File di bucket privat,
  tabel menyimpan jalur dan metadata. File besar tidak membebani database. Butuh satu
  langkah setup (bucket dan aturan akses), dijalankan lewat `schema.sql`.
- **B. Markdown sebagai teks di database, sisanya ke Storage.** Memungkinkan edit dan pencarian
  nanti, tetapi dua jalur penyimpanan. Ditolak untuk sekarang.
- **C. Semua file di database.** Database 500 MB dipakai bersama StudyO dan Wishmap. Ditolak.

## Rancangan (pendekatan A)

### Skema (schema.sql v1.2, idempoten)

- Bucket privat `peta-berkas`, batas 25 MB per file (keputusan saya, di bawah batas Supabase).
- Jalur objek: `<user_id>/<id_sumber>/<nama-file-aman>`.
- Aturan akses `storage.objects`: pengguna login hanya boleh membaca, menulis, dan menghapus
  objek di bucket itu yang folder pertamanya sama dengan `auth.uid()`.
- `peta_sumber` mendapat kolom `berkas_path`, `berkas_nama`, `berkas_tipe`, `berkas_ukuran`.
  Kolom `url` boleh kosong dengan syarat: `url` terisi dan berawalan http(s), atau `berkas_path` terisi.
- `jenis` ditambah dua nilai: `catatan` (md, txt) dan `berkas` (jenis lain). File PDF memakai `pdf`.

### Alur unggah

1. Form sumber mendapat pilihan "Link | Berkas". Pilihan Berkas menampilkan pemilih file
   (dan area seret-lepas).
2. Validasi di klien: ukuran maksimal 25 MB, nama file dibersihkan. Judul terisi dari nama file
   tanpa ekstensi, bisa diubah.
3. Unggah ke Storage lebih dulu, lalu simpan baris `peta_sumber`. Jika penyimpanan baris gagal,
   objek yang baru terunggah dihapus lagi.
4. Menghapus sumber, atau menghapus materi, ikut menghapus objek di bucket.

### Tampilan dan baca

- Kartu sumber file: ikon menurut jenis, judul, "nama-file.ext · ukuran".
- Markdown: tombol "Baca" membuka isinya di dalam kartu (area gulir). Dirender dengan
  `marked` dan dibersihkan dengan `DOMPurify`, keduanya dimuat dari CDN saat pertama dipakai.
  Gambar dengan jalur relatif tidak didukung. Link di dalamnya dibuka di tab baru.
- PDF: tautan bertanda tangan (berlaku 1 jam) dibuka di tab baru.
- File lain: unduh lewat tautan bertanda tangan.

### Mode contoh

Pilihan Berkas dinonaktifkan dengan keterangan bahwa unggah butuh login.

### Keamanan

- Bucket privat, akses hanya lewat tautan bertanda tangan.
- Markdown selalu disanitasi sebelum ditampilkan; file HTML tidak pernah dirender, hanya diunduh.
- Nama file dibersihkan sebelum jadi bagian jalur objek.

## Keputusan saya (bisa dikoreksi)

- Jenis yang diterima: PDF, MD, TXT, gambar, DOCX; jenis lain tetap bisa diunggah sebagai unduhan.
- Batas 25 MB per file.
- Mengganti isi file tidak ada di v1.
- Pengujian: fungsi murni diuji langsung; alur di browser diuji dengan penyimpanan tiruan karena
  Supabase tidak terjangkau dari lingkungan kerja ini. Uji nyata ke Storage dilakukan kamu
  setelah menjalankan `schema.sql`.

## Diserahkan ke pembangun

Bentuk visual kartu dan area baca, ikon, teks pesan galat.
