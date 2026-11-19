"""
routes/resource.py - Endpoint CRUD Resource Utama (Modul Baterai Pintar AeroSwap)
Sub-bagian B1 (20 Poin)

Seluruh handler menggunakan 'async def' dan memanggil operasi basis data
'aiosqlite' menggunakan 'await' agar tidak memblokir event loop utama FastAPI.
"""

from fastapi import APIRouter, HTTPException, Query, status
import database as db
from models import (
    DeleteResourceResponse,
    ResourceCreate,
    ResourceResponse,
    ResourceUpdate,
)

router = APIRouter(tags=["Resource Utama (Modul Baterai AeroSwap)"])


@router.get(
    "/resource",
    response_model=list[ResourceResponse],
    status_code=status.HTTP_200_OK,
    summary="Daftar semua modul baterai (mendukung paginasi ?skip=0&limit=10)",
)
async def list_resources(
    skip: int = Query(0, ge=0, description="Jumlah baris awal yang dilewati (offset)"),
    limit: int = Query(10, ge=1, le=100, description="Batas jumlah baris yang diambil"),
):
    """
    Mengambil daftar modul baterai yang terdaftar di stasiun pengisian AeroSwap
    secara asinkron (non-blocking I/O) dengan parameter wajib ?skip=0&limit=10.
    """
    items = await db.get_all_resources(skip=skip, limit=limit)
    return items


@router.get(
    "/resource/{id}",
    response_model=ResourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Detail satu modul baterai berdasarkan ID",
)
async def get_resource(id: int):
    """
    Mengambil informasi lengkap satu modul baterai berdasarkan ID.
    Mengembalikan 404 Not Found apabila ID tidak ditemukan pada SQLite.
    """
    item = await db.get_resource_by_id(id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modul baterai dengan ID {id} tidak ditemukan.",
        )
    return item


@router.post(
    "/resource",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah modul baterai baru ke basis data",
)
async def create_new_resource(payload: ResourceCreate):
    """
    Menambahkan resource modul baterai baru setelah divalidasi oleh Pydantic.
    Mengembalikan kode status 201 Created beserta data yang baru disimpan.
    """
    created = await db.create_resource(payload.model_dump())
    return created


@router.put(
    "/resource/{id}",
    response_model=ResourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Perbarui data modul baterai berdasarkan ID",
)
async def update_existing_resource(id: int, payload: ResourceUpdate):
    """
    Memperbarui seluruh atribut modul baterai berdasarkan ID secara asinkron
    dan mengembalikan data terbaru (200 OK) atau 404 Not Found jika tidak ada.
    """
    updated = await db.update_resource(id, payload.model_dump())
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gagal memperbarui: Modul baterai dengan ID {id} tidak ditemukan.",
        )
    return updated


@router.delete(
    "/resource/{id}",
    response_model=DeleteResourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Hapus permanen (hard delete) modul baterai berdasarkan ID",
)
async def delete_existing_resource(id: int):
    """
    Menghapus permanen (hard delete) baris modul baterai dari basis data SQLite.
    Mengembalikan 200 OK jika berhasil dihapus atau 404 Not Found jika ID tidak ditemukan.
    """
    deleted = await db.delete_resource(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gagal menghapus: Modul baterai dengan ID {id} tidak ditemukan.",
        )
    return {
        "message": f"Modul baterai dengan ID {id} berhasil dihapus permanen (hard delete).",
        "deleted_id": id,
    }
