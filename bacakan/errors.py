"""Jenis kesalahan yang pesannya aman ditampilkan ke pengguna."""


class Kesalahan(Exception):
    """Kesalahan umum dengan pesan berbahasa Indonesia."""


class InputTidakValid(Kesalahan):
    """Masukan pengguna tidak memenuhi aturan."""


class NamaTidakValid(InputTidakValid):
    """Nama file tidak bisa dipakai di sistem operasi ini."""


class GangguanSementara(Kesalahan):
    """Kegagalan sementara yang layak dicoba ulang."""
