import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from bs4 import BeautifulSoup
import requests, os, time, random, csv, pandas as pd, concurrent.futures
from serpapi import GoogleSearch
from urllib.parse import urlparse
from dotenv import load_dotenv
import subprocess

# ========== CONFIG ==========
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:85.0)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X)",
    "Mozilla/5.0 (iPad; CPU OS 13_6_1 like Mac OS X)",
]

HEADERS = lambda: {"User-Agent": random.choice(USER_AGENTS)}

# ========== SCRAPING FUNCTIONS ==========
def generate_query(start, end, keyword, site, specific):
    if specific:
        keyword = f'"{keyword}"'
    return f'{keyword} site:{site} after:{start} before:{end}'

def search_google(query, log):
    urls = []
    start = 0
    step = 10
    while True:
        search_params = {
            "q": query,
            "start": start,
            "num": 10,
            "api_key": SERPAPI_KEY,
            "engine": "google",
            "hl": "id",
            "gl": "id"
        }
        search = GoogleSearch(search_params)
        result = search.get_dict()

        if "error" in result:
            log.insert(tk.END, f"❌ Error: {result['error']}\n")
            break

        organic = result.get("organic_results", [])
        if not organic:
            break

        for r in organic:
            link = r.get("link")
            if link and link not in urls:
                urls.append(link)
                log.insert(tk.END, f"{len(urls)}. {link}\n")
                log.see(tk.END)
        start += step
        time.sleep(1)
    return urls

def scrape_multipage(url, soup):
    content = ""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.split('?')[0]}"
    page = 1
    while True:
        if page > 1:
            try:
                resp = requests.get(f"{base_url}?page={page}", headers=HEADERS(), timeout=10)
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, 'html.parser')
            except:
                break
        tag = (
            soup.find("div", class_="txt-article") or
            soup.find("div", class_="td-post-content") or
            soup.find("div", class_="article-content") or
            soup.find("div", class_="content") or
            soup.find("div", class_="isi-berita") or
            soup.find("div", class_="article-body") or
            soup.find("div", class_="entry-content") or
            soup.find("div", class_="read__content") or
            soup.find("div", class_="post-content") or
            soup.find("div", class_="detail__body-text") or
            soup.find("div", class_="article__content") or
            soup.find("div", class_="article-content-body__item-content") or
            soup.find("div", class_="detail-desc") or
            soup.find("div", class_="itp_bodycontent")
        )
        if tag:
            for p in tag.find_all("p"):
                txt = p.get_text(strip=True)
                if len(txt) > 30:
                    content += txt + "\n"
        else:
            break
        paging = soup.find("div", class_="paging-news")
        if not paging or not paging.find("a", string=str(page + 1)):
            break
        page += 1
    return content.strip()

def improved_scrape(url, lokasi_filter):
    try:
        url = url.replace("/amp/", "/")
        resp = requests.get(url, headers=HEADERS(), timeout=10)
        if resp.status_code != 200:
            return "Tidak ada judul", url, "Tidak ada konten", "❌ Tidak diketahui"
        soup = BeautifulSoup(resp.text, 'html.parser')
        title = soup.title.text.strip() if soup.title else "Tidak ada judul"
        content = scrape_multipage(url, soup)
        lokasi_status = "✅ Ya" if lokasi_filter and lokasi_filter.lower() in content.lower() else "❌ Tidak"
        return title, url, content if content else "Tidak ada konten", lokasi_status
    except Exception as e:
        return "Gagal", url, f"Error: {e}", "❌ Error"

def scrape_all(urls, lokasi_filter, log, progressbar):
    results = []
    total = len(urls)
    completed = 0
    progressbar["maximum"] = total

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(improved_scrape, url, lokasi_filter): url for url in urls}
        for f in concurrent.futures.as_completed(futures):
            completed += 1
            progressbar["value"] = completed
            try:
                res = f.result()
                log.insert(tk.END, f"✔ [{completed}/{total}] {res[0]}\n")
                log.see(tk.END)
                results.append(res)
            except Exception as e:
                log.insert(tk.END, f"❌ [{completed}/{total}] Error scraping: {futures[f]}\n")
                log.see(tk.END)
                results.append(["Error", futures[f], f"Error: {e}", "❌"])
    return results

