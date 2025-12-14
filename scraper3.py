import requests
import pandas as pd
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

CAREER_KEYWORDS = ["career", "careers", "jobs", "join", "hiring"]
ATS_DOMAINS = ["lever.co", "greenhouse.io", "workable.com", "zohorecruit", "ashbyhq"]

# ---------------- HELPERS ---------------- #

def clean_url(url):
    if not isinstance(url, str) or not url.strip():
        return None
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code < 400:
            return BeautifulSoup(r.text, "lxml")
    except:
        return None
    return None


# ---------------- CAREERS PAGE ---------------- #

def find_careers_page(home_url):
    soup = fetch(home_url)
    if not soup:
        return None

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        href = a["href"].lower()
        if any(k in text or k in href for k in CAREER_KEYWORDS):
            return urljoin(home_url, a["href"])

    for path in ["/careers", "/jobs", "/join-us"]:
        test = home_url.rstrip("/") + path
        if fetch(test):
            return test

    return None


# ---------------- JOB LISTINGS PAGE ---------------- #

def find_job_listings_page(careers_url):
    soup = fetch(careers_url)
    if not soup:
        return careers_url

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        if any(k in text for k in ["open positions", "view jobs", "see openings"]):
            return urljoin(careers_url, a["href"])

    for a in soup.find_all("a", href=True):
        if any(ats in a["href"].lower() for ats in ATS_DOMAINS):
            return urljoin(careers_url, a["href"])

    return careers_url


# ---------------- JOB SCRAPING ---------------- #

def scrape_jobs(listing_url, max_jobs=7):
    soup = fetch(listing_url)
    if not soup:
        return []

    jobs = []
    seen = set()

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"].lower()

        if (
            len(title) > 8
            and any(k in href for k in ["job", "opening", "position"])
            and not any(x in href for x in ["privacy", "blog", "about"])
        ):
            full_url = urljoin(listing_url, a["href"])
            if full_url in seen:
                continue
            seen.add(full_url)

            jsoup = fetch(full_url)
            if not jsoup:
                continue

            text = jsoup.get_text(" ", strip=True)

            location = "Not specified"
            loc = re.search(r"(Remote|Hybrid|On[- ]site|Sydney|India|USA|UK)", text, re.I)
            if loc:
                location = loc.group(1)

            jobs.append({
                "title": title,
                "url": full_url,
                "location": location
            })

        if len(jobs) >= max_jobs:
            break

    return jobs


# ---------------- MAIN ---------------- #

def main():
    INPUT_FILE = "input.xlsx"

    # ✅ UNIQUE OUTPUT FILE — NEVER LOCKED
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    OUTPUT_FILE = f"output_{timestamp}.xlsx"

    df = pd.read_excel(INPUT_FILE)
    df_out = df.copy().head(40)  # ✅ FIRST 40 COMPANIES

    for idx, row in df_out.iterrows():
        website = clean_url(row.iloc[1])
        if not website:
            df_out.at[idx, "Scraping Status"] = "Invalid website"
            continue

        careers = find_careers_page(website)
        if not careers:
            df_out.at[idx, "Scraping Status"] = "No careers page"
            continue

        listings = find_job_listings_page(careers)

        df_out.at[idx, "Careers Page"] = careers
        df_out.at[idx, "Job Listings Page"] = listings

        jobs = scrape_jobs(listings)

        if not jobs:
            df_out.at[idx, "Scraping Status"] = "No jobs found"
            continue

        # ✅ SEQUENTIAL JOB FILLING (NO GAPS)
        for i, job in enumerate(jobs, start=1):
            if i > 7:
                break
            df_out.at[idx, f"Job {i} Title"] = job["title"]
            df_out.at[idx, f"Job {i} URL"] = job["url"]
            df_out.at[idx, f"Job {i} Location"] = job["location"]

        df_out.at[idx, "Scraping Status"] = "Success"
        time.sleep(2)

    # ✅ SAFE WRITE — NO PERMISSION ISSUE POSSIBLE
    df_out.to_excel(OUTPUT_FILE, index=False)
    print(f"✅ Scraping completed. Output saved as: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
