# Unggah Materi Sendiri — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven
> development (recommended) or inline execution to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** File (PDF, MD, dan lainnya) bisa diunggah ke sebuah materi, muncul sebagai sumber, Markdown dibaca di panel, PDF dibuka di tab baru, file lain diunduh.

**Architecture:** File disimpan di bucket privat Supabase Storage `peta-berkas` dengan jalur `<user_id>/<id_sumber>/<nama-aman>`; metadata di kolom baru `peta_sumber`. App mengakses Storage lewat antarmuka `store.files`; mode contoh tidak punya `store.files` (unggah dimatikan), kecuali `?demo&testfiles` yang memakai penyimpanan tiruan di memori untuk pengujian.

**Tech Stack:** HTML tunggal + D3 7.9.0 + supabase-js 2.110.1; baru: marked 18.0.10, DOMPurify 3.4.14 (jsDelivr, dimuat saat pertama dipakai). Tes: pytest + Playwright (Python), Postgres 16 lokal.

**Spec:** `docs/superpowers/specs/2026-11-18-upload-materi-design.md`

## Global Constraints

- Satu file `index.html`, tanpa build. Pustaka hanya dari CDN dengan versi dipatok persis.
- Batas 25 MB per file (`MAX_FILE = 26214400`), sama di app dan di bucket.
- Bucket `peta-berkas`, privat. Jalur objek `<user_id>/<id_sumber>/<nama-aman>`.
- `schema.sql` tetap idempoten dan tidak menyentuh tabel StudyO.
- `jenis` sumber file: `pdf` (PDF), `catatan` (md, markdown, txt), `berkas` (lainnya).
- Markdown selalu lewat DOMPurify sebelum masuk DOM; HTML tidak pernah dirender.
- Teks antarmuka berbahasa Indonesia; tanpa em dash di teks antarmuka.
- Tautan bertanda tangan berlaku 3600 detik.

## Review Focus

1. Penyimpanan baris gagal setelah unggah berhasil → objek dihapus lagi, tidak tertinggal yatim. (Task 4)
2. Menghapus materi yang punya sumber file → semua objeknya ikut terhapus. (Task 3)
3. Nama file beraksen, berspasi, sangat panjang, atau tanpa ekstensi → jalur objek tetap valid. (Task 2)
4. Markdown berisi `<script>`, `onerror`, atau link `javascript:` → tidak dieksekusi. (Task 5)
5. Mode contoh tanpa `testfiles` → pilihan Berkas mati dengan keterangan, tidak melempar galat. (Task 4)

---

### Task 1: Skema v1.2 (bucket, kolom, aturan akses)

**Files:**
- Modify: `schema.sql`
- Create: `tests/schema_upload.sql`, `tests/test_schema.py`

**Interfaces:**
- Produces: kolom `peta_sumber.berkas_path text`, `berkas_nama text`, `berkas_tipe text`, `berkas_ukuran bigint`; `url` nullable; constraint `peta_sumber_isi_check`: `(url is not null and url ~* '^https?://') or berkas_path is not null`; `jenis` ∈ youtube, web, pdf, lainnya, catatan, berkas; baris `storage.buckets` id `peta-berkas`, `public=false`, `file_size_limit=26214400`; 4 policy pada `storage.objects` (select/insert/update/delete) dengan syarat `bucket_id = 'peta-berkas' and (storage.foldername(name))[1] = auth.uid()::text`.

- [ ] **Step 1: Tulis tes yang gagal.** `tests/schema_upload.sql` membuat stub (`auth.uid()` dari setting `test.uid`, `auth.users`, skema `storage` dengan `buckets`, `objects`, `foldername`), menjalankan `schema.sql`, lalu memeriksa dengan `do $$ ... assert ... $$`: baris dengan `url` null + `berkas_path` diterima; keduanya null ditolak; `url = 'ftp://x'` ditolak; `jenis = 'catatan'` diterima; bucket `peta-berkas` ada dengan limit 26214400 dan privat; sebagai role `authenticated` dengan uid A, insert objek `A/…` diterima dan `B/…` ditolak RLS. `tests/test_schema.py::test_schema_upload` menjalankan file itu dengan `psql -v ON_ERROR_STOP=1` ke database baru di port 5499 dan mengharapkan exit 0.
- [ ] **Step 2:** `pytest tests/test_schema.py -q` → Expected: FAIL (kolom/constraint/bucket belum ada).
- [ ] **Step 3:** Tambahkan bagian "v1.2: berkas" ke `schema.sql` sesuai Interfaces. Constraint `jenis` lama dibuang lewat nama default `peta_sumber_jenis_check` lalu dibuat ulang. Bucket lewat `insert … on conflict (id) do update`. Policy lewat `drop policy if exists` + `create policy`.
- [ ] **Step 4:** `pytest tests/test_schema.py -q` → Expected: PASS. Jalankan `schema.sql` dua kali berturut-turut → exit 0 (idempoten).
- [ ] **Step 5:** Commit `Skema v1.2: bucket peta-berkas dan kolom berkas`.

