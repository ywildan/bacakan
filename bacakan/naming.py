"""Aturan nama file yang aman di Linux, macOS, dan Windows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .errors import NamaTidakValid

EKTENSI = (".wav", ".mp3")
KARAKTER_TERLARANG = frozenset('<>:"/\\|?*')
NAMA_PERANGKAT = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
)
PANJANG_MAKS = 120


def lepas_ekstensi(nama: str) -> str:
    hasil = nama.strip()
    for ekstensi in EKTENSI:
        if hasil.lower().endswith(ekstensi):
            return hasil[: -len(ekstensi)].strip()
    return hasil


def validasi_nama(nama: str) -> str:
    dasar = lepas_ekstensi(str(nama or ""))
    if not dasar:
        raise NamaTidakValid("Nama file tidak boleh kosong.")
    if len(dasar) > PANJANG_MAKS:
        raise NamaTidakValid(
            f"Nama file terlalu panjang (maksimal {PANJANG_MAKS} karakter)."
        )
    if dasar in {".", ".."}:
        raise NamaTidakValid("Nama file tidak boleh '.' atau '..'.")
    if dasar.startswith("."):
        raise NamaTidakValid("Nama file tidak boleh diawali titik.")
    if any(karakter in KARAKTER_TERLARANG for karakter in dasar):
        raise NamaTidakValid(
            'Nama file tidak boleh memakai karakter < > : " / \\ | ? *.'
        )
    if any(ord(karakter) < 32 for karakter in dasar):
        raise NamaTidakValid("Nama file tidak boleh mengandung karakter kontrol.")
    if dasar != dasar.rstrip(" ."):
        raise NamaTidakValid("Nama file tidak boleh diakhiri titik atau spasi.")
    if dasar.split(".")[0].strip().lower() in NAMA_PERANGKAT:
        raise NamaTidakValid(
            f"'{dasar}' memakai nama khusus Windows. Silakan pilih nama lain."
        )
    return dasar


def validasi_nama_opsional(nama: object) -> str:
    teks = str(nama or "").strip()
    if not teks:
        return ""
    return validasi_nama(teks)


def nama_default(format_: str) -> str:
    return "output-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "." + format_


def path_keluaran(folder: Path, nama_dasar: str, format_: str) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if not nama_dasar:
        dasar = nama_default(format_)
        path = folder / dasar
        nomor = 2
        while path.exists():
            path = folder / f"{dasar[:-len(format_) - 1]}-{nomor}.{format_}"
            nomor += 1
        return path
    path = folder / f"{nama_dasar}.{format_}"
    if path.exists():
        raise NamaTidakValid(f"File '{path.name}' sudah ada. Pakai nama lain.")
    return path
