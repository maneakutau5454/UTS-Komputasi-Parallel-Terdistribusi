"""
seed.py - Skrip Inisialisasi Data Awal (Minimal 10 Baris Data)
Tema Aplikasi: AeroSwap - Sistem Manajemen & Alokasi Modul Baterai Tukar-Cepat
               (Battery Swapping Station) untuk Armada Drone Logistik

Cara penggunaan:
1. Inisialisasi / reset 12 data awal (stok penuh untuk uji CRUD & Locust Benchmark):
   python seed.py

2. Atur stok resource ID=1 menjadi 1 (khusus persiapan uji Race Condition B3):
   python seed.py --set-race-stock
"""

import asyncio
import sys
import aiosqlite
import database as db

INITIAL_BATTERY_MODULES = [
    {
        "kode_seri": "BAT-LIPO-6S-22A",
        "nama": "AeroPack LiPo 6S 22000mAh Heavy-Lift",
        "kategori": "Heavy-Cargo",
        "kapasitas_wh": 488.4,
        "lokasi_stasiun": "Stasiun-Pontianak-Utara",
        "harga": 85000.0,
        "stok": 250,
    },
    {
        "kode_seri": "BAT-SLD-8S-30A",
        "nama": "AeroPack Solid-State 8S 30000mAh Long-Endurance",
        "kategori": "Medical-Express",
        "kapasitas_wh": 888.0,
        "lokasi_stasiun": "Stasiun-RSUD-Soedarso",
        "harga": 125000.0,
        "stok": 200,
    },
    {
        "kode_seri": "BAT-LIION-4S-12A",
        "nama": "SkyCell Li-Ion 4S 12000mAh Agile-Courier",
        "kategori": "Urban-Parcel",
        "kapasitas_wh": 177.6,
        "lokasi_stasiun": "Stasiun-Pontianak-Kota",
        "harga": 45000.0,
        "stok": 300,
    },
    {
        "kode_seri": "BAT-LIPO-6S-16A",
        "nama": "TerraScan LiPo 6S 16000mAh LiDAR-Survey",
        "kategori": "Mapping-Geospasial",
        "kapasitas_wh": 355.2,
        "lokasi_stasiun": "Stasiun-Kubu-Raya",
        "harga": 70000.0,
        "stok": 180,
    },
    {
        "kode_seri": "BAT-HV-12S-28A",
        "nama": "TitanVolt HV 12S 28000mAh Industrial-Cargo",
        "kategori": "Heavy-Cargo",
        "kapasitas_wh": 1243.2,
        "lokasi_stasiun": "Stasiun-Pelabuhan-Dwikora",
        "harga": 160000.0,
        "stok": 150,
    },
    {
        "kode_seri": "BAT-LIFE-6S-18A",
        "nama": "EcoFlight LiFePO4 6S 18000mAh Patrol-Thermal",
        "kategori": "Forest-Fire-Patrol",
        "kapasitas_wh": 345.6,
        "lokasi_stasiun": "Stasiun-Rasau-Jaya",
        "harga": 65000.0,
        "stok": 220,
    },
    {
        "kode_seri": "BAT-SLD-6S-25A",
        "nama": "CryoMed Solid-State 6S 25000mAh Cold-Chain",
        "kategori": "Medical-Express",
        "kapasitas_wh": 555.0,
        "lokasi_stasiun": "Stasiun-Bumi-Khatulistiwa",
        "harga": 95000.0,
        "stok": 190,
    },
    {
        "kode_seri": "BAT-LIPO-4S-10A",
        "nama": "SwiftWing LiPo 4S 10000mAh Rapid-Inspect",
        "kategori": "Grid-Inspection",
        "kapasitas_wh": 148.0,
        "lokasi_stasiun": "Stasiun-Siantan-Hilir",
        "harga": 40000.0,
        "stok": 280,
    },
    {
        "kode_seri": "BAT-HV-10S-24A",
        "nama": "AgriPulse HV 10S 24000mAh Sprayer-Pro",
        "kategori": "Smart-Agriculture",
        "kapasitas_wh": 888.0,
        "lokasi_stasiun": "Stasiun-Sungai-Kakap",
        "harga": 110000.0,
        "stok": 175,
    },
    {
        "kode_seri": "BAT-LIION-6S-20A",
        "nama": "MarineGuard Li-Ion 6S 20000mAh Coastal-Relay",
        "kategori": "Maritime-Telemetry",
        "kapasitas_wh": 444.0,
        "lokasi_stasiun": "Stasiun-Jungkat-Pesisir",
        "harga": 80000.0,
        "stok": 160,
    },
    {
        "kode_seri": "BAT-SLD-12S-35A",
        "nama": "AeroMax Solid-State 12S 35000mAh Inter-Island",
        "kategori": "Heavy-Cargo",
        "kapasitas_wh": 1554.0,
        "lokasi_stasiun": "Stasiun-Supadio-Hub",
        "harga": 195000.0,
        "stok": 120,
    },
    {
        "kode_seri": "BAT-LIPO-6S-14A",
        "nama": "OrthoMap LiPo 6S 14000mAh Photogrammetry",
        "kategori": "Mapping-Geospasial",
        "kapasitas_wh": 310.8,
        "lokasi_stasiun": "Stasiun-Kampus-UMPontianak",
        "harga": 60000.0,
        "stok": 210,
    },
]