### Task 2: Fungsi bantu file

**Files:**
- Modify: `index.html` (blok skrip, dekat `detectJenis`)
- Create: `tests/conftest.py` (fixture Playwright: route d3, marked, DOMPurify, supabase dari file lokal; halaman `?demo&testfiles`), `tests/test_helpers.py`

**Interfaces:**
- Produces (global di skrip, juga di `window.__t` saat `testfiles`):
  - `MAX_FILE = 26214400`
  - `safeFileName(name: string): string`
  - `fileJenis(name: string, mime: string): 'pdf'|'catatan'|'berkas'`
  - `fmtSize(bytes: number): string`
  - `checkFile(f: {name: string, size: number}): string|null`
  - `titleFromFile(name: string): string`
  - `objectPath(userId: string, srcId: string, name: string): string`

- [ ] **Step 1: Tulis tes yang gagal** (`page.evaluate` ke `window.__t`):
  - `safeFileName('Catatan Aljabar Ü #1.md') == 'Catatan-Aljabar-U-1.md'`
  - `safeFileName('a'*200 + '.pdf')` panjang ≤ 80 dan berakhiran `.pdf`
  - `safeFileName('???') == 'berkas'`
  - `fileJenis('x.PDF','') == 'pdf'`, `fileJenis('n.md','') == 'catatan'`, `fileJenis('n','text/plain') == 'catatan'`, `fileJenis('a.docx','') == 'berkas'`
  - `fmtSize(512) == '512 B'`, `fmtSize(1536) == '1,5 KB'`, `fmtSize(3.4*1048576) == '3,4 MB'`
  - `checkFile({name:'a', size:0}) == 'File ini kosong.'`, `checkFile({name:'a', size:26214401}) == 'Ukuran file maksimal 25 MB.'`, `checkFile({name:'a', size:10}) is None`
  - `titleFromFile('rumus_cepat-SPLTV.final.md') == 'rumus cepat SPLTV.final'`
  - `objectPath('u1','s1','Bab 1.pdf') == 'u1/s1/Bab-1.pdf'`
- [ ] **Step 2:** `pytest tests/test_helpers.py -q` → Expected: FAIL (`window.__t` undefined).
- [ ] **Step 3:** Implementasi. `safeFileName`: NFKD, buang diakritik, karakter di luar `[A-Za-z0-9._-]` jadi `-`, rapatkan `-` berulang, potong `-` di tepi, batasi 80 karakter dengan ekstensi dipertahankan, kosong → `berkas`. `fmtSize` memakai `Intl.NumberFormat('id-ID', {maximumFractionDigits: 1})`.
- [ ] **Step 4:** `pytest tests/test_helpers.py -q` → PASS; `pytest -q` (seluruh suite) → PASS.
- [ ] **Step 5:** Commit `Fungsi bantu nama, jenis, dan ukuran file`.

### Task 3: `store.files` dan pembersihan saat hapus

**Files:**
- Modify: `index.html` (`COLS[T_SRC]`, `LocalStore`, `makeSupabaseStore`, `removeMat`, handler `src-delete`)
- Create: `tests/test_files_store.py`

**Interfaces:**
- Consumes: `objectPath` (Task 2).
- Produces:
  - `COLS[T_SRC]` ditambah `berkas_path, berkas_nama, berkas_tipe, berkas_ukuran`.
  - `store.files: null | { upload(path: string, file: Blob, type: string): Promise<void>, signedUrl(path: string, download?: string): Promise<string>, remove(paths: string[]): Promise<void> }`; Supabase memakai `sb.storage.from('peta-berkas')` (`upload` dengan `upsert:false`, `createSignedUrl(path, 3600, download ? {download} : undefined)`, `remove`). Mode `testfiles`: Map di memori, `signedUrl` mengembalikan `URL.createObjectURL`, diekspos sebagai `window.__t.files` (Map) dan `window.__t.failNextSave()`.
  - `currentUserId(): string` (Supabase: id sesi; testfiles: `'demo'`).
  - `removeSrc(id: string): Promise<void>` — hapus objek (bila ada `berkas_path`) lalu baris.
  - `removeMat` menghapus objek semua sumbernya sebelum baris materi.

- [ ] **Step 1: Tulis tes yang gagal:** `test_delete_source_removes_object` (sisipkan sumber berkas + objek lewat `__t`, klik Hapus dua kali, `__t.files.size == 0`); `test_delete_materi_removes_objects` (dua sumber berkas di satu materi, hapus materi, Map kosong).
- [ ] **Step 2:** `pytest tests/test_files_store.py -q` → FAIL.
- [ ] **Step 3:** Implementasi sesuai Interfaces. Handler `src-delete` memanggil `removeSrc`. Kegagalan hapus objek tidak membatalkan hapus baris; tampilkan toast `File di penyimpanan gagal dihapus.`
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit `Antarmuka store.files dan hapus objek bersama sumbernya`.

