"""Server web lokal: halaman satu file, API JSON, dan penyajian audio."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import traceback
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path

from . import __version__, config
from .engine import Mesin
from .errors import InputTidakValid, Kesalahan
from .share import bagikan_file
from .validation import permintaan_dari_json

BATAS_JSON = 1_000_000


@dataclass
class Aplikasi:
    mesin: Mesin
    folder: Path
    halaman: str
    bagikan_aktif: bool


def buat_halaman(bagikan_aktif: bool, mp3_aktif: bool) -> str:
    templat = (files("bacakan") / "templates" / "index.html").read_text(encoding="utf-8")
    return (
        templat.replace("__VOICES__", json.dumps(list(config.VOICES)))
        .replace("__SPEED__", str(config.DEFAULT_SPEED))
        .replace("__STEPS__", str(config.DEFAULT_TOTAL_STEPS))
        .replace("__DEFAULT_VOICE__", config.DEFAULT_VOICE)
        .replace("__MP3__", "true" if mp3_aktif else "false")
        .replace("__SHARE__", "true" if bagikan_aktif else "false")
        .replace("__VERSION__", __version__)
    )


def file_bagikan(folder: Path, nama: object) -> Path:
    nama = str(nama or "").strip()
    if (
        not nama
        or Path(nama).name != nama
        or nama.startswith(".")
        or Path(nama).suffix.lower() not in config.AUDIO_MIME
    ):
        raise InputTidakValid("Nama file tidak valid.")
    folder = Path(folder).resolve()
    path = (folder / nama).resolve()
    if not path.is_relative_to(folder) or not path.is_file():
        raise InputTidakValid("File tidak ditemukan di folder output.")
    return path


class ServerBacakan(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, alamat, aplikasi: Aplikasi):
        super().__init__(alamat, Penangan)
        self.app = aplikasi


class Penangan(BaseHTTPRequestHandler):
    server_version = "Bacakan/" + __version__

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

    def kirim(self, status: int, body: bytes, tipe: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipe)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def kirim_json(self, status: int, obj: dict) -> None:
        self.kirim(status, json.dumps(obj).encode(), "application/json; charset=utf-8")

    def baca_json(self) -> dict:
        panjang = int(self.headers.get("Content-Length") or 0)
        if panjang <= 0 or panjang > BATAS_JSON:
            raise InputTidakValid("Data permintaan tidak valid.")
        try:
            data = json.loads(self.rfile.read(panjang).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise InputTidakValid("Format data permintaan tidak valid.")
        if not isinstance(data, dict):
            raise InputTidakValid("Data permintaan tidak valid.")
        return data

    def do_GET(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self.kirim(
                200, self.server.app.halaman.encode(), "text/html; charset=utf-8"
            )
            return
        if path.startswith("/audio/"):
            self.sajikan_audio(urllib.parse.unquote(path[len("/audio/"):]))
            return
        self.kirim_json(404, {"pesan": "Tidak ditemukan."})

    def sajikan_audio(self, nama: str) -> None:
        ekstensi = Path(nama).suffix.lower()
        if (
            not nama
            or nama != Path(nama).name
            or nama.startswith(".")
            or ekstensi not in config.AUDIO_MIME
        ):
            self.kirim_json(404, {"pesan": "File tidak ditemukan."})
            return
        folder = Path(self.server.app.folder).resolve()
        path = (folder / nama).resolve()
        if not path.is_relative_to(folder) or not path.is_file():
            self.kirim_json(404, {"pesan": "File tidak ditemukan."})
            return
        biner = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", config.AUDIO_MIME[ekstensi])
        self.send_header("Content-Length", str(len(biner)))
        self.send_header("Content-Disposition", f'inline; filename="{nama}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(biner)

    def do_POST(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        app = self.server.app
        try:
            data = self.baca_json()
            if path == "/api/sintesis":
                permintaan = permintaan_dari_json(data, app.mesin.mp3_tersedia)
                hasil = app.mesin.sintesis(permintaan, app.folder)
                jawaban = {
                    "nama": hasil.nama,
                    "url": "/audio/" + urllib.parse.quote(hasil.nama),
                    "ukuran": hasil.ukuran,
                    "durasi": hasil.durasi,
                    "suara": hasil.suara,
                    "format": hasil.format_,
                }
            elif path == "/api/bagikan":
                if not app.bagikan_aktif:
                    raise InputTidakValid("Fitur bagikan dimatikan di server ini.")
                path_file = file_bagikan(app.folder, data.get("nama"))
                jawaban = {"link": bagikan_file(path_file)}
            else:
                self.kirim_json(404, {"pesan": "Tidak ditemukan."})
                return
        except InputTidakValid as galat:
            self.kirim_json(400, {"pesan": str(galat)})
            return
        except Kesalahan as galat:
            self.kirim_json(400, {"pesan": str(galat)})
            return
        except Exception as galat:
            print(f"KESALAHAN: {galat}", file=sys.stderr)
            traceback.print_exc()
            self.kirim_json(
                500,
                {"pesan": "Terjadi kesalahan di server. Cek log terminal untuk detail."},
            )
            return
        self.kirim_json(200, jawaban)


def _siapkan_keluaran() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass


def main() -> int:
    _siapkan_keluaran()
    parser = argparse.ArgumentParser(
        prog="bacakan",
        description="Jalankan antarmuka web Bacakan di komputer sendiri.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Alamat bind (default 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Port server (default 8000).")
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Folder hasil audio (default: ./outputs).",
    )
    parser.add_argument(
        "--model-dir",
        default=None,
        help="Folder model Supertonic kalau sudah diunduh manual.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Buka browser otomatis setelah server siap.",
    )
    parser.add_argument(
        "--no-share",
        action="store_true",
        help="Matikan tombol bagikan ke getshared.",
    )
    argumen = parser.parse_args()

    folder = Path(argumen.output_dir).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)

    print("Menyiapkan model Supertonic. Pada pemakaian pertama ini bisa memakan waktu...")
    mesin = Mesin(model_dir=argumen.model_dir)
    print("Model siap. Bahasa: Indonesia.")
    print("Format: " + ("WAV dan MP3." if mesin.mp3_tersedia else "WAV saja (ffmpeg tidak ditemukan)."))
    print("Bagikan ke getshared: " + ("aktif." if not argumen.no_share else "dimatikan."))
    print(f"Folder hasil: {folder}")

    app = Aplikasi(
        mesin=mesin,
        folder=folder,
        halaman=buat_halaman(
            bagikan_aktif=not argumen.no_share, mp3_aktif=mesin.mp3_tersedia
        ),
        bagikan_aktif=not argumen.no_share,
    )
    try:
        server = ServerBacakan((argumen.host, argumen.port), app)
    except OSError as galat:
        print(
            f"Gagal membuka {argumen.host}:{argumen.port} ({galat}). "
            "Coba port lain dengan --port.",
            file=sys.stderr,
        )
        return 1

    alamat = f"http://{argumen.host}:{argumen.port}"
    print(f"Buka {alamat} di browser. Tekan Ctrl+C untuk berhenti.")
    if argumen.host not in ("127.0.0.1", "localhost", "::1"):
        print(
            "PERHATIAN: server terbuka ke jaringan dan tidak punya login. "
            "Hanya pakai di jaringan tepercaya."
        )
    if argumen.open:
        threading.Timer(1.0, webbrowser.open, args=[alamat]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
