Video Presentasi UTS (YouTube Unlisted): https://youtu.be/_fly-SfX88s?si=FvcTW1YWWKByoa5K

# AeroSwap — Sistem Manajemen & Alokasi Modul Baterai Tukar-Cepat (*Battery Swapping Station*) Armada Drone Logistik

Proyek ini disusun untuk memenuhi **Ujian Tengah Semester (UTS) Komputasi Paralel dan Terdistribusi** (Semester Ganjil 2026/2027) Program Studi Teknik Informatika, Fakultas Teknik dan Ilmu Komputer, Universitas Muhammadiyah Pontianak.

---

## 1. Deskripsi Tema Aplikasi

**AeroSwap** adalah backend REST API asinkron untuk mengelola inventaris dan transaksi penukaran paket baterai pintar (*Smart Flight Battery Pack*) pada stasiun pengisian otonom (*Drone Battery Swapping Station*) bagi armada drone kargo, pengiriman medis darurat, dan pemetaan geospasial.

- **Resource Utama (`/resource`)**: Modul baterai pintar yang tersimpan di rak stasiun pengisian, dilengkapi atribut `id`, `kode_seri`, `nama`, `kategori`, `kapasitas_wh`, `lokasi_stasiun`, `harga`, dan kolom kuantitas wajib `stok` (jumlah baterai berstatus *Full-Charged & Ready*).
- **Resource Transaksi (`/transactions`)**: Permintaan alokasi/penukaran baterai oleh unit drone (`item_id`, `qty`, `kode_drone`, `total_biaya`, `status`, `created_at`, `updated_at`) yang diproses secara asinkron di latar belakang (`pending` $\rightarrow$ `processing` $\rightarrow$ `completed`) menggunakan `BackgroundTasks` dan dilindungi dari *race condition* (*overselling*) menggunakan `asyncio.Lock`.

---