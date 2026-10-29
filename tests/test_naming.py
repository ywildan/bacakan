import re
import tempfile
import unittest
from pathlib import Path

from bacakan import naming
from bacakan.errors import NamaTidakValid


class ValidasiNamaTest(unittest.TestCase):
    def test_ekstensi_dilepas(self):
        self.assertEqual(naming.validasi_nama("halo.wav"), "halo")
        self.assertEqual(naming.validasi_nama("halo.MP3"), "halo")
        self.assertEqual(naming.validasi_nama("  halo  "), "halo")

    def test_unicode_dan_spasi_diizinkan(self):
        self.assertEqual(naming.validasi_nama("selamat pagi"), "selamat pagi")
        self.assertEqual(naming.validasi_nama("pidato-presiden_02"), "pidato-presiden_02")

    def test_karakter_terlarang(self):
        for nama in ['a/b', "a\\b", "a:b", "a*b", "a?b", 'a"b', "a<b", "a>b", "a|b"]:
            with self.subTest(nama=nama):
                with self.assertRaises(NamaTidakValid):
                    naming.validasi_nama(nama)

    def test_nama_perangkat_windows(self):
        for nama in ["CON", "con", "NUL.wav", "COM1", "lpt9", "aux.mp3"]:
            with self.subTest(nama=nama):
                with self.assertRaises(NamaTidakValid):
                    naming.validasi_nama(nama)

    def test_titik_di_akhir(self):
        for nama in ["halo.", "rapat.."]:
            with self.subTest(nama=nama):
                with self.assertRaises(NamaTidakValid):
                    naming.validasi_nama(nama)

    def test_spasi_di_akhir_dirapikan(self):
        self.assertEqual(naming.validasi_nama("halo "), "halo")

    def test_titik_di_awal(self):
        with self.assertRaises(NamaTidakValid):
            naming.validasi_nama(".rahasia")

    def test_nama_kosong(self):
        with self.assertRaises(NamaTidakValid):
            naming.validasi_nama("")
        with self.assertRaises(NamaTidakValid):
            naming.validasi_nama("   ")

    def test_dotdot_ditolak(self):
        with self.assertRaises(NamaTidakValid):
            naming.validasi_nama("..")

    def test_terlalu_panjang(self):
        with self.assertRaises(NamaTidakValid):
            naming.validasi_nama("a" * (naming.PANJANG_MAKS + 1))

    def test_opsional(self):
        self.assertEqual(naming.validasi_nama_opsional(""), "")
        self.assertEqual(naming.validasi_nama_opsional(None), "")
        self.assertEqual(naming.validasi_nama_opsional("halo.wav"), "halo")


class PathKeluaranTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_nama_otomatis(self):
        path = naming.path_keluaran(self.folder, "", "wav")
        self.assertEqual(path.parent, self.folder)
        self.assertRegex(path.name, r"^output-\d{8}-\d{6}\.wav$")

    def test_nama_otomatis_tidak_menimpa(self):
        pertama = naming.path_keluaran(self.folder, "", "mp3")
        pertama.write_bytes(b"x")
        kedua = naming.path_keluaran(self.folder, "", "mp3")
        self.assertNotEqual(pertama, kedua)
        self.assertRegex(kedua.name, r"^output-\d{8}-\d{6}-2\.mp3$")

    def test_nama_eksplisit_bentrok(self):
        (self.folder / "rapat.wav").write_bytes(b"x")
        with self.assertRaises(NamaTidakValid):
            naming.path_keluaran(self.folder, "rapat", "wav")

    def test_folder_dibuat_otomatis(self):
        path = naming.path_keluaran(self.folder / "baru", "", "wav")
        self.assertTrue(path.parent.is_dir())


if __name__ == "__main__":
    unittest.main()
