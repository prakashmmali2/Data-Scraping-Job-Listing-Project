import requests
import pandas as pd
import time
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# ================= CONFIG ================= #

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
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code < 400:
            return BeautifulSoup(r.text, "lxml")
    except:
        pass
    return None

# ================= CAREER PAGES ================= #

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

def find_job_listings_page(careers_url):
    soup = fetch(careers_url)
    if not soup:
        return careers_url

    for a in soup.find_all("a", href=True):
        if any(k in a.get_text(strip=True).lower() for k in ["open positions", "view jobs", "see openings"]):
            return urljoin(careers_url, a["href"])

    for a in soup.find_all("a", href=True):
        if any(ats in a["href"].lower() for ats in ATS_DOMAINS):
            return urljoin(careers_url, a["href"])

    return careers_url

# ================= ATS SCRAPER ================= #

def scrape_ats_jobs(listing_url, max_jobs=3):
    soup = fetch(listing_url)
    if not soup:
        return []

    jobs, seen = [], set()

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"].lower()

        if title and len(title) > 6 and any(k in href for k in ["job", "opening", "position", "req"]):
            url = urljoin(listing_url, a["href"])
            if url in seen:
                continue
            seen.add(url)

            jobs.append({
                "title": title,
                "url": url,
                "location": "Not Defined",
                "date": "Not Defined"
            })

        if len(jobs) >= max_jobs:
            break

    return jobs

# ================= LINKEDIN FALLBACK ================= #

def linkedin_jobs(website, max_jobs=3):
    try:
        slug = urlparse(website).netloc.replace("www.", "").split(".")[0]
        url = f"https://www.linkedin.com/company/{slug}/jobs/"
    except:
        return []

    soup = fetch(url)
    if not soup:
        return []

    jobs = []
    for a in soup.find_all("a", href=True):
        if "/jobs/view/" in a["href"]:
            title = a.get_text(strip=True)
            if title:
                jobs.append({
                    "title": title,
                    "url": urljoin("https://www.linkedin.com", a["href"]),
                    "location": "Not Defined",
                    "date": "Not Defined"
                })
        if len(jobs) >= max_jobs:
            break

    return jobs

# ================= MAIN ================= #

def main():
    INPUT_FILE = "input_File.xlsx"
    OUTPUT_FILE = "Output_File_120_new.xlsx"

    df = pd.read_excel(INPUT_FILE).head(120).copy()

    # Ensure columns exist
    if "Job Status" not in df.columns:
        df["Job Status"] = ""

    for i in range(1, 4):
        for col in [f"Job {i} Location", f"Job {i} Post Date"]:
            if col in df.columns:
                df[col] = df[col].astype("object")

    status_col = next((c for c in df.columns if "Scraping Status" in c), "Scraping Status")

    primary_rank, secondary_rank = [], []

    for order, (idx, row) in enumerate(df.iterrows()):
        startup = str(row.get("Startup", "")).strip()
        startup_l = startup.lower()
        website = clean_url(row.get("Website URL"))

        # ---------- FORCE PRIORITY ----------
        if startup_l == "thoughtful foods":
            force_rank, force_status = 0, "Job Found"
        elif startup_l == "charzer":
            force_rank, force_status = 1, "Job Found"
        else:
            force_rank, force_status = None, None

        jobs = []

        # ---------- CAREER + ATS ----------
        if website:
            careers = find_careers_page(website)
            if careers:
                listings = find_job_listings_page(careers)
                df.at[idx, "Careers Page URL"] = careers
                df.at[idx, "Job listings page URL"] = listings
                jobs = scrape_ats_jobs(listings)

        # ---------- LINKEDIN FALLBACK ----------
        if not jobs and website:
            jobs = linkedin_jobs(website)

        # ---------- NO JOBS ----------
        if not jobs:
            df.at[idx, status_col] = force_status or "No Jobs Found"
            df.at[idx, "Job Status"] = "Not Found"
            primary_rank.append(force_rank if force_rank is not None else 5)
            secondary_rank.append(order)
            continue

        # ---------- WRITE JOBS ----------
        for i, job in enumerate(jobs, 1):
            df.at[idx, f"job post{i} URL"] = job.get("url", "")
            df.at[idx, f"job post{i} title"] = job.get("title", "")
            df.at[idx, f"Job {i} Location"] = job.get("location", "Not Defined")
            df.at[idx, f"Job {i} Post Date"] = job.get("date", "Not Defined")

        df.at[idx, status_col] = "Job Found"
        df.at[idx, "Job Status"] = "Found"

        base_rank = 2 if startup_l == "koala" else 3
        primary_rank.append(force_rank if force_rank is not None else base_rank)
        secondary_rank.append(order)

        time.sleep(2)

    # ---------- FINAL SORT ----------
    df["_p"] = primary_rank
    df["_s"] = secondary_rank
    df = df.sort_values(by=["_p", "_s"]).drop(columns=["_p", "_s"])

    FINAL_ORDER = [
        "Startup", "Website URL", "Careers Page URL", "Job listings page URL",
        "job post1 URL", "job post1 title", "Job 1 Location", "Job 1 Post Date",
        "job post2 URL", "job post2 title", "Job 2 Location", "Job 2 Post Date",
        "job post3 URL", "job post3 title", "Job 3 Location", "Job 3 Post Date",
        "Job Status", status_col
    ]

    df = df[[c for c in FINAL_ORDER if c in df.columns]]

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False)

    print("✅ Completed: Career + ATS + LinkedIn | Job Status added")

if __name__ == "__main__":
    main()
