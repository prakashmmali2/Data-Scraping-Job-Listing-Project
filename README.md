# 🔎 Startup Job Scraper (Career + ATS + LinkedIn)

A **production-style Python scraper** that discovers and organizes **active job openings** for startups by scanning:

- Official **Career pages**
- Popular **ATS platforms** (Lever, Greenhouse, Ashby, Workable, Zoho)
- **LinkedIn Jobs** (safe fallback)

The output is a **clean, ranked Excel file** with job titles, locations, posting dates, and a clear job status — suitable for analysis, internships, and research.

---

## ✨ Key Features

✅ Intelligent Career Page Detection  
✅ ATS-aware Job Scraping  
✅ LinkedIn Jobs Fallback  
✅ Fake / Non-job Title Filtering  
✅ Title ↔ Location Separation  
✅ Month-Year Job Date Generation (e.g. *December 2025*)  
✅ Deterministic Company Ranking  
✅ Auto-generated **Methodology Sheet**  
✅ Excel-ready Output (No schema break)

---

## 🧠 Ranking Logic (Auto-Sorted)

| Priority | Rule |
|--------|------|
| 0 | Thoughtful Foods |
| 1 | Charzer |
| 2 | 3 jobs with complete info |
| 3 | 2 jobs with complete info |
| 4 | 1 job with complete info |
| 5 | 3 jobs with partial info |
| 6 | 1–2 jobs with partial info |
| 7 | Career page found only |
| 8 | Only name + website |

---

## 📁 Output Structure

**Sheet 1 – Job_List**
- Startup Name
- Website URL
- Careers Page URL
- Job Listings Page URL
- Job Post URLs (1–3)
- Job Titles
- Job Locations
- Job Post Dates
- Job Status (Found / Not Found)

**Sheet 2 – Methodology**
- Scraping steps followed
- Platforms checked
- ATS handling approach
- Summary statistics:
  - Total companies processed
  - Companies with jobs
  - Total jobs found

---

## 🛠️ Tech Stack

- **Python 3**
- `requests`
- `BeautifulSoup`
- `pandas`
- `openpyxl`

---

## 🚀 How to Run

```bash
pip install requests beautifulsoup4 pandas openpyxl
python job_scraper.py
