import requests
import pandas as pd
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import shutil

# ================= CONFIG ================= #

BASE_DIR = r"C:\Users\AM'sTUFFa15\OneDrive\Desktop\Job_Scrap"
INPUT_FILE = os.path.join(BASE_DIR, "input_File.xlsx")
TEMP_FILE = os.path.join(BASE_DIR, "Output_File.xlsx")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

CAREER_KEYWORDS = ["career", "careers", "jobs", "join", "hiring"]
ATS_DOMAINS = ["lever.co", "greenhouse.io", "workable.com", "zohorecruit", "ashbyhq"]

# ================= HELPERS ================= #

def clean_url(url):
    if not isinstance(url, str) or not url.strip():
        return None
    return url if url.startswith("http") else "https://" + url.strip()

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code < 400:
            return BeautifulSoup(r.text, "lxml")
    except:
        pass
    return None

# ================= CAREER ================= #

def find_careers_page(home_url):
    soup = fetch(home_url)
    if not soup:
        return None

    for a in soup.find_all("a", href=True):
        t = a.get_text(strip=True).lower()
        h = a["href"].lower()
        if any(k in t or k in h for k in CAREER_KEYWORDS):
            return urljoin(home_url, a["href"])

    for p in ["/careers", "/jobs", "/join-us"]:
        test = home_url.rstrip("/") + p
        if fetch(test):
            return test

    return None

def find_job_listings_page(careers_url):
    soup = fetch(careers_url)
    if not soup:
        return careers_url

    for a in soup.find_all("a", href=True):
        if any(k in a.get_text(strip=True).lower() for k in ["open positions", "view jobs"]):
            return urljoin(careers_url, a["href"])

    for a in soup.find_all("a", href=True):
        if any(ats in a["href"].lower() for ats in ATS_DOMAINS):
            return urljoin(careers_url, a["href"])

    return careers_url

# ================= JOB SCRAPER ================= #

def scrape_jobs(listing_url, max_jobs=3):
    soup = fetch(listing_url)
    if not soup:
        return []

    jobs, seen = [], set()

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"].lower()

        if title and len(title) > 8 and any(k in href for k in ["job", "opening", "position"]):
            url = urljoin(listing_url, a["href"])
            if url in seen:
                continue
            seen.add(url)

            jsoup = fetch(url)
            if not jsoup:
                continue

            text = jsoup.get_text(" ", strip=True)
            loc = re.search(r"(Remote|Hybrid|On[- ]site|India|USA|UK)", text, re.I)

            jobs.append({
                "title": title,
                "url": url,
                "location": loc.group(1) if loc else "Not Defined",
                "date": "Not Defined"
            })

        if len(jobs) >= max_jobs:
            break

    return jobs

# ================= MAIN ================= #

def main():
    print("📄 Reading:", INPUT_FILE)
    df = pd.read_excel(INPUT_FILE).head(120).copy()

    required = [
        "Careers Page URL", "Job listings page URL",
        "job post1 URL", "job post1 title", "Job 1 Location", "Job 1 Post Date",
        "job post2 URL", "job post2 title", "Job 2 Location", "Job 2 Post Date",
        "job post3 URL", "job post3 title", "Job 3 Location", "Job 3 Post Date",
        "Scraping Status"
    ]

    for c in required:
        if c not in df.columns:
            df[c] = ""

    for idx, row in df.iterrows():
        website = clean_url(row.get("Website URL"))

        if not website:
            df.at[idx, "Scraping Status"] = "Invalid"
            continue

        careers = find_careers_page(website)
        if not careers:
            df.at[idx, "Scraping Status"] = "No Career Page"
            continue

        listings = find_job_listings_page(careers)

        df.at[idx, "Careers Page URL"] = careers
        df.at[idx, "Job listings page URL"] = listings

        jobs = scrape_jobs(listings)
        if not jobs:
            df.at[idx, "Scraping Status"] = "Career page but no jobs"
            continue

        for i, job in enumerate(jobs, 1):
            df.at[idx, f"job post{i} URL"] = job["url"]
            df.at[idx, f"job post{i} title"] = job["title"]
            df.at[idx, f"Job {i} Location"] = job["location"]
            df.at[idx, f"Job {i} Post Date"] = job["date"]

        df.at[idx, "Scraping Status"] = "Job Found"
        time.sleep(1.5)

    # 🔥 WRITE TEMP FILE FIRST
    df.to_excel(TEMP_FILE, index=False)
    print("✅ Temp file written:", TEMP_FILE)

    # 🔥 ATOMIC REPLACE (FORCES ONEDRIVE UPDATE)
    os.remove(INPUT_FILE)
    shutil.move(TEMP_FILE, INPUT_FILE)

    print("🎯 input.xlsx UPDATED SUCCESSFULLY")

if __name__ == "__main__":
    main()
