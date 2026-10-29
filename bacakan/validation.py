"""Validasi masukan dari API web maupun argumen terminal."""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import config
from .errors import InputTidakValid
from .naming import validasi_nama_opsional


@dataclass(frozen=True)
class Permintaan:
    teks: str
    suara: str
    nama: str
    speed: float
    steps: int
    format_: str


def validasi_suara(nilai: object) -> str:
    mentah = "" if nilai is None else str(nilai).strip()
    suara = (mentah or config.DEFAULT_VOICE).upper()
    if suara not in config.VOICES:
        raise InputTidakValid(
            "Suara tidak dikenal. Pilih salah satu dari: " + " ".join(config.VOICES) + "."
        )
    return suara


def validasi_format(nilai: object, mp3_tersedia: bool) -> str:
    mentah = "" if nilai is None else str(nilai).strip()
    format_ = (mentah or config.DEFAULT_FORMAT).lower().lstrip(".")
    if format_ not in ("wav", "mp3"):
        raise InputTidakValid("Format harus wav atau mp3.")
    if format_ == "mp3" and not mp3_tersedia:
        raise InputTidakValid(
            "Format MP3 butuh ffmpeg, dan ffmpeg tidak ditemukan di komputer ini."
        )
    return format_


def validasi_speed(nilai: object) -> float:
    teks = str(nilai if nilai is not None else "").strip()
    if not teks:
        return config.DEFAULT_SPEED
    try:
        angka = float(teks.replace(",", "."))
    except ValueError:
        raise InputTidakValid("Speed harus berupa angka, misalnya 1.05.")
    if not math.isfinite(angka):
        raise InputTidakValid("Speed harus berupa angka yang wajar.")
    if not config.MIN_SPEED <= angka <= config.MAX_SPEED:
        raise InputTidakValid(
            f"Speed harus antara {config.MIN_SPEED} dan {config.MAX_SPEED}."
        )
    return angka


def validasi_steps(nilai: object) -> int:
    if isinstance(nilai, bool):
        raise InputTidakValid("Total steps harus bilangan bulat, misalnya 8.")
    if nilai is None or (isinstance(nilai, str) and not nilai.strip()):
        return config.DEFAULT_TOTAL_STEPS
    if isinstance(nilai, int):
        angka = nilai
    elif isinstance(nilai, float) and nilai.is_integer():
        angka = int(nilai)
    else:
        try:
            angka = int(str(nilai).strip())
        except ValueError:
            raise InputTidakValid("Total steps harus bilangan bulat, misalnya 8.")
    if not config.MIN_TOTAL_STEPS <= angka <= config.MAX_TOTAL_STEPS:
        raise InputTidakValid(
            "Total steps harus antara "
            f"{config.MIN_TOTAL_STEPS} dan {config.MAX_TOTAL_STEPS}."
        )
    return angka


def validasi_teks(nilai: object) -> str:
    if not isinstance(nilai, str) or not nilai.strip():
        raise InputTidakValid("Teks belum diisi.")
    teks = nilai.strip()
    if len(teks) > config.MAX_TEXT_LENGTH:
        raise InputTidakValid(
            f"Teks terlalu panjang (maksimal {config.MAX_TEXT_LENGTH} karakter)."
        )
    return teks


def susun_permintaan(
    *,
    teks: object,
    suara: object = None,
    nama: object = "",
    speed: object = None,
    steps: object = None,
    format_: object = None,
    mp3_tersedia: bool = False,
) -> Permintaan:
    return Permintaan(
        teks=validasi_teks(teks),
        suara=validasi_suara(suara),
        nama=validasi_nama_opsional(nama),
        speed=validasi_speed(speed),
        steps=validasi_steps(steps),
        format_=validasi_format(format_, mp3_tersedia),
    )


def permintaan_dari_json(data: object, mp3_tersedia: bool) -> Permintaan:
    if not isinstance(data, dict):
        raise InputTidakValid("Data permintaan tidak valid.")
    return susun_permintaan(
        teks=data.get("teks"),
        suara=data.get("suara"),
        nama=data.get("nama"),
        speed=data.get("speed"),
        steps=data.get("steps"),
        format_=data.get("format"),
        mp3_tersedia=mp3_tersedia,
    )