### Task 4: Form "Link | Berkas" dan alur unggah

**Files:**
- Modify: `index.html` (`srcFormHTML`, `wireSrcForm`, CSS form)
- Create: `tests/test_upload_form.py`

**Interfaces:**
- Consumes: Task 2 helpers, `store.files`, `currentUserId`, `saveSrc`.
- Produces: form punya `input[name="mode"]` (`link`|`berkas`), `input[type=file][name="berkas"]`, pesan galat `[data-err="berkas"]`; mode Berkas `disabled` dengan keterangan `Unggah file butuh login. Mode contoh tidak menyimpan file.` bila `!store.files`. Mode tidak ditampilkan saat mengubah sumber yang sudah ada.

- [ ] **Step 1: Tulis tes yang gagal:**
  - `test_upload_md_creates_card`: pilih Berkas, `set_input_files` `catatan-aljabar.md` (isi `# Aljabar`, 9 byte), judul terisi `catatan aljabar`, kirim → kartu baru berisi `catatan-aljabar.md · 9 B`, `__t.files` punya 1 kunci berawalan `demo/`.
  - `test_upload_too_big_rejected`: file 26214401 byte → pesan `Ukuran file maksimal 25 MB.`, tidak ada unggahan.
  - `test_failed_save_cleans_object`: `__t.failNextSave()` lalu unggah → toast galat, `__t.files.size == 0`, tidak ada kartu baru.
  - `test_demo_without_testfiles_disables_berkas`: buka `?demo` saja → radio Berkas `disabled`, keterangan tampil, tidak ada pageerror.
- [ ] **Step 2:** `pytest tests/test_upload_form.py -q` → FAIL.
- [ ] **Step 3:** Implementasi. Urutan kirim: validasi → `id = uuid()` → `store.files.upload(objectPath(uid, id, f.name), f, f.type || 'application/octet-stream')` → `saveSrc({id, url:null, jenis: fileJenis(...), berkas_path, berkas_nama: f.name, berkas_tipe, berkas_ukuran: f.size, judul, kelompok, materi_id})`; bila `saveSrc` melempar → `store.files.remove([path])` lalu `failed(err)`. Area seret-lepas pada label input file.
- [ ] **Step 4:** `pytest -q` → PASS.
- [ ] **Step 5:** Commit `Form sumber: unggah berkas`.

### Task 5: Kartu berkas, pembaca Markdown, buka PDF dan unduh

**Files:**
- Modify: `index.html` (`srcCard`, `kindIcon`, `JENIS`, handler `data-act`, CSS `.reader`), `README.md`
- Create: `tests/test_reader.py`

**Interfaces:**
- Consumes: `store.files.signedUrl`, `fmtSize`.
- Produces: kartu berkas `article.src[data-kind="berkas"]`; tombol `data-act="read"` (catatan), `data-act="open-file"` (pdf, tab baru), `data-act="download-file"` (berkas). Pembaca `.reader` di dalam kartu; isi dari `marked.parse` → `DOMPurify.sanitize`; semua `a` di dalamnya `target=_blank rel=noopener noreferrer`. Pemuat pustaka: `loadScript('https://cdn.jsdelivr.net/npm/marked@18.0.10/lib/marked.umd.js')` dan `'https://cdn.jsdelivr.net/npm/dompurify@3.4.14/dist/purify.min.js'`.

- [ ] **Step 1: Tulis tes yang gagal:**
  - `test_read_markdown_renders`: unggah MD `# Bab 1\n\n- a` → klik Baca → `.reader h1` berteks `Bab 1`, `.reader li` ada; klik lagi → pembaca tertutup.
  - `test_markdown_sanitized`: MD berisi `<img src=x onerror="window.__pwned=1">` dan `[x](javascript:alert(1))` → `window.__pwned` undefined, tidak ada `href` berawalan `javascript:`.
  - `test_pdf_opens_new_tab`: unggah PDF kecil → klik Buka → `context.expect_page()` menangkap tab baru.
  - `test_other_downloads`: unggah `a.docx` → tombol berlabel `Unduh`.
  - `test_search_finds_file_name`: cari `catatan-aljabar` → hasil menunjuk sumber berkas itu.
- [ ] **Step 2:** `pytest tests/test_reader.py -q` → FAIL.
- [ ] **Step 3:** Implementasi. Gagal memuat pustaka atau mengambil file → pesan di dalam pembaca `Catatan gagal dimuat. Coba lagi.` Pencarian ikut mencocokkan `berkas_nama`. Kartu tanpa `url` tidak memanggil `safeUrl`/`hostOf`. README: bagian setup (jalankan `schema.sql` terbaru) dan cara pakai unggah.
- [ ] **Step 4:** `pytest -q` → PASS; tes Playwright lama (`run.py`, `run2.py`) tanpa pageerror; screenshot desktop dan HP diperiksa.
- [ ] **Step 5:** Commit `Kartu berkas dan pembaca Markdown`.
