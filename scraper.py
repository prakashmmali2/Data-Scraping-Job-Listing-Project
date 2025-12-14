import pandas as pd
import requests
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

CAREER_KEYWORDS = [
    "career", "careers", "jobs", "join-us",
    "work-with-us", "openings"
]

ATS_KEYWORDS = [
    "lever.co",
    "greenhouse.io",
    "workable.com",
    "zoho.com/recruit",
    "apply.workable.com"
]


# ---------------------------
# Utility Functions
# ---------------------------

def fetch_page(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, "lxml")
    except Exception:
        return None
    return None


def find_career_page(homepage_url):
    soup = fetch_page(homepage_url)
    if not soup:
        return None

    for link in soup.find_all("a", href=True):
        href = link["href"].lower()
        if any(keyword in href for keyword in CAREER_KEYWORDS):
            return urljoin(homepage_url, link["href"])

    return None


def detect_ats(url):
    return any(ats in url for ats in ATS_KEYWORDS)


# ---------------------------
# Job Scrapers
# ---------------------------

def scrape_ats_jobs(job_page_url, company_name):
    jobs = []
    soup = fetch_page(job_page_url)
    if not soup:
        return jobs

    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)

        if len(text) > 5 and "job" in href.lower():
            jobs.append({
                "Company": company_name,
                "Job Title": text,
                "Location": "Not specified",
                "Job Link": urljoin(job_page_url, href),
                "Source": "Career Page"
            })

        if len(jobs) >= 3:
            break

    return jobs


def scrape_simple_jobs(job_page_url, company_name):
    jobs = []
    soup = fetch_page(job_page_url)
    if not soup:
        return jobs

    job_cards = soup.find_all(["li", "div"], limit=10)

    for card in job_cards:
        title = card.get_text(strip=True)
        if len(title) > 10:
            jobs.append({
                "Company": company_name,
                "Job Title": title,
                "Location": "Not specified",
                "Job Link": job_page_url,
                "Source": "Career Page"
            })

        if len(jobs) >= 3:
            break

    return jobs


def fallback_indeed(company_name):
    search_url = f"https://www.indeed.com/jobs?q={company_name}"
    return [{
        "Company": company_name,
        "Job Title": "Jobs on Indeed",
        "Location": "Check link",
        "Job Link": search_url,
        "Source": "Indeed"
    }]


# ---------------------------
# MAIN PIPELINE
# ---------------------------

def run_scraper(input_file, output_file):
    df = pd.read_excel(input_file)

    # 🔴 IMPORTANT: ONLY FIRST 30 COMPANIES
    df = df.head(30)

    all_jobs = []

    for index, row in df.iterrows():
        company = row.get("Company Name") or row.get("Company")
        website = row.get("Website")

        if not isinstance(website, str):
            continue

        print(f"\n[{index+1}] Processing: {company}")

        career_page = find_career_page(website)

        if not career_page:
            print("  ❌ Career page not found → fallback")
            all_jobs.extend(fallback_indeed(company))
            continue

        print(f"  ✅ Career Page: {career_page}")

        if detect_ats(career_page):
            jobs = scrape_ats_jobs(career_page, company)
        else:
            jobs = scrape_simple_jobs(career_page, company)

        if not jobs:
            print("  ⚠ No jobs found → fallback")
            jobs = fallback_indeed(company)

        all_jobs.extend(jobs)

        time.sleep(random.uniform(2, 4))  # polite scraping

    output_df = pd.DataFrame(all_jobs)
    output_df.to_excel(output_file, index=False)
    print("\n✅ Scraping completed for first 30 companies.")


# ---------------------------
# RUN
# ---------------------------

if __name__ == "__main__":
    run_scraper("input.xlsx", "output.xlsx")