def open_folder(path):
    if os.name == "nt":
        subprocess.Popen(f'explorer "{path}"')

def save_files(data, keyword, site):
    folder = site.replace('.', '_')
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df = pd.DataFrame(data, columns=["Title", "URL", "Konten", "Lokasi Cocok"])
    excel_path = os.path.join(folder, f"{keyword}_{timestamp}.xlsx")
    df.to_excel(excel_path, index=False)
    with open(os.path.join(folder, f"{keyword}_{timestamp}.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "URL", "Konten", "Lokasi Cocok"])
        writer.writerows(data)
    return folder

# ========== GUI ==========
def start_scraping():
    log.delete(1.0, tk.END)
    progress["value"] = 0
    try:
        start = datetime.strptime(start_entry.get(), "%Y-%m-%d").strftime("%Y-%m-%d")
        end = datetime.strptime(end_entry.get(), "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        messagebox.showerror("Error", "Format tanggal salah (YYYY-MM-DD)")
        return

    keyword = keyword_entry.get()
    site = site_entry.get()
    lokasi = lokasi_entry.get()
    spesifik = specific_var.get()

    if not keyword or not site:
        messagebox.showwarning("Input Kosong", "Kata kunci dan domain situs wajib diisi.")
        return

    query = generate_query(start, end, keyword, site, spesifik)
    log.insert(tk.END, f"🔍 Query: {query}\n\n")
    log.see(tk.END)
    urls = search_google(query, log)
    if not urls:
        log.insert(tk.END, "❌ Tidak ada hasil ditemukan.\n")
        return
    log.insert(tk.END, f"\n🔄 Mulai scraping {len(urls)} URL...\n")
    log.see(tk.END)
    results = scrape_all(urls, lokasi, log, progress)
    folder_path = save_files(results, keyword, site)
    messagebox.showinfo("Selesai", "Scraping selesai dan hasil disimpan.")
    open_folder(folder_path)
    log.insert(tk.END, f"\n📁 Hasil disimpan ke folder: {folder_path}\n")
    log.see(tk.END)

# GUI Layout
root = tk.Tk()
root.title("Scraper Berita - Tkinter")
root.geometry("700x550")

frame = ttk.Frame(root, padding="10")
frame.pack(fill="both", expand=True)

ttk.Label(frame, text="Tanggal Awal (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
start_entry = ttk.Entry(frame)
start_entry.grid(row=0, column=1, sticky="ew")

ttk.Label(frame, text="Tanggal Akhir (YYYY-MM-DD)").grid(row=1, column=0, sticky="w")
end_entry = ttk.Entry(frame)
end_entry.grid(row=1, column=1, sticky="ew")

ttk.Label(frame, text="Kata Kunci").grid(row=2, column=0, sticky="w")
keyword_entry = ttk.Entry(frame)
keyword_entry.grid(row=2, column=1, sticky="ew")

ttk.Label(frame, text="Domain Situs (misal: detik.com)").grid(row=3, column=0, sticky="w")
site_entry = ttk.Entry(frame)
site_entry.grid(row=3, column=1, sticky="ew")

ttk.Label(frame, text="Filter Lokasi (opsional)").grid(row=4, column=0, sticky="w")
lokasi_entry = ttk.Entry(frame)
lokasi_entry.grid(row=4, column=1, sticky="ew")

specific_var = tk.BooleanVar()
ttk.Checkbutton(frame, text="Pencarian Spesifik (Exact match)", variable=specific_var).grid(row=5, columnspan=2, sticky="w")

ttk.Button(frame, text="Mulai Scraping", command=lambda: threading.Thread(target=start_scraping).start()).grid(row=6, columnspan=2, pady=5)

progress = ttk.Progressbar(frame, mode='determinate')
progress.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 10))

log = tk.Text(frame, height=15, wrap="word")
log.grid(row=8, column=0, columnspan=2, sticky="nsew")

frame.columnconfigure(1, weight=1)
frame.rowconfigure(8, weight=1)

root.mainloop()
