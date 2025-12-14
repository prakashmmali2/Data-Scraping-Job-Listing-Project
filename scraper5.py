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

def scrape_jobs(listing_url, max_jobs=3):
    soup = fetch(listing_url)
    if not soup:
        return []

    jobs = []
    seen = set()

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"].lower()

        if (
            title and len(title) > 8
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

            location = ""
            loc = re.search(r"(Remote|Hybrid|On[- ]site|India|USA|UK|Sydney|Melbourne)", text, re.I)
            if loc:
                location = loc.group(1)

            post_date = ""
            date_match = re.search(r"(Posted\s*\w+|\b202[4-5]\b)", text, re.I)
            if date_match:
                post_date = date_match.group(1)

            jobs.append({
                "url": full_url,
                "title": title,
                "location": location,
                "date": post_date
            })

        if len(jobs) >= max_jobs:
            break

    return jobs


# ---------------- MAIN ---------------- #

def main():
    FILE_PATH = "input.xlsx"

    df = pd.read_excel(FILE_PATH)
    df = df.head(50).copy()

    if not any("Scraping Status" in c for c in df.columns):
        df["Scraping Status"] = ""

    status_col = [c for c in df.columns if "Scraping Status" in c][0]

    # Initialize job-related columns with string dtype to avoid dtype warnings
    for i in range(1, 4):  # Assuming max 3 jobs
        df[f"Job Post {i} URL"] = df.get(f"Job Post {i} URL", pd.Series(dtype=str))
        df[f"Job Post {i} Title"] = df.get(f"Job Post {i} Title", pd.Series(dtype=str))
        df[f"Job {i} Location"] = df.get(f"Job {i} Location", pd.Series(dtype=str))
        df[f"Job {i} Post Date"] = df.get(f"Job {i} Post Date", pd.Series(dtype=str))

    # Initialize other columns
    df["Careers Page URL"] = df.get("Careers Page URL", pd.Series(dtype=str))
    df["Job Listings Page URL"] = df.get("Job Listings Page URL", pd.Series(dtype=str))

    priority_rank = []

    for idx, row in df.iterrows():
        website = clean_url(row.get("Website URL"))

        if not website:
            df.at[idx, status_col] = "Invalid Website"
            priority_rank.append(5)
            continue

        careers = find_careers_page(website)
        if not careers:
            df.at[idx, status_col] = "No Career Page"
            priority_rank.append(4)
            continue

        listings = find_job_listings_page(careers)

        df.at[idx, "Careers Page URL"] = careers
        df.at[idx, "Job Listings Page URL"] = listings

        jobs = scrape_jobs(listings)

        if not jobs:
            df.at[idx, status_col] = "Career page but no jobs"
            priority_rank.append(3)
            continue

        for i, job in enumerate(jobs, start=1):
            df.at[idx, f"Job Post {i} URL"] = job["url"]
            df.at[idx, f"Job Post {i} Title"] = job["title"]
            df.at[idx, f"Job {i} Location"] = job["location"]
            df.at[idx, f"Job {i} Post Date"] = job["date"]

        df.at[idx, status_col] = "Jobs Found"
        priority_rank.append(1)

        time.sleep(2)

    df["_sort"] = priority_rank
    df = df.sort_values("_sort").drop(columns="_sort")

    # ✅ OVERWRITE SAME FILE
    with pd.ExcelWriter(FILE_PATH, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False)

    print("✅ File updated successfully (overwritten & sorted)")


if __name__ == "__main__":
    main()
