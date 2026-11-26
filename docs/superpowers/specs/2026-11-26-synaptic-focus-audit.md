# Synaptic Focus: UX, Performance & Code Readiness Audit

Audit `index.html` di `main` (`d7b8e9a`) terhadap konsep awal *Synaptic Focus & Study-Flow Choreography*. Hasilnya menjadi dasar spesifikasi revisi di `2026-11-26-synaptic-focus-design.md`. Semua temuan berasal dari membaca kode; angka 165 ms berasal dari peninjau fitur peta rapi (1.901 simpul).

## 1. Temuan kritis

### High
1. **CSS `transform` di `g.node` menimpa atribut `transform="translate(x,y)"`.** Skala apa pun di `g.node` melempar simpul ke (0,0). Semua skala harus di `g.body` (sudah `transform-box: fill-box`).
2. **Badge kategori = jumlah materi (`D.total`), bukan sumber.** Odometer dari `saveSrc`/`removeSrc` tidak akan pernah berubah.
3. **Lebar badge ikut jumlah digit (`bw` di `boxOf`).** 9 → 10 melebarkan kartu dan menggeser satu kolom `treeLayout`.
4. **`refresh()` membangun ulang semuanya** (`derive`, `boxOf` + `measureText` per simpul, `paintNode` hapus-bangun, `renderSide`, `innerHTML` panel, `applyHighlight`). Animasi apa pun yang dimulai sesudahnya tersendat.
5. **`renderPanel()` menulis ulang `innerHTML` di setiap `refresh()`.** Iframe YouTube yang diputar dibuat ulang (video mulai dari awal), slide/FLIP akan terulang, dan `aria-live="polite"` membacakan ulang seluruh panel.
6. **Migrasi dot-grid ke `<pattern>` tidak menghemat apa pun.** Isi SVG di `#vp` dirender ulang tiap perubahan transform, pattern ikut di render itu dan kehilangan normalisasi kepadatan titik. Biaya per-frame yang nyata adalah `--inv` di `#vp`, yang tidak dipakai CSS mana pun.

### Medium
7. `backdrop-filter` di sidebar, panel, dan zoombar memaksa blur ulang setiap kanvas di bawahnya repaint.
8. `applyHighlight` memakai `hoverId || selectedId`; DOF tiga lapis akan berkedip mengikuti mouse.
9. Ambang `far` (`K < 0.5`) tanpa histeresis berkedip saat pinch.
10. Transisi CSS untuk `width`/`height`/`rx` pada `<rect>` belum terverifikasi di Safari; `circle.far` sudah ada untuk crossfade.
11. Lipat lalu buka dalam 220 ms menghasilkan dua `g.node` ber-id sama; `rebuild()` sudah menghapus posisi simpul tersembunyi dari `pos`.
12. Posisi digerakkan JS (`settle` → `d3.timer`); transisi CSS untuk posisi akan berebut properti.
13. `.panel` sudah punya animasi `slide`/`rise`; slide `.panel-body` di dalam `overflow: auto` memunculkan scrollbar; `select()` bisa memanggil `renderPanel()` dua kali.
14. Cabang terbuka tidak punya penanda; melipat butuh klik kedua yang tidak mudah ditemukan.
15. Semua simpul `tabindex="0"` dalam urutan BFS, tanpa navigasi panah.
16. Opacity 0,26 membuat label sekitar 1,5:1; label kategori 14 px tampil 3–7 px di zoom `far`.
17. `prefers-reduced-motion` di CSS tidak menghentikan animasi JS; `reduceMotion` dibaca sekali saat dimuat.

### Low
18. `isPhone()` mengukur lebar (≤760 px); peek harus memakai `canHover`.
19. `freeRect()` di ponsel memakai `H * 0.34` tetap, bukan tepi panel.
20. Ripple saat `settle` berjalan butuh `getTotalLength()` per frame.
21. Pill peek tertimpa simpul berikutnya; `raise()` mengacak urutan DOM dan tab.
22. `drop-shadow` di `.node.root .shape` dirender ulang tiap frame pan.
23. Ctrl+scroll di atas panel atau sidebar memperbesar halaman browser.

