"""
main.py - Titik Masuk Utama Aplikasi REST API FastAPI
Tema Aplikasi: AeroSwap - Sistem Manajemen & Alokasi Modul Baterai Tukar-Cepat
               (Battery Swapping Station) untuk Armada Drone Logistik

Mata Kuliah  : Komputasi Paralel dan Terdistribusi (UTS Ganjil 2026/2027)
Program Studi: Teknik Informatika - Universitas Muhammadiyah Pontianak
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
import database as db
from routes import resource, transaction


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler asinkron: memastikan skema tabel SQLite (resources & transactions)
    telah diinisialisasi secara non-blocking sebelum server melayani request.
    """
    await db.init_db()
    yield


app = FastAPI(
    title="AeroSwap - Drone Battery Swapping & Allocation API",
    description=(
        "REST API Asinkron untuk Manajemen Inventaris & Transaksi Penukaran Modul Baterai "
        "Pintar (Smart Battery Swapping Station) Armada Drone Logistik.\n\n"
        "**Fitur Utama (UTS Komputasi Paralel & Terdistribusi):**\n"
        "- **B1 (CRUD Resource Utama)**: Operasi asinkron via `aiosqlite` & validasi `Pydantic`.\n"
        "- **B2 (Async Processing)**: Pemrosesan transaksi latar belakang via `BackgroundTasks` "
        "(`pending` -> `processing` -> `completed`).\n"
        "- **B3 (Thread/Async Safety)**: Pencegahan *race condition* (*overselling* stok baterai) "
        "menggunakan `asyncio.Lock`."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Registrasi router terpisah sesuai ketentuan B4 (Struktur Kode)
app.include_router(resource.router)
app.include_router(transaction.router)


@app.get("/", tags=["Info Sistem"])
async def root():
    """Endpoint informasi status server dan mode penguncian konkurensi."""
    return {
        "aplikasi": "AeroSwap - Sistem Manajemen & Alokasi Modul Baterai Tukar-Cepat Drone Logistik",
        "status": "online",
        "mode_asyncio_lock_aktif": transaction.USE_LOCK,
        "dokumentasi_swagger": "http://127.0.0.1:8000/docs",
    }
