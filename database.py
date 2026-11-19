"""
database.py - Modul Manajemen Basis Data Asinkron (aiosqlite)
Tema Aplikasi: AeroSwap - Sistem Manajemen & Alokasi Modul Baterai Tukar-Cepat
               (Battery Swapping Station) untuk Armada Drone Logistik

Seluruh operasi I/O ke SQLite dilakukan secara non-blocking menggunakan
async/await dan pustaka aiosqlite agar event loop FastAPI tidak terblokir.
"""

import os
from datetime import datetime, timezone
from typing import Any, Optional
import aiosqlite

# Lokasi berkas basis data SQLite di dalam direktori UTS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "aeroswap.db")

# Skema tabel resource utama (modul baterai pintar di stasiun tukar-cepat).
# Memiliki 7 kolom selain 'id' (melebihi syarat minimum 4 kolom selain 'id')
# serta memuat kolom kuantitas wajib 'stok' bertipe INTEGER.
# Catatan: Validasi stok >= 0 untuk input pengguna diterapkan pada model Pydantic
# dan penguncian transaksi pada asyncio.Lock, sehingga skenario uji Tahap 1 B3
# (tanpa lock -> stok akhir minus/overselling) dapat teramati pada SQLite.
CREATE_RESOURCE_TABLE = """
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_seri TEXT NOT NULL,
    nama TEXT NOT NULL,
    kategori TEXT NOT NULL,
    kapasitas_wh REAL NOT NULL,
    lokasi_stasiun TEXT NOT NULL,
    harga REAL NOT NULL,
    stok INTEGER NOT NULL
);
"""

# Skema tabel transaksi penukaran/alokasi baterai drone.
# Menyimpan status siklus hidup transaksi: pending -> processing -> completed / failed
CREATE_TRANSACTION_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    kode_drone TEXT NOT NULL DEFAULT 'DRN-LOGISTIK-01',
    total_biaya REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES resources (id) ON DELETE CASCADE
);
"""


def _waktu_sekarang() -> str:
    """Mengembalikan timestamp ISO-8601 UTC saat ini."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def get_db_connection() -> aiosqlite.Connection:
    """
    Membuka koneksi asinkron ke SQLite dengan mode WAL (Write-Ahead Logging)
    dan busy_timeout agar aman diakses secara konkuren oleh multi-worker Uvicorn.
    """
    conn = await aiosqlite.connect(DB_PATH, timeout=15.0)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA busy_timeout=15000;")
    return conn


async def init_db() -> None:
    """
    Inisialisasi tabel resources dan transactions secara asinkron saat aplikasi dijalankan.
    """
    conn = await get_db_connection()
    try:
        await conn.execute(CREATE_RESOURCE_TABLE)
        await conn.execute(CREATE_TRANSACTION_TABLE)
        await conn.commit()
    finally:
        await conn.close()


# =====================================================================
# OPERASI CRUD RESOURCE UTAMA (B1) - ASINKRON (NON-BLOCKING I/O)
# =====================================================================

async def get_all_resources(skip: int = 0, limit: int = 10) -> list[dict[str, Any]]:
    """Mengambil daftar resource dengan paginasi (skip & limit) secara asinkron."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM resources ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, skip),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_resource_by_id(resource_id: int) -> Optional[dict[str, Any]]:
    """Mengambil detail satu resource berdasarkan ID secara asinkron."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM resources WHERE id = ?",
            (resource_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def create_resource(data: dict[str, Any]) -> dict[str, Any]:
    """Menambahkan resource modul baterai baru ke basis data secara asinkron."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO resources (
                kode_seri, nama, kategori, kapasitas_wh, lokasi_stasiun, harga, stok
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["kode_seri"],
                data["nama"],
                data["kategori"],
                data["kapasitas_wh"],
                data["lokasi_stasiun"],
                data["harga"],
                data["stok"],
            ),
        )
        await conn.commit()
        new_id = cursor.lastrowid
        cursor_select = await conn.execute(
            "SELECT * FROM resources WHERE id = ?", (new_id,)
        )
        row = await cursor_select.fetchone()
        return dict(row)
    finally:
        await conn.close()


async def update_resource(resource_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Memperbarui data resource berdasarkan ID dan mengembalikan data terbaru."""
    conn = await get_db_connection()
    try:
        cursor_check = await conn.execute(
            "SELECT id FROM resources WHERE id = ?", (resource_id,)
        )
        if not await cursor_check.fetchone():
            return None

        await conn.execute(
            """
            UPDATE resources
            SET kode_seri = ?,
                nama = ?,
                kategori = ?,
                kapasitas_wh = ?,
                lokasi_stasiun = ?,
                harga = ?,
                stok = ?
            WHERE id = ?
            """,
            (
                data["kode_seri"],
                data["nama"],
                data["kategori"],
                data["kapasitas_wh"],
                data["lokasi_stasiun"],
                data["harga"],
                data["stok"],
                resource_id,
            ),
        )
        await conn.commit()

        cursor_updated = await conn.execute(
            "SELECT * FROM resources WHERE id = ?", (resource_id,)
        )
        row = await cursor_updated.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def delete_resource(resource_id: int) -> bool:
    """Menghapus permanen (hard delete) resource dari basis data."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            "DELETE FROM resources WHERE id = ?", (resource_id,)
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


# =====================================================================
# OPERASI STOK & TRANSAKSI ASINKRON (B2 & B3)
# =====================================================================

async def get_stok(item_id: int) -> Optional[int]:
    """Membaca jumlah stok terkini dari suatu resource berdasarkan item_id."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            "SELECT stok FROM resources WHERE id = ?", (item_id,)
        )
        row = await cursor.fetchone()
        return int(row["stok"]) if row is not None else None
    finally:
        await conn.close()


