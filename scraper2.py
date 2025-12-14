import requests
import pandas as pd
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

CAREER_KEYWORDS = ["career", "careers", "jobs", "join", "hiring"]
ATS_DOMAINS = ["lever.co", "greenhouse.io", "workable.com", "zohorecruit", "ashbyhq"]

# ---------------- BASIC HELPERS ---------------- #

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code < 400:
            return BeautifulSoup(r.text, "lxml")
    except:
        return None
    return None


def clean_url(url):
    if not isinstance(url, str) or not url.strip():
        return None
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


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

def scrape_jobs(listing_url):
    soup = fetch(listing_url)
    if not soup:
        return []

    job_links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        text = a.get_text(strip=True)

        if (
            len(text) > 8
            and any(k in href for k in ["job", "opening", "position"])
            and not any(x in href for x in ["privacy", "blog", "about"])
        ):
            job_links.append(urljoin(listing_url, a["href"]))

    job_links = list(dict.fromkeys(job_links))[:3]

    jobs = []
    for link in job_links:
        jsoup = fetch(link)
        if not jsoup:
            continue

        title = jsoup.find("h1")
        title = title.get_text(strip=True) if title else "Not specified"

        text = jsoup.get_text(" ", strip=True)

        location = "Not specified"
        loc = re.search(r"(Remote|Hybrid|On[- ]site|India|USA|UK)", text, re.I)
        if loc:
            location = loc.group(1)

        jobs.append({
            "title": title,
            "url": link,
            "location": location
        })

    return jobs


# ---------------- MAIN ---------------- #

def main():
    INPUT_FILE = "input.xlsx"
    OUTPUT_FILE = "output.xlsx"

    df = pd.read_excel(INPUT_FILE)
    df_out = df.copy().head(30)   # 🔴 FIRST 30 ONLY

    # Standardized columns
    columns = [
        "Careers Page",
        "Job Listings Page",
        "Job 1 Title", "Job 1 URL", "Job 1 Location",
        "Job 2 Title", "Job 2 URL", "Job 2 Location",
        "Job 3 Title", "Job 3 URL", "Job 3 Location",
        "Scraping Status"
    ]

    for col in columns:
        if col not in df_out.columns:
            df_out[col] = ""

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
        jobs = scrape_jobs(listings)

        df_out.at[idx, "Careers Page"] = careers
        df_out.at[idx, "Job Listings Page"] = listings

        if not jobs:
            df_out.at[idx, "Scraping Status"] = "No jobs found"
            continue

        for i, job in enumerate(jobs, start=1):
            df_out.at[idx, f"Job {i} Title"] = job["title"]
            df_out.at[idx, f"Job {i} URL"] = job["url"]
            df_out.at[idx, f"Job {i} Location"] = job["location"]

        df_out.at[idx, "Scraping Status"] = "Success"
        time.sleep(2)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Data")

        pd.DataFrame({
            "Methodology": [
                "Processed first 30 companies for validation.",
                "Identified careers pages via homepage links and common paths.",
                "Detected job listing pages using CTA buttons and ATS domains.",
                "Extracted up to 3 recent job postings per company.",
                "Preserved original Excel structure and columns."
            ]
        }).to_excel(writer, index=False, sheet_name="Methodology")

    print("✅ Scraping completed for first 30 companies.")


if __name__ == "__main__":
    main()
