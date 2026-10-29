"""Pembungkus model Supertonic: muat sekali, sintesis, konversi MP3."""

from __future__ import annotations

import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from . import config
from .errors import Kesalahan
from .naming import path_keluaran
from .validation import Permintaan


@dataclass(frozen=True)
class Hasil:
    nama: str
    path: Path
    ukuran: int
    durasi: float
    suara: str
    format_: str


class Mesin:
    """Satu instance per proses, dipakai ulang untuk semua sintesis."""

    def __init__(self, model_dir: str | Path | None = None):
        from supertonic import TTS

        self._kunci = threading.RLock()
        self._gaya: dict = {}
        self._ffmpeg = shutil.which("ffmpeg")
        opsi: dict = {"auto_download": True}
        if model_dir:
            opsi["model_dir"] = str(model_dir)
        self._tts = TTS(**opsi)

    @property
    def mp3_tersedia(self) -> bool:
        return self._ffmpeg is not None

    def _gaya_untuk(self, suara: str):
        with self._kunci:
            if suara not in self._gaya:
                self._gaya[suara] = self._tts.get_voice_style(voice_name=suara)
            return self._gaya[suara]

    def sintesis(self, permintaan: Permintaan, folder: str | Path) -> Hasil:
        folder = Path(folder)
        path = path_keluaran(folder, permintaan.nama, permintaan.format_)
        gaya = self._gaya_untuk(permintaan.suara)
        sementara = (
            folder / f".bacakan-{uuid4().hex}.wav"
            if permintaan.format_ == "mp3"
            else None
        )
        tujuan = sementara if sementara is not None else path
        try:
            with self._kunci:
                try:
                    wav, durasi = self._tts.synthesize(
                        text=permintaan.teks,
                        lang=config.LANGUAGE,
                        voice_style=gaya,
                        total_steps=permintaan.steps,
                        speed=permintaan.speed,
                    )
                except ValueError as kesalahan:
                    raise Kesalahan(f"Model menolak teks ini: {kesalahan}")
                self._tts.save_audio(wav, str(tujuan))
            if sementara is not None:
                self._ubah_mp3(sementara, path)
        finally:
            if sementara is not None:
                sementara.unlink(missing_ok=True)

        return Hasil(
            nama=path.name,
            path=path,
            ukuran=path.stat().st_size,
            durasi=float(durasi[0]),
            suara=permintaan.suara,
            format_=permintaan.format_,
        )

    def _ubah_mp3(self, sumber: Path, tujuan: Path) -> None:
        perintah = [
            self._ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(sumber),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(tujuan),
        ]
        try:
            hasil = subprocess.run(perintah, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            tujuan.unlink(missing_ok=True)
            raise Kesalahan("Konversi MP3 terlalu lama dan dihentikan.")
        if hasil.returncode != 0:
            tujuan.unlink(missing_ok=True)
            baris = (hasil.stderr or "").strip().splitlines()
            alasan = baris[-1] if baris else "tanpa pesan dari ffmpeg"
            raise Kesalahan(f"Gagal mengubah ke MP3: {alasan}")
