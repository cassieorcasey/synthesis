# Peta rapi (pohon kiri ke kanan) — Design

## Maksud
Peta sekarang memakai simulasi fisika (d3-force) dan anak baru muncul di sudut acak, jadi letak simpul berubah-ubah dan terasa ngacak. Pengguna ingin struktur mindmap rapi dan tetap.

## Tujuan
- Letak simpul ditentukan murni oleh struktur pohon: input yang sama selalu menghasilkan posisi yang sama.
- Induk di kiri, anak di kolom kanannya, anak sejajar rapi dan berurutan.
- Tidak ada kartu saling menimpa; garis lengkung tidak saling silang.
- Membuka atau menutup cabang menggeser tata letak dengan animasi halus.

## Bukan tujuan
- Tidak ada radial atau dua sisi.
- Posisi hasil seret tidak disimpan ke database.
- Struktur data dan skema Supabase tidak berubah.

## Pendekatan yang dipertimbangkan
1. **Pohon kiri ke kanan (dipilih pengguna)**: deterministik, tanpa tumpang tindih, cocok untuk kartu lebar. Peta memanjang ke bawah bila cabang banyak.
2. Radial: kartu lebar berdempet di dekat pusat.
3. Dua sisi: urutan baca terpecah.

## Keputusan (pengguna memilih opsi 1; sisanya pilihanku)
- Tata letak dihitung fungsi murni `layoutTree()` memakai ukuran kartu (`w`, `h`): tinggi subpohon = maks(tinggi kartu, jumlah tinggi anak + jarak); induk dipusatkan terhadap anaknya; lebar kolom = kartu terlebar di kedalaman itu + jarak.
- Kategori utama (akar) ditumpuk vertikal di kolom pertama, warna cabang tetap.
- Urutan anak: subkategori dulu, lalu materi, masing-masing urut abjad seperti yang sudah dilakukan `derive()` (bukan urutan input; dikoreksi setelah membaca kode). *Pilihanku.*
- d3-force dibuang. Posisi bergerak lewat transisi (tanpa transisi bila `prefers-reduced-motion`).
- Seret simpul = geser sementara; tombol **Rapikan** mengembalikan semua ke tata letak. Muat ulang atau buka/tutup cabang juga merapikan kembali. *Pilihanku.*
- Zoom, hover, semantic zoom, pencarian, dan panel samping tidak berubah. Garis tetap kurva Bézier dari tepi kanan induk ke tepi kiri anak.

## Diserahkan ke pembangun
Nilai jarak antar kolom dan antar baris, dan detail transisi.

## Pengujian
- Tidak ada dua kartu yang kotaknya beririsan (pohon contoh besar, dalam, dan acak).
- Setiap anak berada di kanan induknya; urutan anak sama dengan urutan `derive()` (abjad).
- Dua kali muat dengan data sama menghasilkan posisi identik.
- Buka lalu tutup cabang kembali ke posisi semula.
- Seret lalu klik Rapikan mengembalikan posisi.
- Seluruh tes lama (29) tetap hijau.
