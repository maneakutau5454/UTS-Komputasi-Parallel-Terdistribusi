"""
test_race.py - Skrip Pengujian Mandiri Race Condition (Sub-bagian B3)
Mengeksekusi 2 request HTTP POST secara serentak dalam milidetik yang sama
ke endpoint /transactions ketika stok resource ID=1 tersisa 1 unit.
"""

import asyncio
import httpx


async def main():
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/transactions"
    payload = {"item_id": 1, "qty": 1}

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Cek stok awal sebelum kedua request konkuren dikirimkan
        info_awal = await client.get(f"{base_url}/resource/1")
        stok_awal = info_awal.json().get("stok") if info_awal.status_code == 200 else "?"

        print("=" * 75)
        print("PENGUJIAN KONKURENSI & RACE CONDITION (2 REQUEST SERENTAK)")
        print(f"Target Endpoint : POST {url}")
        print(f"Payload         : {payload}")
        print(f"Stok Awal ID=1  : {stok_awal}")
        print("-" * 75)

        # Kirim dua request secara serentak dalam milidetik yang sama
        req1 = client.post(url, json=payload)
        req2 = client.post(url, json=payload)

        res1, res2 = await asyncio.gather(req1, req2)

        print("Respon Request 1:", res1.status_code, res1.json())
        print("Respon Request 2:", res2.status_code, res2.json())

        # Cek stok akhir pada basis data setelah kedua request selesai diproses
        info_akhir = await client.get(f"{base_url}/resource/1")
        if info_akhir.status_code == 200:
            data_akhir = info_akhir.json()
            stok_akhir = data_akhir.get("stok")
            print("-" * 75)
            print(f"Nilai Stok Akhir Resource ID=1 ({data_akhir.get('nama')}): {stok_akhir}")
            if isinstance(stok_akhir, int) and stok_akhir < 0:
                print("STATUS ANALISIS : [TAHAP 1 - TANPA LOCK] Terjadi Race Condition (Overselling / Stok Minus!)")
            else:
                print("STATUS ANALISIS : [TAHAP 2 - DENGAN LOCK] Aman! asyncio.Lock mencegah Overselling (409 Conflict).")
        print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())
