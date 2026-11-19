"""
models.py - Skema Validasi Request & Serialisasi Response menggunakan Pydantic
Tema Aplikasi: AeroSwap - Sistem Manajemen & Alokasi Modul Baterai Tukar-Cepat
               (Battery Swapping Station) untuk Armada Drone Logistik
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# =====================================================================
# SKEMA PYDANTIC UNTUK RESOURCE UTAMA (MODUL BATERAI DRONE) - B1
# =====================================================================

class ResourceBase(BaseModel):
    """Skema dasar atribut modul baterai pintar pada stasiun AeroSwap."""

    kode_seri: str = Field(
        default="BAT-LIPO-6S-STD",
        min_length=3,
        max_length=50,
        description="Kode seri teknis modul baterai",
    )
    nama: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Nama lengkap modul baterai drone",
    )
    kategori: str = Field(
        ...,
        min_length=2,
        max_length=60,
        description="Kategori misi drone (misal: Heavy-Cargo, Medical-Express, Mapping-LiDAR)",
    )
    kapasitas_wh: float = Field(
        default=488.4,
        gt=0,
        description="Kapasitas energi modul baterai dalam satuan Watt-hour (Wh)",
    )
    lokasi_stasiun: str = Field(
        default="Stasiun-Pontianak-Kota",
        min_length=3,
        max_length=100,
        description="Lokasi stasiun pengisian/penukaran baterai (Docking Station)",
    )
    harga: float = Field(
        ...,
        gt=0,
        description="Biaya sewa/tukar per siklus terbang (Rp)",
    )
    stok: int = Field(
        ...,
        ge=0,
        description="Kuantitas unit baterai berstatus Full-Charged yang siap ditukar",
    )


class ResourceCreate(ResourceBase):
    """Skema request body untuk menambah resource modul baterai baru (POST /resource)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kode_seri": "BAT-HV-8S-30A",
                "nama": "AeroPack Solid-State 8S 30000mAh Ultra-Cargo",
                "kategori": "Heavy-Cargo",
                "kapasitas_wh": 888.0,
                "lokasi_stasiun": "Hub-Supadio-Aerospace",
                "harga": 120000.0,
                "stok": 15,
            }
        }
    )


class ResourceUpdate(ResourceBase):
    """Skema request body untuk memperbarui resource modul baterai (PUT /resource/{id})."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kode_seri": "BAT-HV-8S-30A",
                "nama": "AeroPack Solid-State 8S 30000mAh Ultra-Cargo (Rev.2)",
                "kategori": "Heavy-Cargo",
                "kapasitas_wh": 888.0,
                "lokasi_stasiun": "Hub-Supadio-Aerospace",
                "harga": 115000.0,
                "stok": 20,
            }
        }
    )


class ResourceResponse(BaseModel):
    """Skema serialisasi response untuk data resource modul baterai."""

    id: int
    kode_seri: str
    nama: str
    kategori: str
    kapasitas_wh: float
    lokasi_stasiun: str
    harga: float
    stok: int

    model_config = ConfigDict(from_attributes=True)


class DeleteResourceResponse(BaseModel):
    """Skema response saat resource berhasil dihapus permanen (hard delete)."""

    message: str
    deleted_id: int


# =====================================================================
# SKEMA PYDANTIC UNTUK TRANSAKSI ALOKASI/TUKAR BATERAI - B2 & B3
# =====================================================================

class TransactionCreate(BaseModel):
    """
    Skema request body untuk membuat transaksi penukaran baterai (POST /transactions).
    Mendukung payload standar {"item_id": 1, "qty": 1} untuk pengujian test_race.py
    maupun atribut tambahan kode_drone.
    """

    item_id: int = Field(
        ...,
        gt=0,
        description="ID resource modul baterai yang akan ditukar/dialokasikan",
    )
    qty: int = Field(
        ...,
        gt=0,
        description="Jumlah unit baterai yang diminta dalam transaksi ini",
    )
    kode_drone: str = Field(
        default="DRN-MED-PONTIANAK-01",
        min_length=2,
        max_length=60,
        description="Kode registrasi unit drone peminta penukaran baterai",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_id": 1,
                "qty": 1,
                "kode_drone": "DRN-MED-PONTIANAK-01",
            }
        }
    )


class TransactionAcceptedResponse(BaseModel):
    """
    Skema response instan (202 Accepted) saat transaksi berhasil dibuat
    dan dijadwalkan ke BackgroundTasks dengan status awal 'pending'.
    """

    id: int
    item_id: int
    qty: int
    kode_drone: str
    total_biaya: float
    status: str
    sisa_stok: int
    mode_proteksi_lock: bool
    message: str


class TransactionDetailResponse(BaseModel):
    """Skema response detail transaksi beserta status terkininya."""

    id: int
    item_id: int
    qty: int
    kode_drone: str
    total_biaya: float
    status: str
    created_at: str
    updated_at: str
    nama_resource: Optional[str] = None
    kode_seri: Optional[str] = None
    sisa_stok_resource: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
