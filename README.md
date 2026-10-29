# Bacakan

Text to speech Bahasa Indonesia yang berjalan lokal, dengan antarmuka web dan versi terminal. Dibangun di atas model [Supertonic 3](https://github.com/supertone-inc/supertonic) lewat ONNX Runtime, jadi suara dibuat di komputer sendiri, bukan di server orang lain.

Hasil bisa disimpan sebagai WAV (lossless) atau MP3 (kecil), dan bisa dibagikan lewat tautan getshared kalau kamu mau.

Bacakan runs fully on your own machine. It provides a small web UI and an interactive terminal mode, exports WAV or MP3, and works on Linux, macOS and Windows. Nothing leaves your computer unless you press the share button.

## Fitur

- Sepuluh suara bawaan: M1 sampai M5 dan F1 sampai F5.
- Model dimuat sekali per sesi, lalu dipakai ulang untuk semua sintesis.
- Antarmuka web lokal dengan pemutar audio, unduh, dan tombol bagikan.
- Mode terminal interaktif, plus mode sekali jalan untuk skrip.
- Ekspor WAV atau MP3. MP3 memakai ffmpeg kalau tersedia.
- Teks bisa diketik langsung, ditempel, atau dibaca dari file `.txt`.
- Nama file otomatis, aman untuk Windows, dan tidak menimpa file lama.
- Bisa dimatikan fitur bagikannya dengan `--no-share`.

## Kebutuhan

- Python 3.10 atau lebih baru.
- Ruang disk sekitar 400 MB untuk model, diunduh otomatis pada pemakaian pertama.
- ffmpeg, hanya kalau ingin hasil MP3. Tanpa ffmpeg, pilihan MP3 dimatikan otomatis dan hanya WAV yang tersedia.

Model disimpan di `~/.cache/supertonic3` di Linux/macOS, dan `C:\Users\<nama>\.cache\supertonic3` di Windows.

## Instalasi

Linux atau macOS:

```bash
git clone https://github.com/<username>/bacakan.git
cd bacakan
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows (PowerShell):

```powershell
git clone https://github.com/<username>/bacakan.git
cd bacakan
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Kalau PowerShell menolak skrip aktivasi, jalankan sekali di jendela itu:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

Di Command Prompt, aktivasi memakai `.venv\Scripts\activate.bat`.

Setelah terpasang, dua perintah tersedia (di Windows otomatis menjadi `bacakan.exe` dan `bacakan-cli.exe`):

- `bacakan` untuk antarmuka web.
- `bacakan-cli` untuk versi terminal.

Paket juga bisa dijalankan tanpa perintah di atas dengan `python -m bacakan` dari folder repo.

### ffmpeg untuk MP3

- Windows: `winget install Gyan.FFmpeg`, lalu buka terminal baru.
- macOS: `brew install ffmpeg`.
- Debian/Ubuntu: `sudo apt install ffmpeg`.

Cek dengan `ffmpeg -version`. Kalau tidak ada, aplikasi tetap jalan dengan WAV saja.

## Pemakaian web

```bash
bacakan
```

Buka `http://127.0.0.1:8000`. Opsi yang sering dipakai:

| Opsi | Arti |
| --- | --- |
| `--port 9000` | Ganti port |
| `--host 0.0.0.0` | Buka ke jaringan lokal, tanpa login, hanya untuk jaringan tepercaya |
| `--output-dir hasil` | Ganti folder hasil, default `./outputs` |
| `--open` | Buka browser otomatis |
| `--no-share` | Sembunyikan fitur bagikan |
| `--model-dir /path/ke/model` | Pakai folder model tertentu |

Alurnya: pilih suara dan format, isi teks, tekan **Buat suara**. Hasil langsung tersimpan di folder output, bisa diputar dan diunduh dari halaman. Tombol **Bagikan ke getshared** mengunggah file tersebut dan menampilkan tautan publik.

## Pemakaian terminal

Interaktif:

```bash
bacakan-cli
```

Setiap pertanyaan bisa dilewati dengan Enter untuk memakai nilai bawaan. Teks multi-baris diakhiri dengan baris berisi `END`, atau ketik path file `.txt`. Ketik `keluar` atau tekan Ctrl+C untuk berhenti.

Sekali jalan, cocok untuk skrip:

```bash
bacakan-cli --text "Selamat pagi semuanya." --voice F1 --out sapaan
bacakan-cli --text-file naskah.txt --voice M3 --format mp3
```

Contoh lain:

```bash
bacakan-cli --list-voices
bacakan-cli --help
```

Kode keluar: `0` berhasil, `2` masukan salah atau gagal.

## Folder hasil

Default `./outputs` relatif terhadap folder tempat perintah dijalankan. Nama otomatis memakai `output-YYYYMMDD-HHMMSS`. Kalau nama yang diminta sudah ada, file lama tidak ditimpa, program meminta nama lain.

Nama file divalidasi untuk semua sistem operasi: karakter `< > : " / \ | ? *` ditolak, begitu juga nama perangkat Windows seperti `CON` atau `NUL`, serta nama yang diakhiri titik.

## API lokal

Kalau ingin memakai dari skrip lain:

```bash
curl -X POST http://127.0.0.1:8000/api/sintesis \
  -H "Content-Type: application/json" \
  -d '{"teks":"Halo dunia.","suara":"F1","format":"mp3","nama":"halo"}'
```

Jawabannya berisi `nama`, `url`, `ukuran`, `durasi`, `suara`, dan `format`. File bisa diambil dari `url` yang diberikan. Untuk membagikan file yang sudah ada:

```bash
curl -X POST http://127.0.0.1:8000/api/bagikan \
  -H "Content-Type: application/json" \
  -d '{"nama":"halo.mp3"}'
```

## Bagikan ke getshared

Fitur ini memakai [getshared](https://getshared.com) sebagai tempat file. Unggahan hanya terjadi saat tombol ditekan atau endpoint `/api/bagikan` dipanggil. Tautan bersifat publik dan berlaku 30 hari, jadi jangan bagikan rekaman yang sensitif. Matikan seluruhnya dengan `--no-share`.

## Struktur proyek

```
bacakan/
  pyproject.toml
  bacakan/
    engine.py       pembungkus model, sintesis, konversi MP3
    naming.py       aturan nama file lintas sistem operasi
    validation.py   validasi masukan web dan CLI
    share.py        unggah getshared dengan percobaan ulang
    server.py       server HTTP dan API
    cli.py          mode terminal
    templates/      halaman web
  tests/            unittest tanpa model
```

## Tes

```bash
python -m unittest discover -s tests -v
```

Tes tidak memuat model dan tidak memakai jaringan, jadi cepat dan bisa jalan di CI. Workflow GitHub Actions di repo ini menjalankannya di Ubuntu dan Windows untuk Python 3.10 dan 3.12.

## Keamanan

Server web mengikat `127.0.0.1` secara bawaan dan tidak punya autentikasi. Jangan buka ke internet. Kalau memakai `--host 0.0.0.0`, siapa pun di jaringan yang sama bisa membuat suara dan mengunggah file.

## Lisensi

MIT. Lihat [LICENSE](LICENSE).
