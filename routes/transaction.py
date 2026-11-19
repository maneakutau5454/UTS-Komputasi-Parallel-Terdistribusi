"""
routes/transaction.py - Endpoint Transaksi Asinkron (BackgroundTasks) & Penguncian Konkurensi (asyncio.Lock)
Sub-bagian B2 (25 Poin) & Sub-bagian B3 (10 Poin)

Mengimplementasikan:
1. Pemrosesan transaksi asinkron di latar belakang menggunakan BackgroundTasks bawaan FastAPI
   dengan alur transisi status: pending -> processing -> completed / failed.
2. Pencegahan race condition (overselling stok baterai) menggunakan asyncio.Lock pada
   critical section pembacaan dan pengurangan stok modul baterai.
"""

import asyncio
import os
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
import database as db
from models import (
    TransactionAcceptedResponse,
    TransactionCreate,
    TransactionDetailResponse,
)

router = APIRouter(tags=["Transaksi Alokasi Baterai (Async & Lock)"])

# =====================================================================
# KONFIGURASI GEMBOK KONKURENSI (B3 - Thread/Async Safety)
# =====================================================================
# Inisialisasi objek asyncio.Lock di tingkat modul untuk melindungi critical section
# pada saat beberapa coroutine mengakses dan memotong stok secara bersamaan.
stok_lock = asyncio.Lock()

# Saklar mode penguncian untuk memudahkan pengujian Tahap 1 (Tanpa Lock) vs Tahap 2 (Dengan Lock).
# Default: True (Menggunakan asyncio.Lock).
# Untuk menguji Tahap 1 (Tanpa Lock), jalankan server dengan:
#   USE_LOCK=0 uvicorn main:app --port 8000
# atau ubah nilai default di bawah menjadi False.
USE_LOCK: bool = os.getenv("USE_LOCK", "1").lower() not in ("0", "false", "no")


# =====================================================================
# FUNGSI PEMOTONGAN STOK: TANPA LOCK vs DENGAN LOCK (Listing 3 & 4)
# =====================================================================

async def potong_stok_tanpa_lock(item_id: int, qty: int) -> tuple[str, Optional[int]]:
    """
    Versi 1 (Tahap 1 - Tanpa Lock): Rentan terhadap Race Condition (Overselling).
    Ketika dua request datang serentak saat stok tersisa 1, keduanya membaca
    stok_terkini = 1 sebelum salah satu sempat memperbarui basis data.
    """
    stok_terkini = await db.get_stok(item_id)
    if stok_terkini is None:
        return "not_found", None

    # Jeda buatan 10 milidetik untuk membuka jendela waktu terjadinya race condition
    # (context switch pada event loop terjadi saat await asyncio.sleep)
    await asyncio.sleep(0.01)

    if stok_terkini < qty:
        return "insufficient", stok_terkini

    # Kedua request membaca nilai stok yang sama sebelum sempat diperbarui,
    # sehingga stok dikurangi dua kali dan menghasilkan nilai akhir negatif (-1).
    sisa_stok = await db.decrement_stok(item_id, qty)
    return "ok", sisa_stok


async def potong_stok_dengan_lock(item_id: int, qty: int) -> tuple[str, Optional[int]]:
    """
    Versi 2 (Tahap 2 - Dengan Lock): Aman dari Race Condition menggunakan asyncio.Lock.
    Blok 'async with stok_lock:' menjamin hanya satu coroutine yang dapat masuk ke
    critical section (baca stok -> cek kecukupan -> kurangi stok) pada satu waktu.
    """
    async with stok_lock:
        stok_terkini = await db.get_stok(item_id)
        if stok_terkini is None:
            return "not_found", None

        # Meskipun terdapat jeda I/O asinkron di dalam critical section,
        # coroutine kedua wajib mengantre hingga coroutine pertama melepas stok_lock.
        await asyncio.sleep(0.01)

        if stok_terkini < qty:
            return "insufficient", stok_terkini

        sisa_stok = await db.decrement_stok(item_id, qty)
        return "ok", sisa_stok


# =====================================================================
# FUNGSI PEKERJA LATAR BELAKANG INTERNAL (B2 - BackgroundTasks)
# =====================================================================

