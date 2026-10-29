import json
import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bacakan import share
from bacakan.errors import Kesalahan


class LayananPalsu(BaseHTTPRequestHandler):
    catatan = []

    def log_message(self, *args):
        pass

    def _balas(self, obj, status=200):
        isi = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(isi)))
        self.end_headers()
        self.wfile.write(isi)

    def do_GET(self):
        if self.path == "/upload/genid":
            self._balas({"upload_id": "uji123"})
        else:
            self._balas({}, 404)

    def do_POST(self):
        panjang = int(self.headers.get("Content-Length") or 0)
        isi = self.rfile.read(panjang)
        LayananPalsu.catatan.append(
            (self.path, self.headers.get("Content-Type", ""), isi)
        )
        if self.path == "/upload/register":
            self._balas({"response": "ok"})
        elif self.path == "/upload":
            self._balas({"files": [{"name": "berkas.wav"}]})
        elif self.path == "/upload/complete":
            self._balas(
                {"status": "success", "link": "https://contoh.test/d/uji123"}
            )
        else:
            self._balas({}, 404)


class BagikanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LayananPalsu)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.alamat = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls._tmp = tempfile.TemporaryDirectory()
        cls.berkas = Path(cls._tmp.name) / "berkas.wav"
        cls.berkas.write_bytes(b"RIFF-data-uji")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls._tmp.cleanup()

    def setUp(self):
        LayananPalsu.catatan = []

    def test_alur_sukses(self):
        link = share.bagikan_file(
            self.berkas, alamat=self.alamat, batas=1, jeda=0, catat=lambda _: None
        )
        self.assertEqual(link, "https://contoh.test/d/uji123")
        jalur = [item[0] for item in LayananPalsu.catatan]
        self.assertEqual(jalur, ["/upload/register", "/upload", "/upload/complete"])

        _, tipe, isi = LayananPalsu.catatan[1]
        self.assertIn("multipart/form-data", tipe)
        self.assertIn(b'filename="berkas.wav"', isi)
        self.assertIn(b"RIFF-data-uji", isi)
        self.assertIn(b"audio/wav", isi)

        _, _, isi_register = LayananPalsu.catatan[0]
        self.assertIn(b'name="upload_id"', isi_register)
        self.assertIn(b"uji123", isi_register)

    def test_formulir(self):
        isi, tipe = share.buat_formulir(
            [("upload_id", "abc")],
            ("files[]", "x.wav", b"\x00\x01", "audio/wav"),
        )
        self.assertTrue(tipe.startswith("multipart/form-data; boundary="))
        batas = tipe.split("boundary=", 1)[1]
        self.assertTrue(isi.startswith(f"--{batas}".encode()))
        self.assertTrue(isi.endswith(f"--{batas}--\r\n".encode()))
        self.assertIn(b'Content-Disposition: form-data; name="upload_id"', isi)
        self.assertIn(b"abc", isi)
        self.assertIn(b"\x00\x01", isi)

    def test_berkas_hilang(self):
        with self.assertRaises(Kesalahan):
            share.bagikan_file(Path(self._tmp.name) / "hilang.wav")

    def test_tipe_tidak_didukung(self):
        txt = Path(self._tmp.name) / "catatan.txt"
        txt.write_text("halo", encoding="utf-8")
        with self.assertRaises(Kesalahan):
            share.bagikan_file(txt)

    def test_koneksi_putus_diulang(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(5)
        port = server.getsockname()[1]
        jumlah = []

        def layani():
            while True:
                try:
                    koneksi, _ = server.accept()
                except OSError:
                    return
                jumlah.append(1)
                koneksi.close()

        threading.Thread(target=layani, daemon=True).start()
        try:
            with self.assertRaises(Kesalahan) as ctx:
                share.bagikan_file(
                    self.berkas,
                    alamat=f"http://127.0.0.1:{port}",
                    batas=3,
                    jeda=0,
                    catat=lambda _: None,
                )
        finally:
            server.close()
        self.assertIn("Sudah dicoba 3 kali", str(ctx.exception))
        self.assertEqual(len(jumlah), 3)


if __name__ == "__main__":
    unittest.main()
