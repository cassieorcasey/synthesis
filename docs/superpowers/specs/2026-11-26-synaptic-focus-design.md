# Synaptic Focus & Study-Flow Choreography

**Spesifikasi Teknis UX, Koreografi Animasi, dan Anggaran Performa untuk Synthesis**

---

## 1. Visi & Prinsip Desain

**Synthesis** memadukan kanvas pohon kiri-ke-kanan berbasis SVG dengan panel baca *frosted glass*. Dokumen ini menetapkan cetak biru peningkatan UX dan animasi yang memperkuat karakter tenang Synthesis tanpa mengorbankan kecepatan interaksi pada peta berskala besar.

Empat prinsip utama mengikat seluruh keputusan teknis dalam dokumen ini:

1. **Satu Jam Gerak (*Single-Clock Motion*):** Seluruh pergeseran koordinat dan siklus masuk/keluar simpul dikendalikan oleh satu mesin interpolasi terpusat (`settle()`).
2. **Pemisahan Geometri dan Dekorasi:** Tata letak pohon (`treeLayout()`) dan ukuran kotak (`boxOf()`) bersifat deterministik dan statis terhadap efek visual sementara seperti *hover* atau *peek*.
3. **Ketenangan Optik (*Bounded Motion*):** Tidak ada animasi tak berujung di bawah lapisan kaca beku (`backdrop-filter`). Seluruh efek aliran berhenti setelah $1\text{--}2$ siklus.
4. **Performa Terukur sebagai Gerbang:** Setiap fase implementasi wajib lolos pengujian anggaran performa otomatis sebelum melangkah ke fase berikutnya.

---

## 2. Kontrak Arsitektur & Anggaran Performa

### 2.1 Anggaran Performa & Gerbang Pengujian (Playwright)

Sebelum melakukan refaktor rendering, sistem pengujian otomatis berbasis Playwright disiapkan untuk mengukur kinerja secara objektif:

* **Dataset Uji Deterministik (`window.__t`):** Generator peta sintetis berkapasitas **$500$ simpul** dan **$2.000$ simpul** (dengan distribusi kategori bertingkat, materi, dan sumber).
* **Anggaran `refresh()`:** Eksekusi penuh siklus `derive()` $\rightarrow$ `rebuild()` $\rightarrow$ `draw()` wajib selesai di bawah **$50\text{ ms}$** pada perangkat desktop.
* **Anggaran Interaksi Kanvas (*Pan & Zoom*):** Gestur geser dan perbesaran berkelanjutan pada peta $500$ maupun $2.000$ simpul tidak boleh menghasilkan *long task* di atas **$50\text{ ms}$** (diukur melalui `PerformanceObserver` untuk entri `longtask`).
* **Gerbang Fase:** Pengujian anggaran di atas dijalankan sebagai syarat kelulusan di akhir setiap fase (Fase 0 hingga Fase 4).

### 2.2 Aturan Gerak Tunggal & Batasan Render CSS/SVG

* **Pembersihan & Latar Kanvas:**
  * Variabel CSS `--inv` yang tidak terpakai pada `#vp` dihapus.
  * Latar titik tak hingga pada `#stage` tetap menggunakan CSS `radial-gradient` yang sudah ada (tidak dimigrasi ke SVG `<pattern>`).
* **Kontrol Posisi & Siklus Hidup via `settle()`:**
  * Baik pergeseran tata letak maupun animasi keluar (*exit* saat `collapse`) dijalankan melalui satu *timer* `settle()`.
  * Saat kategori dilipat (`collapse`), simpul anak tetap dipertahankan sementara di daftar render sebagai simpul keluar (*exiting nodes*), bergerak menyusut kembali ke koordinat induknya dalam satu siklus `settle()`, lalu dihapus dari DOM ketika jam berhenti.
* **Disiplin Properti CSS & Transformasi SVG:**
  * Transformasi skala (`transform: scale(...)`) **hanya** diterapkan pada grup internal `.body` (`transform-box: fill-box; transform-origin: center`) agar tidak berbenturan dengan atribut `transform="translate(x, y)"` milik `<g class="node">`.
  * Transisi CSS (`transition`) dibatasi secara ketat hanya pada properti **`opacity`**, **warna (`fill`, `stroke`)**, dan **skala `.body`**. Tidak ada transisi CSS pada atribut geometri SVG (`x`, `y`, `width`, `height`, `d`).

### 2.3 *Keyed Incremental DOM Update* pada `paintNode()`

* Menghapus pola `g.selectAll('*').remove()` yang menghancurkan dan membuat ulang elemen SVG di setiap `refresh()`.
* Struktur dasar simpul (`.body`, `.shape`, `.ring`, `.stack`, `.pip`/`.ico`, `.t`, `.badge`, `.far`) dibuat satu kali saat fase `enter()`.
* Pada fase `update()`, `paintNode()` hanya menambal atribut dan isi teks yang berubah, sehingga status kelas dan transisi `opacity`/warna/skala tetap utuh.

### 2.4 Gerbang `reduceMotion` Reaktif

