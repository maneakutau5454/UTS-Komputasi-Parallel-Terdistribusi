"""
locustfile.py - Skrip Pengujian Beban (Load Testing & Benchmark) menggunakan Locust
Sub-bagian C1 (10 Poin): Perbandingan Performa 1 Worker vs 4 Worker

Mendefinisikan dua skenario pengujian beban sesuai dokumen soal UTS:
1. Skenario Read  (ReadResourceUser)     : GET /resource       - 100 request, konkurensi 20
2. Skenario Write (WriteTransactionUser) : POST /transactions  - 50 request,  konkurensi 10

Cara eksekusi otomatis via terminal (headless):
- Skenario Read (100 request, 20 konkurensi):
  locust -f locustfile.py --headless -u 20 -r 20 --host http://127.0.0.1:8000 ReadResourceUser

- Skenario Write (50 request, 10 konkurensi):
  locust -f locustfile.py --headless -u 10 -r 10 --host http://127.0.0.1:8000 WriteTransactionUser
"""

import os
import random
import time
import gevent
from locust import HttpUser, between, events, tag, task

# Variabel pelacak jumlah request agar berhenti tepat pada target (100 Read / 50 Write)
_dispatched_requests = 0
_completed_requests = 0
_start_time = 0.0
_end_time = 0.0
_active_scenario_name = "Benchmark"
_target_limit = int(os.getenv("TARGET_REQUESTS", "0"))


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Mencatat waktu mulai pengujian beban."""
    global _dispatched_requests, _completed_requests, _start_time, _end_time
    _dispatched_requests = 0
    _completed_requests = 0
    _start_time = time.perf_counter()
    _end_time = 0.0


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """
    Menampilkan ringkasan tabel metrik benchmark (Total Waktu, Throughput, Rata-rata Latensi)
    agar mudah dicatat ke tabel Bagian C1 pada laporan_uts.pdf.
    """
    global _end_time
    if _end_time <= 0.0:
        _end_time = time.perf_counter()

    total_waktu = max(_end_time - _start_time, 0.001)
    stats = environment.stats.total
    total_reqs = stats.num_requests
    avg_latency_ms = stats.avg_response_time
    throughput_rps = total_reqs / total_waktu if total_waktu > 0 else 0.0

    print("\n" + "=" * 78)
    print("RINGKASAN METRIK BENCHMARK (UNTUK TABEL C1 LAPORAN UTS)")
    print("=" * 78)
    print(f"  Skenario Uji      : {_active_scenario_name}")
    print(f"  Jumlah Request    : {total_reqs} request (Gagal: {stats.num_failures})")
    print(f"  Total Waktu       : {total_waktu:.3f} detik")
    print(f"  Throughput        : {throughput_rps:.2f} req/detik (RPS)")
    print(f"  Rata-rata Latensi : {avg_latency_ms:.2f} ms")
    print("=" * 78 + "\n")


class ReadResourceUser(HttpUser):
    """
    Skenario Read: Menguji endpoint GET /resource?skip=0&limit=10
    Target standar soal C1: 100 request dengan konkurensi 20 user.
    """

    wait_time = between(0.01, 0.05)

    @tag("read")
    @task
    def get_resources(self):
        global _dispatched_requests, _completed_requests, _end_time, _active_scenario_name
        _active_scenario_name = "GET /resource (Skenario Read)"
        target = _target_limit if _target_limit > 0 else 100

        if _dispatched_requests >= target:
            gevent.sleep(0.1)
            return

        _dispatched_requests += 1
        with self.client.get(
            "/resource?skip=0&limit=10",
            name="GET /resource",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status HTTP tidak sesuai: {response.status_code}")

        _completed_requests += 1
        if _completed_requests >= target:
            _end_time = time.perf_counter()
            if self.environment.runner:
                self.environment.runner.quit()


class WriteTransactionUser(HttpUser):
    """
    Skenario Write: Menguji endpoint POST /transactions
    Target standar soal C1: 50 request dengan konkurensi 10 user.
    """

    wait_time = between(0.01, 0.05)

    @tag("write")
    @task
    def post_transaction(self):
        global _dispatched_requests, _completed_requests, _end_time, _active_scenario_name
        _active_scenario_name = "POST /transactions (Skenario Write)"
        target = _target_limit if _target_limit > 0 else 50

        if _dispatched_requests >= target:
            gevent.sleep(0.1)
            return

        _dispatched_requests += 1
        # Pilih salah satu dari 10 resource modul baterai awal secara acak
        item_id = random.randint(1, 10)
        payload = {
            "item_id": item_id,
            "qty": 1,
            "kode_drone": f"DRN-BENCH-{random.randint(100, 999)}",
        }

        with self.client.post(
            "/transactions",
            json=payload,
            name="POST /transactions",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201, 202):
                response.success()
            else:
                response.failure(f"Gagal membuat transaksi: {response.status_code}")

        _completed_requests += 1
        if _completed_requests >= target:
            _end_time = time.perf_counter()
            if self.environment.runner:
                self.environment.runner.quit()