async def proses_transaksi_background(trx_id: int, item_id: int, qty: int) -> None:
    """
    Fungsi pekerja internal di latar belakang (bukan endpoint HTTP).
    Menjalankan siklus hidup status transaksi secara asinkron:
        pending -> processing -> completed (atau failed jika terjadi galat)
    """
    try:
        # 1. Perbarui status transaksi dari 'pending' menjadi 'processing'
        await db.update_trx_status(trx_id, "processing")

        # 2. Simulasi pekerjaan I/O intensif selama 3 detik:
        #    (Verifikasi telemetri BMS baterai, kalibrasi voltase sel, dan
        #     pelepasan kunci mekanis laci stasiun tukar-cepat AeroSwap)
        await asyncio.sleep(3)

        # 3. Finalisasi transaksi dan perbarui status menjadi 'completed'
        await db.update_trx_status(trx_id, "completed")
    except Exception:
        # Jika terjadi kegagalan sistem saat pemrosesan latar belakang, tandai 'failed'
        await db.update_trx_status(trx_id, "failed")


# =====================================================================
# ENDPOINT HTTP TRANSAKSI (B2 & B3)
# =====================================================================

@router.post(
    "/transactions",
    response_model=TransactionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Buat transaksi penukaran baterai baru (non-blocking, respon instan status pending)",
)
async def create_transaction(data: TransactionCreate, bg: BackgroundTasks):
    """
    Endpoint HTTP untuk membuat transaksi penukaran modul baterai AeroSwap:
    1. Memvalidasi ketersediaan resource dan memotong stok (dengan/tanpa asyncio.Lock).
    2. Jika resource tidak ada -> 404 Not Found.
    3. Jika stok habis / tidak mencukupi -> 409 Conflict.
    4. Menyimpan transaksi dengan status awal 'pending'.
    5. Menjadwalkan 'proses_transaksi_background' ke BackgroundTasks dan
       langsung mengembalikan respon instan (202 Accepted) tanpa menunggu 3 detik.
    """
    if USE_LOCK:
        hasil, sisa_stok = await potong_stok_dengan_lock(data.item_id, data.qty)
    else:
        hasil, sisa_stok = await potong_stok_tanpa_lock(data.item_id, data.qty)

    if hasil == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modul baterai dengan ID {data.item_id} tidak terdaftar pada basis data.",
        )

    if hasil == "insufficient":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Stok modul baterai habis atau tidak mencukupi "
                f"(ID={data.item_id}, stok tersedia={sisa_stok}, diminta={data.qty})."
            ),
        )

    # Catat transaksi baru di SQLite dengan status awal 'pending'
    trx_record = await db.insert_transaction(
        item_id=data.item_id,
        qty=data.qty,
        kode_drone=data.kode_drone,
        status="pending",
    )
    trx_id = trx_record["id"]

    # Jadwalkan pemrosesan latar belakang ke BackgroundTasks bawaan FastAPI
    bg.add_task(proses_transaksi_background, trx_id, data.item_id, data.qty)

    return {
        "id": trx_id,
        "item_id": data.item_id,
        "qty": data.qty,
        "kode_drone": data.kode_drone,
        "total_biaya": trx_record["total_biaya"],
        "status": "pending",
        "sisa_stok": sisa_stok if sisa_stok is not None else 0,
        "mode_proteksi_lock": USE_LOCK,
        "message": "Transaksi diproses di latar belakang (pending -> processing -> completed)",
    }


@router.get(
    "/transactions",
    response_model=list[TransactionDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar semua transaksi (mendukung filter ?status=pending)",
)
async def list_transactions(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter opsional berdasarkan status transaksi: pending, processing, completed, failed",
    )
):
    """
    Mengambil daftar seluruh transaksi penukaran baterai secara asinkron.
    Mendukung filter query parameter ?status=pending (atau processing/completed/failed).
    """
    return await db.get_all_transactions(status_filter=status_filter)


@router.get(
    "/transactions/{id}",
    response_model=TransactionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Detail satu transaksi beserta status terkininya",
)
async def get_transaction_detail(id: int):
    """
    Memantau status terkini dari suatu transaksi (pending -> processing -> completed)
    berdasarkan ID transaksi. Mengembalikan 404 Not Found jika ID tidak ditemukan.
    """
    trx = await db.get_transaction_by_id(id)
    if not trx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaksi dengan ID {id} tidak ditemukan.",
        )
    return trx
