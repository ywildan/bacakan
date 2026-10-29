"""Versi terminal: interaktif, atau sekali jalan lewat argumen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config
from .engine import Hasil, Mesin
from .errors import InputTidakValid, Kesalahan
from .naming import nama_default, validasi_nama, validasi_nama_opsional
from .validation import (
    susun_permintaan,
    validasi_format,
    validasi_speed,
    validasi_steps,
    validasi_suara,
)


def ukuran_manusia(jumlah_byte: int) -> str:
    if jumlah_byte >= 1024 * 1024:
        return f"{jumlah_byte / (1024 * 1024):.2f} MB"
    return f"{jumlah_byte / 1024:.1f} KB"


def baca_file_teks(path: Path) -> str:
    path = Path(path).expanduser()
    if not path.exists():
        raise InputTidakValid(f"File tidak ditemukan: {path}")
    if path.is_dir():
        raise InputTidakValid(f"'{path}' adalah folder, bukan file teks.")
    try:
        isi = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise InputTidakValid(f"File '{path}' tidak bisa dibaca sebagai teks UTF-8.")
    except OSError as galat:
        raise InputTidakValid(f"Gagal membaca file '{path}': {galat}")
    if not isi.strip():
        raise InputTidakValid(f"Isi file '{path}' kosong.")
    return isi.strip()


def cetak_hasil(hasil: Hasil) -> None:
    print(f"File tersimpan: {hasil.path}")
    print(f"Ukuran: {ukuran_manusia(hasil.ukuran)} ({hasil.ukuran} byte)")
    print(f"Durasi: {hasil.durasi:.2f} detik")
    print(f"Suara: {hasil.suara}, format: {hasil.format_}")


def tanya_suara(default: str) -> str:
    print("\nSuara tersedia: " + " ".join(config.VOICES) + ".")
    while True:
        jawab = input(f"Suara [{default}]: ").strip()
        if not jawab:
            return default
        try:
            return validasi_suara(jawab)
        except InputTidakValid as galat:
            print(galat)


def tanya_format(default: str, mp3_tersedia: bool) -> str:
    keterangan = "wav (lossless) atau mp3 (kecil)"
    if not mp3_tersedia:
        keterangan += ". MP3 tidak tersedia karena ffmpeg tidak ditemukan"
    print(f"\nFormat: {keterangan}.")
    while True:
        jawab = input(f"Format [{default}]: ").strip()
        if not jawab:
            return default
        try:
            return validasi_format(jawab, mp3_tersedia)
        except InputTidakValid as galat:
            print(galat)


def tanya_teks() -> str:
    while True:
        print(
            "\nKetik teks (boleh beberapa baris) lalu akhiri dengan baris berisi END,"
            "\natau ketik path file .txt untuk membacanya dari file."
        )
        baris = input("Teks: ")
        calon = baris.strip()
        if calon.lower().endswith(".txt"):
            try:
                return baca_file_teks(Path(calon))
            except InputTidakValid as galat:
                print(galat)
                continue

        kumpulan = []
        if calon.lower() != "end":
            kumpulan.append(baris)
            while True:
                baris = input("... ")
                if baris.strip().lower() == "end":
                    break
                kumpulan.append(baris)

        teks = "\n".join(kumpulan).strip()
        if teks:
            return teks
        print("Teks kosong. Silakan ulangi.")


def tanya_nama(default: str) -> str:
    while True:
        jawab = input(f"Nama file tanpa ekstensi [{default}]: ").strip()
        if not jawab:
            return ""
        try:
            return validasi_nama(jawab)
        except InputTidakValid as galat:
            print(galat)


def tanya_speed(default: float) -> float:
    while True:
        jawab = input(f"Speed [{default:g}]: ").strip()
        if not jawab:
            return default
        try:
            return validasi_speed(jawab)
        except InputTidakValid as galat:
            print(galat)


def tanya_steps(default: int) -> int:
    while True:
        jawab = input(f"Total steps [{default}]: ").strip()
        if not jawab:
            return default
        try:
            return validasi_steps(jawab)
        except InputTidakValid as galat:
            print(galat)


def buat_secara_interaktif(mesin: Mesin, folder: Path, bawaan: dict) -> None:
    suara = tanya_suara(bawaan["suara"])
    format_ = tanya_format(bawaan["format"], mesin.mp3_tersedia)
    teks = tanya_teks()
    nama = tanya_nama(bawaan["nama"] or nama_default(format_).rsplit(".", 1)[0])
    speed = tanya_speed(bawaan["speed"])
    steps = tanya_steps(bawaan["steps"])

    permintaan = susun_permintaan(
        teks=teks,
        suara=suara,
        nama=nama,
        speed=speed,
        steps=steps,
        format_=format_,
        mp3_tersedia=mesin.mp3_tersedia,
    )
    print(f"\nMembuat suara {permintaan.suara} ({len(permintaan.teks)} karakter)...")
    cetak_hasil(mesin.sintesis(permintaan, folder))


def jalankan_interaktif(mesin: Mesin, folder: Path, bawaan: dict) -> int:
    print("\nKetik 'keluar' untuk berhenti, atau Ctrl+C kapan saja.")
    while True:
        jawab = input(
            "\nTekan Enter untuk membuat suara baru, atau ketik 'keluar': "
        ).strip()
        if jawab.lower() == "keluar":
            print("Sampai jumpa!")
            return 0
        if jawab:
            print("Perintah tidak dikenal. Tekan Enter untuk lanjut atau ketik 'keluar'.")
            continue
        try:
            buat_secara_interaktif(mesin, folder, bawaan)
        except Kesalahan as galat:
            print(f"Gagal membuat suara: {galat}")


def jalankan_sekali(mesin: Mesin, folder: Path, argumen) -> int:
    if argumen.text is not None:
        teks = argumen.text
    else:
        teks = baca_file_teks(Path(argumen.text_file))

    permintaan = susun_permintaan(
        teks=teks,
        suara=argumen.voice,
        nama=argumen.out,
        speed=argumen.speed,
        steps=argumen.steps,
        format_=argumen.format,
        mp3_tersedia=mesin.mp3_tersedia,
    )
    cetak_hasil(mesin.sintesis(permintaan, folder))
    return 0


def _siapkan_keluaran() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass


def main() -> int:
    _siapkan_keluaran()
    parser = argparse.ArgumentParser(
        prog="bacakan-cli",
        description="Buat suara Bahasa Indonesia dari terminal.",
    )
    parser.add_argument(
        "--output-dir", default="outputs", help="Folder hasil audio (default: ./outputs)."
    )
    parser.add_argument("--model-dir", default=None, help="Folder model Supertonic.")
    parser.add_argument("--voice", default=None, help="Suara, misalnya F1 atau M2.")
    parser.add_argument("--speed", default=None, help="Kecepatan bicara, default 1.05.")
    parser.add_argument("--steps", default=None, help="Total steps, default 8.")
    parser.add_argument("--format", default=None, help="wav atau mp3, default wav.")
    sumber = parser.add_mutually_exclusive_group()
    sumber.add_argument("--text", default=None, help="Teks untuk mode sekali jalan.")
    sumber.add_argument(
        "--text-file", default=None, help="File .txt untuk mode sekali jalan."
    )
    parser.add_argument(
        "--out", default=None, help="Nama file tanpa ekstensi untuk mode sekali jalan."
    )
    parser.add_argument(
        "--list-voices", action="store_true", help="Tampilkan daftar suara lalu keluar."
    )
    argumen = parser.parse_args()

    if argumen.list_voices:
        print(" ".join(config.VOICES))
        return 0

    folder = Path(argumen.output_dir).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)

    sekali_jalan = argumen.text is not None or argumen.text_file is not None
    try:
        print("Menyiapkan model Supertonic. Pada pemakaian pertama ini bisa memakan waktu...")
        mesin = Mesin(model_dir=argumen.model_dir)
        print("Model siap. Bahasa: Indonesia.\n")

        if sekali_jalan:
            return jalankan_sekali(mesin, folder, argumen)

        bawaan = {
            "suara": validasi_suara(argumen.voice) if argumen.voice else config.DEFAULT_VOICE,
            "format": validasi_format(argumen.format, mesin.mp3_tersedia)
            if argumen.format
            else config.DEFAULT_FORMAT,
            "nama": validasi_nama_opsional(argumen.out),
            "speed": validasi_speed(argumen.speed) if argumen.speed else config.DEFAULT_SPEED,
            "steps": validasi_steps(argumen.steps) if argumen.steps else config.DEFAULT_TOTAL_STEPS,
        }
        return jalankan_interaktif(mesin, folder, bawaan)
    except (InputTidakValid, Kesalahan) as galat:
        print(f"Gagal: {galat}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nDihentikan. Sampai jumpa!")
        return 0
    except EOFError:
        print("\nInput selesai. Sampai jumpa!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