* Mengganti pembacaan statis `reduceMotion` menjadi status reaktif yang mendengarkan perubahan preferensi sistem secara langsung (`matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', ...)`).
* Setiap animasi JavaScript (`settle()`, *ripple*, *odometer*, *camera framing*, dan transisi FLIP) wajib memeriksa gerbang `prefersReducedMotion()` sebelum berjalan, dan langsung memotong ke keadaan akhir apabila mode pengurangan gerak aktif.

---

## 3. Spesifikasi Koreografi UX & Animasi

### 3.1 *Semantic Zoom Crossfade* (dengan Histeresis) & *Overlay Peek*

* **Crossfade Tanpa Morph Geometri:**
  * Perpindahan antar-level zoom (`far`, `mid`, `near`) menggunakan transisi `opacity` yang halus antara chip materi lengkap (`.chip`) dan titik konstelasi (`.far`), tanpa menganimasikan perubahan dimensi kotak.
* **Pita Histeresis Skala Zoom ($K$):**
  * Untuk mencegah kedipan (*flicker*) saat pengguna melakukan *zoom* di sekitar titik ambang batas, transisi level menerapkan histeresis:
    * Masuk ke mode `far` saat $K < 0.46$; kembali ke mode `mid` saat $K > 0.54$.
    * Masuk ke mode `near` saat $K > 1.55$; kembali ke mode `mid` saat $K < 1.45$.
* ***Peek* pada Lapisan *Overlay* Terpisah:**
  * Ketika pengguna mengarahkan kursor (*hover*) ke titik materi (`.far`) pada mode `far`, pratinjau judul ringkas ditampilkan pada lapisan `<g id="overlay">` di atas `#nodes`.
  * Karena berada di lapisan terpisah, *peek* tidak mengubah `boxOf()`, tidak memicu `treeLayout()`, dan otomatis hilang saat kursor berpindah atau zoom berubah.

### 3.2 *Synaptic Readiness*, *Ripple* Terbatas & *Odometer Badge* Terkunci

* **Makna & Ukuran *Badge* Kategori:**
  * *Badge* kategori tetap menghitung jumlah materi pada cabang tersebut (`D.total`).
  * Lebar kotak *badge* (`bw` pada `boxOf()`) dikunci tetap setara lebar **3 digit** (`textW('888', 'badge') + 14`) sehingga ukuran pil kategori tidak pernah berubah saat jumlah materi bertambah atau berkurang.
* **Animasi *Odometer* pada *Badge*:**
  * Guliran angka *odometer* pada *badge* hanya dipicu ketika terjadi perubahan jumlah materi (penambahan, penghapusan, atau pemindahan materi antar-kategori), bukan saat sumber belajar ditambah.
  * Angka bergeser vertikal sesuai arah perubahan (ke atas saat bertambah, ke bawah saat berkurang) disertai denyut ringan pada `.body`.
* **Spektrum Kesiapan Materi & *Synaptic Ripple* Terbatas:**
  * Titik status materi (`.ico`) membedakan 3 tingkat kelengkapan: **kosong** ($0$ sumber, cincin berongga), **terkurasi** ($1\text{--}2$ sumber, titik penuh), dan **matang** ($\ge 3$ sumber, titik penuh dengan cincin luar tipis).
  * Ketika sumber baru ditambahkan ke suatu materi, impuls cahaya merambat di sepanjang kurva Bézier aktif menuju kategori induk. Animasi aliran garis (*dash flow*) dibatasi maksimal **$1\text{--}2$ putaran** lalu berhenti sepenuhnya.

### 3.3 *Depth-of-Field Cognitive Spotlight* (Khusus Seleksi)

* **Aktivasi Khusus Seleksi:** Efek *Depth-of-Field* hanya aktif ketika pengguna memilih sebuah simpul (`selectedId !== null`).
* **Interaksi *Hover*:** Mengarahkan kursor (*hover*) tetap menggunakan sorotan ringan lokal pada simpul dan leluhurnya tanpa meredupkan atau mengubah skala seluruh cabang lain di peta.
* **Hierarki Fokus saat Seleksi Aktif:**
  1. **Jalur Aktif (*Selected & Lineage*):** Opasitas penuh ($1.0$), skala `.body` sedikit menonjol ($1.02$), serta animasi arah aliran garis terbatas ($1\text{--}2$ putaran) pada konektor terhubung.
  2. **Konteks Saudara (*Siblings*):** Opasitas menengah ($0.62$) dan skala `.body` normal ($1.0$).
  3. **Cabang Luar (*Distant*):** Opasitas diredupkan ($0.28$) dan skala `.body` sedikit menyusut ($0.96$) untuk memusatkan perhatian tanpa menggunakan `filter: blur()`.

### 3.4 Penanda Buka/Tutup Cabang & Navigasi Keyboard (*Roving Tabindex*)

* **Penanda Status Ekspansi Cabang:**
  * Kategori yang memiliki anak (`hasKids(id)`) menampilkan indikator status buka/tutup yang konsisten—tumpukan kartu `.stack` saat tertutup dan penanda lipat yang jelas saat terbuka—sehingga pengguna memahami bahwa klik kedua pada kategori terbuka akan melipat cabangnya.
