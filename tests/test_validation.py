import unittest

from bacakan import config
from bacakan.errors import InputTidakValid
from bacakan.validation import (
    permintaan_dari_json,
    validasi_format,
    validasi_speed,
    validasi_steps,
    validasi_suara,
    validasi_teks,
)


class SuaraTest(unittest.TestCase):
    def test_bawaan(self):
        self.assertEqual(validasi_suara(None), config.DEFAULT_VOICE)
        self.assertEqual(validasi_suara(""), config.DEFAULT_VOICE)

    def test_huruf_kecil(self):
        self.assertEqual(validasi_suara("f3"), "F3")

    def test_tidak_dikenal(self):
        with self.assertRaises(InputTidakValid):
            validasi_suara("X9")


class SpeedTest(unittest.TestCase):
    def test_bawaan(self):
        self.assertEqual(validasi_speed(""), config.DEFAULT_SPEED)

    def test_koma(self):
        self.assertAlmostEqual(validasi_speed("1,2"), 1.2)

    def test_di_luar_batas(self):
        for nilai in ["0", "-1", "3.01", "abc", "nan", "inf"]:
            with self.subTest(nilai=nilai):
                with self.assertRaises(InputTidakValid):
                    validasi_speed(nilai)


class StepsTest(unittest.TestCase):
    def test_bawaan(self):
        self.assertEqual(validasi_steps(None), config.DEFAULT_TOTAL_STEPS)

    def test_bulat(self):
        self.assertEqual(validasi_steps("12"), 12)
        self.assertEqual(validasi_steps(8.0), 8)

    def test_salah(self):
        for nilai in ["0", "101", "8.5", "abc", True]:
            with self.subTest(nilai=nilai):
                with self.assertRaises(InputTidakValid):
                    validasi_steps(nilai)


class FormatTest(unittest.TestCase):
    def test_wav_mp3(self):
        self.assertEqual(validasi_format("", True), "wav")
        self.assertEqual(validasi_format("MP3", True), "mp3")
        self.assertEqual(validasi_format(".wav", True), "wav")

    def test_mp3_tanpa_ffmpeg(self):
        with self.assertRaises(InputTidakValid):
            validasi_format("mp3", False)

    def test_format_asing(self):
        with self.assertRaises(InputTidakValid):
            validasi_format("ogg", True)


class TeksTest(unittest.TestCase):
    def test_kosong(self):
        for nilai in ["", "   ", None, 123]:
            with self.subTest(nilai=nilai):
                with self.assertRaises(InputTidakValid):
                    validasi_teks(nilai)

    def test_terlalu_panjang(self):
        with self.assertRaises(InputTidakValid):
            validasi_teks("a" * (config.MAX_TEXT_LENGTH + 1))


class PermintaanJsonTest(unittest.TestCase):
    def test_lengkap(self):
        permintaan = permintaan_dari_json(
            {
                "teks": "  Halo dunia.  ",
                "suara": "m2",
                "nama": "sapaan.wav",
                "speed": "1,1",
                "steps": 10,
                "format": "wav",
            },
            mp3_tersedia=True,
        )
        self.assertEqual(permintaan.teks, "Halo dunia.")
        self.assertEqual(permintaan.suara, "M2")
        self.assertEqual(permintaan.nama, "sapaan")
        self.assertAlmostEqual(permintaan.speed, 1.1)
        self.assertEqual(permintaan.steps, 10)
        self.assertEqual(permintaan.format_, "wav")

    def test_bawaan(self):
        permintaan = permintaan_dari_json({"teks": "Halo."}, mp3_tersedia=True)
        self.assertEqual(permintaan.suara, config.DEFAULT_VOICE)
        self.assertEqual(permintaan.nama, "")
        self.assertEqual(permintaan.format_, "wav")

    def test_bukan_objek(self):
        with self.assertRaises(InputTidakValid):
            permintaan_dari_json(["teks"], mp3_tersedia=True)

    def test_nama_traversal(self):
        for nama in ["../rahasia", "a/b", ".."]:
            with self.subTest(nama=nama):
                with self.assertRaises(InputTidakValid):
                    permintaan_dari_json({"teks": "Halo.", "nama": nama}, True)


if __name__ == "__main__":
    unittest.main()
