import requests
import csv
import time
import pandas as pd
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from urllib.parse import urlparse
from dotenv import load_dotenv
import os
import datetime
import concurrent.futures
import random

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

# ========== INPUT ==========
def is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def get_days_in_month(year, month):
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return 29 if month == 2 and is_leap_year(year) else days[month - 1]

def get_date_input(prompt):
    while True:
        try:
            date_input = input(f"Tanggal {prompt} (YYYY-MM-DD): ")
            y, m, d = map(int, date_input.split('-'))
            if 1 <= m <= 12 and 1 <= d <= get_days_in_month(y, m):
                return y, m, d
        except:
            pass
        print("❌ Format salah. Coba lagi.")

# ========== GOOGLE SEARCH ==========
def generate_google_search_query(start, end, keyword, site, specific):
    start_date = f"{start[0]}-{start[1]:02d}-{start[2]:02d}"
    end_date = f"{end[0]}-{end[1]:02d}-{end[2]:02d}"
    if specific.lower() == "ya":
        keyword = f'"{keyword}"'
    query = f"{keyword} site:{site} after:{start_date} before:{end_date}"
    print("\n🔍 Query:")
    print(query)
    return query

def search_google(query):
    print("\n🔎 Mencari dengan SerpAPI...")
    urls = []
    start = 0
    step = 10

    try:
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
                print("❌ Error:", result["error"])
                break

            organic = result.get("organic_results", [])
            if not organic:
                print("✅ Halaman terakhir tercapai.")
                break

            for r in organic:
                link = r.get("link")
                if link and link not in urls:
                    urls.append(link)
                    print(f"{len(urls)}. {link}")

            start += step
            time.sleep(1)

    except Exception as e:
        print(f"❌ Error ambil hasil: {e}")

    return urls

# ========== SCRAPER ==========
def scrape_multipage(url, soup):
    content = ""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.split('?')[0]}"
    page = 1

    while True:
        if page > 1:
            paged_url = f"{base_url}?page={page}"
            try:
                resp = requests.get(paged_url, headers=HEADERS(), timeout=10)
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

def improved_scrape(url, lokasi_filter=None):
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

def scrape_all_fast(urls, lokasi_filter=None, max_workers=5):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(improved_scrape, url, lokasi_filter): url for url in urls
        }
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                results.append(future.result())
            except Exception as e:
                results.append(["Error", future_to_url[future], f"Error future: {e}", "❌ Error"])
    return results

# ========== SIMPAN FILE ==========
def save_to_excel(data, keyword, site):
    folder = site.replace('.', '_')
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(folder, f"{keyword}_{timestamp}.xlsx")
    df = pd.DataFrame(data, columns=["Title", "URL", "Konten", "Lokasi Cocok"])
    df.to_excel(filepath, index=False)
    print(f"📁 Disimpan ke Excel: {filepath}")

def save_to_csv(data, keyword, site):
    folder = site.replace('.', '_')
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(folder, f"{keyword}_{timestamp}.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "URL", "Konten", "Lokasi Cocok"])
        writer.writerows(data)
    print(f"📁 Disimpan ke CSV: {filepath}")

# ========== MAIN ==========
if __name__ == "__main__":
    print("🚀 Mulai Program Scraper Berita\n")

    start_date = get_date_input("awal")
    end_date = get_date_input("akhir")
    keyword = input("Kata kunci: ")
    specific = input("Apakah pencarian spesifik? (Ya/Tidak): ")
    site = input("Domain situs (contoh: kalimantanpost.com): ")
    lokasi = input("Masukkan lokasi (kosongkan jika tidak perlu): ")

    query = generate_google_search_query(start_date, end_date, keyword, site, specific)
    urls = search_google(query)

    if not urls:
        print("❌ Tidak ada hasil ditemukan.")
    else:
        print("\n🔄 Mulai scraping...")
        results = scrape_all_fast(urls, lokasi_filter=lokasi)
        save_to_excel(results, keyword, site)
        save_to_csv(results, keyword, site)
