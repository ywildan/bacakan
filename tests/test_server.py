import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from bacakan import naming
from bacakan.engine import Hasil
from bacakan.server import Aplikasi, Penangan, ServerBacakan, buat_halaman


class MesinPalsu:
    mp3_tersedia = False

    def sintesis(self, permintaan, folder):
        path = naming.path_keluaran(Path(folder), permintaan.nama, permintaan.format_)
        path.write_bytes(b"RIFF-palsu")
        return Hasil(
            nama=path.name,
            path=path,
            ukuran=path.stat().st_size,
            durasi=1.5,
            suara=permintaan.suara,
            format_=permintaan.format_,
        )


class DasarServerTest(unittest.TestCase):
    bagikan_aktif = False

    def setUp(self):
        senyap = mock.patch.object(Penangan, "log_message", lambda *args, **kwargs: None)
        senyap.start()
        self.addCleanup(senyap.stop)
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        self.app = Aplikasi(
            mesin=MesinPalsu(),
            folder=self.folder,
            halaman=buat_halaman(
                bagikan_aktif=self.bagikan_aktif, mp3_aktif=False
            ),
            bagikan_aktif=self.bagikan_aktif,
        )
        self.server = ServerBacakan(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self._tmp.cleanup()

    def ambil(self, path):
        return urllib.request.urlopen(self.base + path, timeout=10)

    def kirim(self, path, obj):
        data = json.dumps(obj).encode()
        permintaan = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urllib.request.urlopen(permintaan, timeout=10)


class ServerTest(DasarServerTest):
    def test_halaman(self):
        with self.ambil("/") as respons:
            body = respons.read().decode()
            self.assertEqual(respons.status, 200)
            self.assertEqual(respons.headers.get_content_type(), "text/html")
        self.assertIn("Bacakan", body)
        self.assertIn('"F1"', body)
        self.assertIn("const BAGIKAN_AKTIF = false", body)
        self.assertNotIn("__SHARE__", body)
        self.assertNotIn("__VOICES__", body)

    def test_sintesis_dan_audio(self):
        with self.kirim("/api/sintesis", {"teks": "Halo.", "nama": "uji"}) as respons:
            data = json.loads(respons.read())
        self.assertEqual(data["nama"], "uji.wav")
        self.assertEqual(data["format"], "wav")
        self.assertEqual(data["suara"], "F1")
        self.assertAlmostEqual(data["durasi"], 1.5)
        with self.ambil(data["url"]) as respons:
            self.assertEqual(respons.status, 200)
            self.assertEqual(respons.headers.get_content_type(), "audio/wav")
            self.assertEqual(respons.read(), b"RIFF-palsu")

    def test_teks_kosong(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.kirim("/api/sintesis", {"teks": ""})
        self.assertEqual(ctx.exception.code, 400)
        self.assertIn("Teks belum diisi", json.loads(ctx.exception.read())["pesan"])

    def test_bagikan_dimatikan(self):
        (self.folder / "a.wav").write_bytes(b"x")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.kirim("/api/bagikan", {"nama": "a.wav"})
        self.assertEqual(ctx.exception.code, 400)
        self.assertIn("dimatikan", json.loads(ctx.exception.read())["pesan"])

    def test_audio_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.ambil("/audio/..%2Fserver.py")
        self.assertEqual(ctx.exception.code, 404)

    def test_audio_tidak_ada(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.ambil("/audio/tidak-ada.wav")
        self.assertEqual(ctx.exception.code, 404)

    def test_tidak_ditemukan(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.ambil("/halaman-lain")
        self.assertEqual(ctx.exception.code, 404)


class BagikanAktifTest(DasarServerTest):
    bagikan_aktif = True

    def test_bagikan_sukses(self):
        (self.folder / "a.wav").write_bytes(b"x")
        with mock.patch(
            "bacakan.server.bagikan_file", return_value="https://contoh.test/d/abc"
        ) as tiruan:
            with self.kirim("/api/bagikan", {"nama": "a.wav"}) as respons:
                data = json.loads(respons.read())
        self.assertEqual(data["link"], "https://contoh.test/d/abc")
        tiruan.assert_called_once()
        self.assertEqual(tiruan.call_args.args[0].name, "a.wav")

    def test_bagikan_nama_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.kirim("/api/bagikan", {"nama": "../a.wav"})
        self.assertEqual(ctx.exception.code, 400)

    def test_bagikan_tipe_asing(self):
        (self.folder / "a.txt").write_bytes(b"x")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.kirim("/api/bagikan", {"nama": "a.txt"})
        self.assertEqual(ctx.exception.code, 400)

    def test_bagikan_berkas_tidak_ada(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.kirim("/api/bagikan", {"nama": "hilang.wav"})
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
