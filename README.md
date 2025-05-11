# 📰 Program Scraping Berita

Aplikasi ini digunakan untuk melakukan scraping berita dari Google menggunakan SerpAPI. Program mendukung dua mode: **tanpa antarmuka (CLI)** dan **dengan antarmuka grafis (GUI berbasis Tkinter)**.

---

## 📌 Persyaratan

| Komponen         | Keterangan                                      |
|------------------|--------------------------------------------------|
| 🧰 Tools          | Visual Studio Code (VSCode)                     |
| 🐍 Bahasa         | Python 3.10 ke atas                             |
| 📦 Dependencies   | Lihat `requirements.txt`                        |
| 🌐 Koneksi Internet | Dibutuhkan untuk menggunakan SerpAPI           |
| 🔑 API Key        | Diperlukan dari [SerpAPI](https://serpapi.com/) |

---

## 🛠 Instalasi

1. Buka VSCode
2. Buka terminal dengan menekan: `Ctrl + Shift + \` (tombol backtick)
3. Install semua dependencies dengan perintah berikut:

   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Menjalankan Program

### 1. Tanpa GUI (Command Line):
```bash
python main.py
```

### 2. Dengan GUI (Tkinter):
```bash
python scraper_gui.py
```

---

## 📝 Catatan Tambahan

- Jika menggunakan Linux dan muncul error terkait `tkinter`, install manual dengan:
  ```bash
  sudo apt install python3-tk
  ```

---

## 📄 Lisensi
Proyek ini bebas digunakan untuk keperluan pembelajaran dan pengembangan pribadi.
