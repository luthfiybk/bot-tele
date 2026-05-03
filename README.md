# 🔍 OSINT Phone Lookup Telegram Bot

Bot Telegram untuk mencari informasi dari nomor telepon menggunakan API Multi-Source (GetContact, Truecaller, CallApp, Eyecon, dll).

## 📋 Fitur

- ✅ **Multi-Source Lookup**: Mengambil data dari GetContact, Truecaller, CallApp, Eyecon, dll.
- ✅ **Separator Per Sumber**: Tampilan hasil yang rapi dengan pemisah antar sumber.
- ✅ **Dynamic Key**: Ganti API Key/Voucher sewaktu-waktu via perintah admin.
- ✅ **Validasi Otomatis**: Mendukung berbagai format nomor (08xx, +62xx, 62xx).
- ✅ **Caching**: Menyimpan hasil pencarian secara lokal untuk menghemat token.
- ✅ **Status Check**: Pantau statistik cache dan status bot via `/status`.

## 🚀 Setup & Instalasi

### Prasyarat

- Python 3.10 atau lebih baru
- Akun Telegram
- Token Bot Telegram (dari @BotFather)
- API Key dari data-publik.com

### Langkah 1: Buat Bot Telegram

1. Buka Telegram, cari **@BotFather**
2. Kirim `/newbot`
3. Simpan **API Token** yang diberikan.

### Langkah 2: Install Dependencies

```bash
# Buat virtual environment
python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Langkah 3: Konfigurasi Environment

Edit file `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
DATAPUBLIK_BASE_URL=https://data-publik.com/api
DATAPUBLIK_DEFAULT_KEY=your_api_key
```

### Langkah 4: Jalankan Bot

```bash
python -m bot.main
```

## 📱 Perintah Admin

- `/set_voucher <kode>` : Memperbarui API Key/Voucher secara dinamis tanpa restart bot.
- `/status` : Melihat statistik bot dan cache.

## 📂 Struktur Project

```
bot-tele/
├── .env                  # Konfigurasi
├── bot/
│   ├── main.py           # Entry point
│   ├── handlers/         # Logic command & message
│   └── services/
│       ├── datapublik.py # API Client Multi-Source
│       ├── cache.py      # SQLite Caching
│       └── phone_utils.py # Phone normalization
└── cache.db              # Database cache lokal
```

## ⚖️ Disclaimer

Bot ini dibuat untuk keperluan edukasi dan riset keamanan. Pastikan Anda memiliki izin untuk menggunakan API pihak ketiga yang terhubung.