async def seed_database() -> None:
    """Mengisi basis data SQLite dengan 12 baris data awal modul baterai AeroSwap."""
    await db.init_db()
    conn = await db.get_db_connection()
    try:
        await conn.execute("DELETE FROM transactions;")
        await conn.execute("DELETE FROM resources;")
        await conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('resources', 'transactions');"
        )

        for item in INITIAL_BATTERY_MODULES:
            await conn.execute(
                """
                INSERT INTO resources (
                    kode_seri, nama, kategori, kapasitas_wh, lokasi_stasiun, harga, stok
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["kode_seri"],
                    item["nama"],
                    item["kategori"],
                    item["kapasitas_wh"],
                    item["lokasi_stasiun"],
                    item["harga"],
                    item["stok"],
                ),
            )
        await conn.commit()

        cursor = await conn.execute("SELECT id, kode_seri, nama, stok FROM resources;")
        rows = await cursor.fetchall()
        print("=" * 72)
        print("INISIALISASI DATA AWAL AEROSWAP BERHASIL (TOTAL:", len(rows), "MODUL BATERAI)")
        print("=" * 72)
        for r in rows:
            print(f"  [ID={r['id']:02d}] {r['kode_seri']} | {r['nama']} | Stok: {r['stok']}")
        print("=" * 72)
    finally:
        await conn.close()


async def set_race_condition_stock() -> None:
    """
    Mengatur nilai stok resource ID=1 menjadi tepat 1 pada basis data SQLite
    untuk pengujian Race Condition (Sub-bagian B3 Tahap 1 & Tahap 2).
    """
    await db.init_db()
    updated = await db.set_stok(1, 1)
    if not updated:
        await seed_database()
        await db.set_stok(1, 1)

    item = await db.get_resource_by_id(1)
    print("=" * 72)
    print("PERSIAPAN UJI RACE CONDITION (B3): STOK RESOURCE ID=1 DIATUR MENJADI 1")
    print("=" * 72)
    if item:
        print(f"  ID Resource : {item['id']}")
        print(f"  Nama Modul  : {item['nama']} ({item['kode_seri']})")
        print(f"  Stok Awal   : {item['stok']} unit")
    print("=" * 72)


if __name__ == "__main__":
    if "--set-race-stock" in sys.argv:
        asyncio.run(set_race_condition_stock())
    else:
        asyncio.run(seed_database())