async def decrement_stok(item_id: int, qty: int) -> Optional[int]:
    """
    Mengurangi stok resource sebanyak qty di basis data SQLite
    dan mengembalikan nilai stok akhir setelah dikurangi.
    """
    conn = await get_db_connection()
    try:
        await conn.execute(
            "UPDATE resources SET stok = stok - ? WHERE id = ?",
            (qty, item_id),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT stok FROM resources WHERE id = ?", (item_id,)
        )
        row = await cursor.fetchone()
        return int(row["stok"]) if row is not None else None
    finally:
        await conn.close()


async def set_stok(item_id: int, stok_baru: int) -> bool:
    """Mengatur ulang nilai stok resource tertentu (berguna untuk pengujian B3)."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            "UPDATE resources SET stok = ? WHERE id = ?",
            (stok_baru, item_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def insert_transaction(
    item_id: int,
    qty: int,
    kode_drone: str = "DRN-LOGISTIK-01",
    status: str = "pending",
) -> dict[str, Any]:
    """
    Mencatat transaksi baru dengan status awal 'pending' secara asinkron.
    """
    conn = await get_db_connection()
    try:
        cursor_res = await conn.execute(
            "SELECT harga, stok FROM resources WHERE id = ?", (item_id,)
        )
        res_row = await cursor_res.fetchone()
        harga_satuan = float(res_row["harga"]) if res_row else 0.0
        sisa_stok = int(res_row["stok"]) if res_row else 0
        total_biaya = harga_satuan * qty
        now = _waktu_sekarang()

        cursor = await conn.execute(
            """
            INSERT INTO transactions (
                item_id, qty, kode_drone, total_biaya, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (item_id, qty, kode_drone, total_biaya, status, now, now),
        )
        await conn.commit()
        trx_id = cursor.lastrowid
        return {
            "id": trx_id,
            "item_id": item_id,
            "qty": qty,
            "kode_drone": kode_drone,
            "total_biaya": total_biaya,
            "status": status,
            "sisa_stok_saat_ini": sisa_stok,
            "created_at": now,
            "updated_at": now,
        }
    finally:
        await conn.close()


async def update_trx_status(trx_id: int, status: str) -> None:
    """
    Memperbarui status transaksi (misalnya dari 'pending' -> 'processing' -> 'completed')
    yang dipanggil oleh fungsi pekerja BackgroundTasks.
    """
    conn = await get_db_connection()
    try:
        now = _waktu_sekarang()
        await conn.execute(
            "UPDATE transactions SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, trx_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_all_transactions(status_filter: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Mengambil daftar transaksi, mendukung filter opsional berdasarkan query ?status=...
    """
    conn = await get_db_connection()
    try:
        if status_filter:
            cursor = await conn.execute(
                """
                SELECT t.*, r.nama AS nama_resource, r.kode_seri
                FROM transactions t
                LEFT JOIN resources r ON t.item_id = r.id
                WHERE t.status = ?
                ORDER BY t.id DESC
                """,
                (status_filter,),
            )
        else:
            cursor = await conn.execute(
                """
                SELECT t.*, r.nama AS nama_resource, r.kode_seri
                FROM transactions t
                LEFT JOIN resources r ON t.item_id = r.id
                ORDER BY t.id DESC
                """
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_transaction_by_id(trx_id: int) -> Optional[dict[str, Any]]:
    """Mengambil detail satu transaksi beserta status terkininya berdasarkan ID."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT t.*, r.nama AS nama_resource, r.kode_seri, r.stok AS sisa_stok_resource
            FROM transactions t
            LEFT JOIN resources r ON t.item_id = r.id
            WHERE t.id = ?
            """,
            (trx_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()