## 2. Peta kecocokan kode

| Nama di dokumen | Kondisi aktual | Catatan |
|---|---|---|
| `#stage`, `applyZoom()` | `radial-gradient` 24 px; `applyZoom` mengubah `backgroundSize`/`Position` dan menulis `--inv` | `--inv` tak terpakai |
| `#map`, `#vp` | `svg#map[data-zoom]` dengan `focusing`/`hovering`/`dragging`; `g#vp` berisi `#links` lalu `#nodes` | Kurva di belakang kartu |
| `#panel` | `aside.panel.glass` + `hidden` + `aria-live`; animasi buka `slide`/`rise` | |
| `.node.mat`/`.node.kat` | `g.node` + `root`, `selected`, `faded`, `hot`, `nosrc`, `custom`, `pulse`; isi di `g.body` | Posisi lewat atribut `transform` |
| `.chip`, `.t`, `.ico` | `g.chip` (materi); `text.t` + `tspan` per baris; `circle.ico` r=4 di kiri | `.ico` juga dipakai di `.src` panel |
| *(tak disebut)* `.far` | `circle.far` r=9 di tengah, tampil lewat `display` saat `far` | Siap untuk crossfade |
| `.badge` | Kategori saja, isi `D.total`, lebar ikut digit | |
| `.link` | `path.link.kk`/`.km`, `d` dari `curve()` induk → anak | Ripple mundur harus dibalik |
| `paintNode()`, `draw()` | `selectAll('*').remove()`; join berkunci id, `exit().remove()`, `order()` | Struktur bergantung tier, stack, jumlah baris |
| `refresh()`, `collapse()` | Rantai penuh + `settle(true)`; `heat` tak dipakai | |
| `freeRect()`, `focusNode()` | Ada; `focusNode` sudah memusatkan target `tx`/`ty` ke ruang bebas | Kamera asimetris sudah ada |
| `applyHighlight()` | Hover atau seleksi; kategori menyorot subpohon, materi hanya leluhur | Belum ada konsep saudara |
| `saveSrc()`/`removeSrc()` | Pembungkus tipis; pemanggil yang `refresh(0.05)` | `saveSrc` juga untuk edit |
| `renderPanel()`, `materiPanel`, `.crumbs`, `.src`, `.thumb`, `.reader.md` | `innerHTML` penuh; `kategoriPanel` juga ada; crumbs `data-act="goto"`; catatan yang dimuat mengganti kartunya sendiri | |
| `isPhone` | `innerWidth <= 760` | Pakai `canHover` untuk hover |
| *(tak disebut)* `settle()`, `treeLayout()`, `tidy()` | Satu `d3.timer` 380 ms | Jam gerak tunggal |

## 3. Keputusan yang sudah diambil di spesifikasi revisi

Badge tetap menghitung materi dengan lebar dikunci 3 digit; `<pattern>` batal dan `--inv` dihapus; satu jam gerak dan skala hanya di `.body`; DOF khusus seleksi; crossfade dengan histeresis dan peek di overlay; dash flow 1–2 putaran; `reduceMotion` reaktif; gerbang performa 500 dan 2.000 simpul; penanda cabang dan roving tabindex masuk lingkup; counter-scaling label `far` ditunda.

## 4. Celah yang masih terbuka (usulan, belum disetujui)

1. **Gerbang Fase 0:** Fase 0 belum menyentuh `paintNode`, jadi anggaran `refresh() < 50 ms` tidak bisa lulus. Usulan: Fase 0 mencatat baseline, anggaran wajib sejak Fase 1, diukur pada `refresh()` penuh.
2. **Saudara saat kategori dipilih:** usulan jalur aktif = terpilih + leluhur + isi cabang yang terlihat; saudara = induk yang sama; sisanya cabang luar.
3. **Jangkauan ripple:** usulan sampai akar, hanya sepanjang garis yang terlihat.
4. **Penanda cabang terbuka:** usulan chevron kecil di tepi kanan pill yang berputar saat dibuka, dengan mockup di Fase 1.