* **Navigasi Panah & *Roving Tabindex*:**
  * Mengganti `tabindex="0"` pada seluruh simpul SVG menjadi pola ***roving tabindex***: hanya satu simpul aktif di kanvas yang memiliki `tabindex="0"`, sementara simpul lainnya menggunakan `tabindex="-1"`. Pengguna dapat melompat masuk dan keluar kanvas dengan satu kali tekan `Tab`.
  * Mendukung navigasi spasial menggunakan tombol panah saat fokus berada di kanvas:
    * `ArrowRight`: Membuka kategori tertutup atau berpindah ke anak pertama.
    * `ArrowLeft`: Melipat kategori terbuka atau berpindah ke kategori induk.
    * `ArrowDown` / `ArrowUp`: Berpindah ke simpul saudara berikutnya atau sebelumnya.

### 3.5 Koreografi Panel & *Study-Flow*

* **Prasyarat Wajib (Perbaikan Bug Panel):**
  1. **Mencegah *Restart* Video YouTube:** Mengubah `renderPanel()` agar tidak menimpa seluruh `panelEl.innerHTML` saat pembaruan bagian kecil terjadi. Pembaruan dilakukan per bagian (*section-level patching*), sehingga `<iframe>` pemutar video yang sedang berjalan tidak ter-reset ketika pengguna mengedit sumber lain atau menambah catatan.
  2. **Perbaikan Aksesibilitas `aria-live`:** Menghapus atribut `aria-live="polite"` dari kontainer utama `#panel` agar pembaca layar tidak membacakan ulang seluruh isi panel dari judul setiap kali ada perubahan di dalam panel. Umpan balik singkat diarahkan secara eksklusif ke `#toast`.
* **Koreografi Alur Belajar (*Study-Flow*):**
  * **Transisi Arah Hierarki:** Perpindahan ke sub-item dalam panel menggeser konten masuk dari kanan, sedangkan navigasi naik melalui `.crumbs` menggeser konten masuk dari kiri.
  * **Pita Navigasi Kelompok (*Study-Flow Stepper*):** Ketika materi memiliki beberapa kelompok sumber (*Pengantar*, *Penjelasan*, *Latihan soal*, dan seterusnya), ditampilkan bilah lompat cepat di atas daftar sumber untuk menggulir mulus ke kelompok tujuan.
  * **Ekspansi FLIP untuk *Reader* & Video:** Pembukaan pembaca Markdown (`.reader.md`) dan penyematan pemutar YouTube menggunakan teknik FLIP (*First-Last-Invert-Play*) agar kartu sumber di bawahnya bergeser turun secara mulus.

---

## 4. Item di Luar Lingkup (Ditunda)

* ***Counter-Scaling* Label Kategori pada Zoom `far`:** Memperbesar skala teks label kategori secara berlawanan dengan skala kamera saat zoom jauh ditunda hingga pasca-Fase 4. Pada peta padat berisi $500\text{--}2.000$ simpul, fitur ini membutuhkan algoritma deteksi dan penyembunyian tabrakan teks (*label collision culling*) tersendiri agar tetap memenuhi anggaran performa $< 50\text{ ms}$.

---

## 5. Peta Jalan Implementasi Bertahap (*Phase-Gated*)

Setiap fase wajib lulus seluruh pengujian fungsional yang ada serta gerbang performa Playwright ($500$ dan $2.000$ simpul, `refresh() < 50 ms`, pan/zoom tanpa *long task* $> 50\text{ ms}$) sebelum lanjut ke fase berikutnya:

| Fase | Fokus Utama | Keluaran & Kriteria Lolos |
| :--- | :--- | :--- |
| **Fase 0** | **Baseline & Kebersihan Fondasi** | Generator peta uji $500$ & $2.000$ simpul, skrip benchmark Playwright, penghapusan `--inv`, serta gerbang `reduceMotion` reaktif. |
| **Fase 1** | **Keyed DOM, Exit Cycle & Roving Tabindex** | Refaktor `paintNode()` menjadi *incremental patch*, transisi keluar simpul melalui satu jam `settle()`, penanda buka/tutup cabang, dan navigasi panah + *roving tabindex*. |
| **Fase 2** | **Semantic Crossfade, Overlay Peek & DOF Seleksi** | Transisi `opacity` antar-level zoom dengan histeresis, *peek* di lapisan `<g id="overlay">`, dan fokus optik 3 lapisan khusus saat `selectedId` aktif. |
| **Fase 3** | **Readiness, Locked Odometer & Bounded Ripple** | Kunci lebar *badge* 3 digit, guliran *odometer* saat jumlah materi berubah, 3 status visual `.ico`, dan pulsa jalur terbatas ($1\text{--}2$ putaran) saat sumber ditambah. |
| **Fase 4** | **Perbaikan Bug Panel & Study-Flow** | Perbaikan *section patching* (`<iframe>` YouTube tidak *restart*) dan penghapusan `aria-live` pada `#panel`, dilanjutkan *directional slide*, *stepper* kelompok, dan ekspansi FLIP *reader*. |