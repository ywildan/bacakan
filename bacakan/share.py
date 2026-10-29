"""Unggah hasil audio ke getshared dengan percobaan ulang."""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request
import uuid
from http.cookiejar import CookieJar
from pathlib import Path

from . import config
from .errors import GangguanSementara, Kesalahan

LAYANAN = "https://getshared.com"
AGEN = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
BATAS_PERCOBAAN = 3
JEDA_DETIK = 1.5


def buat_formulir(fields, file_field=None) -> tuple[bytes, str]:
    batas = "----bacakan" + uuid.uuid4().hex
    isi = bytearray()
    for nama, nilai in fields:
        isi += (
            f"--{batas}\r\n"
            f'Content-Disposition: form-data; name="{nama}"\r\n\r\n'
        ).encode()
        isi += str(nilai).encode() + b"\r\n"
    if file_field:
        nama_field, nama_file, biner, tipe = file_field
        isi += (
            f"--{batas}\r\n"
            f'Content-Disposition: form-data; name="{nama_field}"; '
            f'filename="{nama_file}"\r\n'
            f"Content-Type: {tipe}\r\n\r\n"
        ).encode()
        isi += biner + b"\r\n"
    isi += f"--{batas}--\r\n".encode()
    return bytes(isi), f"multipart/form-data; boundary={batas}"


def panggil(alamat: str, url: str, body=None, tipe=None) -> dict:
    header = {
        "User-Agent": AGEN,
        "Referer": alamat + "/",
        "Accept": "application/json, */*",
        "Connection": "close",
    }
    if body is not None:
        header["Origin"] = alamat
    if tipe:
        header["Content-Type"] = tipe
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(CookieJar())
    )
    permintaan = urllib.request.Request(
        url, data=body, headers=header, method="POST" if body is not None else "GET"
    )
    try:
        with opener.open(permintaan, timeout=120) as respons:
            mentah = respons.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as galat:
        rincian = galat.read().decode("utf-8", "replace")[:200]
        if galat.code == 429 or galat.code >= 500:
            raise GangguanSementara(f"Layanan berbagi sedang sibuk (HTTP {galat.code}).")
        raise Kesalahan(f"getshared menolak permintaan (HTTP {galat.code}). {rincian}")
    except (OSError, http.client.HTTPException) as galat:
        alasan = getattr(galat, "reason", None) or galat or "tanpa keterangan"
        raise GangguanSementara(f"Koneksi ke getshared terputus ({alasan}).")
    try:
        return json.loads(mentah or "{}")
    except json.JSONDecodeError:
        raise Kesalahan("Jawaban getshared tidak bisa dibaca.")


def _unggah_sekali(nama: str, biner: bytes, tipe: str, alamat: str) -> str:
    info = panggil(alamat, alamat + "/upload/genid")
    upload_id = str(info.get("upload_id") or "")
    if not upload_id:
        raise Kesalahan("getshared tidak memberi upload_id.")

    body, tipe_form = buat_formulir(
        [
            ("upload_id", upload_id),
            ("email_from", ""),
            ("email_to[]", ""),
            ("message", ""),
            ("password", ""),
            ("destruct", "no"),
            ("share", "link"),
            ("expire", "2592000"),
            ("preview", "0"),
        ]
    )
    hasil = panggil(alamat, alamat + "/upload/register", body, tipe_form)
    kode = hasil.get("response")
    if kode != "ok":
        pesan = {
            "rate_limit": "Terlalu banyak unggahan dari jaringan ini. Coba lagi nanti.",
            "recaptcha": "Layanan berbagi butuh verifikasi. Coba lagi nanti.",
            "email": "Alamat email tidak valid.",
            "fields": "Formulir unggahan ditolak layanan berbagi.",
        }.get(kode, "Layanan berbagi menolak unggahan. Coba lagi.")
        raise Kesalahan(pesan)

    body, tipe_form = buat_formulir(
        [
            ("upload_id", upload_id),
            ("file_uid", f"{nama}_{int(time.time() * 1000)}"),
            ("original_path", nama),
        ],
        ("files[]", nama, biner, tipe),
    )
    hasil = panggil(alamat, alamat + "/upload", body, tipe_form)
    berkas = hasil.get("files")
    if isinstance(berkas, list) and berkas and isinstance(berkas[0], dict):
        if berkas[0].get("error"):
            raise Kesalahan(f"Layanan berbagi menolak file: {berkas[0]['error']}")

    body, tipe_form = buat_formulir([("upload_id", upload_id)])
    akhir = panggil(alamat, alamat + "/upload/complete", body, tipe_form)
    link = akhir.get("link")
    if link:
        return str(link)
    if akhir.get("status") == "success":
        return f"{alamat}/d/{upload_id}"
    raise Kesalahan(str(akhir.get("message") or "Unggahan gagal diselesaikan."))


def bagikan_file(
    path: str | Path,
    *,
    alamat: str = LAYANAN,
    batas: int = BATAS_PERCOBAAN,
    jeda: float = JEDA_DETIK,
    catat=print,
) -> str:
    path = Path(path)
    if not path.is_file():
        raise Kesalahan("File tidak ditemukan di folder output.")
    ekstensi = path.suffix.lower()
    if ekstensi not in config.AUDIO_MIME:
        raise Kesalahan("Hanya file WAV atau MP3 yang bisa dibagikan.")
    biner = path.read_bytes()

    for nomor in range(1, batas + 1):
        try:
            return _unggah_sekali(path.name, biner, config.AUDIO_MIME[ekstensi], alamat)
        except GangguanSementara as galat:
            if nomor == batas:
                raise Kesalahan(
                    f"Koneksi ke getshared terus terputus. Sudah dicoba {batas} kali, "
                    "silakan coba lagi beberapa saat lagi."
                )
            catat(f"Unggahan gagal ({galat}), mencoba ulang ({nomor + 1}/{batas})...")
            time.sleep(jeda * nomor)
    raise Kesalahan("Unggahan tidak selesai.")
