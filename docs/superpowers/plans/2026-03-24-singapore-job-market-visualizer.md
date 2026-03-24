# Singapore Job Market Visualizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the US BLS-based Job Market Visualizer to use Singapore data sources (MOM, SkillsFuture, Census 2021)

**Architecture:** Multi-phase data pipeline: (1) Scrape Singapore data → (2) Parse to SSOC-based structure → (3) Generate CSV/JSON → (4) Build frontend → (5) LLM AI scoring

**Tech Stack:** Python 3.12+, Playwright, BeautifulSoup, pandas, OpenRouter API, HTML5 Canvas

---

## File Structure Overview

### New Files to Create
```
sg_scrape.py           # MOM/SkillsFuture data scraper
sg_parse.py            # Parse Singapore data to Markdown
sg_process.py          # Process Skills Framework job descriptions
sg_make_csv.py         # Generate Singapore occupations.csv
sg_score.py            # AI exposure scoring for Singapore (uses score.py)
build_sg_data.py       # Build site/data.json from Singapore data
sg_occupations.json    # Master Singapore occupation list (SSOC-based)
ssoc_mapping.json      # SSOC to SkillsFramework mapping
```

### Files to Modify
```
site/index.html        # Update labels, remove BLS references
README.md              # Update for Singapore context
score.py               # Adapt prompt for Singapore context (optional)
```

### Files to Keep Unchanged
```
build_site_data.py     # Keep for US version reference
parse_detail.py        # Keep for reference
process.py             # Keep for reference
```

---

## PHASE 1: Data Collection (2-3 weeks)

### Task 1.1: Set up Singapore data scraper infrastructure

**Files:**
- Create: `sg_scrape.py`
- Create: `.env.sg` (example)

- [ ] **Step 1: Create environment file template**

```bash
# .env.sg.example
OPENROUTER_API_KEY=your_key_here
SG_DATA_DIR=./sg_data
```

- [ ] **Step 2: Run to create .env file**

```bash
cp .env.sg.example .env
```

- [ ] **Step 3: Create base scraper skeleton**

```python
# sg_scrape.py
"""
Singapore job market data scraper.

Scrapes:
1. MOM Occupational Wage Tables
2. SkillsFuture Skills Frameworks (30+ industries)
3. Census 2021 employment data (manual download + parse)

Usage:
    uv run python sg_scrape.py --source wages
    uv run python sg_scrape.py --source skills
    uv run python sg_scrape.py --all
"""

import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urljoin

import requests
from playwright.async_api import async_playwright


class SingaporeDataScraper:
    """Scraper for Singapore job market data"""

    BASE_URL = {
        "mom": "https://www.mom.gov.sg",
        "skillsfuture": "https://www.skillsfuture.gov.sg",
        "census": "https://www.singstat.gov.sg"
    }

    def __init__(self, data_dir: str = "./sg_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }

    async def scrape_wage_tables(self):
        """Scrape MOM Occupational Wage Tables"""
        print("Scraping MOM Occupational Wage Tables...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # MOM may block headless
            page = await browser.new_page()

            # Navigate to wage tables page
            url = f"{self.BASE_URL['mom']}/employment-practices/wage-practices/occupational-wage-tables"
            await page.goto(url, wait_until="networkidle")

            # Wait for page to load
            await page.wait_for_selector("table", timeout=10000)

            # Extract download links for Excel files
            download_links = await page.eval_on_selector_all(
                "a[href*='.xlsx'], a[href*='.xls']",
                "els => els.map(el => ({ text: el.textContent, href: el.href }))"
            )

            print(f"Found {len(download_links)} download links")

            # Download each file
            for link in download_links:
                href = link.get("href")
                text = link.get("text", "wage_table")

                if href:
                    filename = self.data_dir / f"wages_{text.strip().replace(' ', '_')}.xlsx"
                    await self._download_file(page, href, filename)
                    print(f"Downloaded: {filename}")

            await browser.close()

    async def _download_file(self, page, url: Path, dest_path: Path):
        """Download file from URL"""
        try:
            response = await page.request.get(url)
            content = await response.body()

            with open(dest_path, "wb") as f:
                f.write(content)

        except Exception as e:
            print(f"Failed to download {url}: {e}")

    async def scrape_skills_frameworks(self):
        """Scrape SkillsFuture Skills Frameworks"""

        print("Scraping SkillsFuture Skills Frameworks...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Navigate to skills frameworks page
            url = f"{self.BASE_URL['skillsfuture']}/skills-frameworks"
            await page.goto(url, wait_until="networkidle")

            # Extract framework links
            framework_links = await page.eval_on_selector_all(
                "a[href*='/skills-frameworks/']",
                "els => els.map(el => ({ text: el.textContent, href: el.href }))"
            )

            print(f"Found {len(framework_links)} skills frameworks")

            # Scrape each framework
            for link in framework_links:
                framework_name = link.get("text", "").strip()
                framework_url = link.get("href")

                if framework_url:
                    await self._scrape_single_framework(page, framework_url, framework_name)

            await browser.close()

    async def _scrape_single_framework(self, page, url: str, name: str):
        """Scrape a single skills framework"""
        try:
            await page.goto(url, wait_until="networkidle")

            # Extract job roles
            job_roles = await page.eval_on_selector_all(
                ".job-role, [data-job-role]",
                "els => els.map(el => ({ title: el.textContent, description: el.getAttribute('data-description') }))"
            )

            # Save to JSON
            output_file = self.data_dir / f"skills_{name.replace(' ', '_')}.json"
            with open(output_file, "w") as f:
                json.dump({
                    "framework": name,
                    "url": url,
                    "job_roles": job_roles
                }, f, indent=2)

            print(f"Saved: {output_file}")

        except Exception as e:
            print(f"Failed to scrape {name}: {e}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Singapore job market data")
    parser.add_argument("--source", choices=["wages", "skills", "all"], default="all")
    parser.add_argument("--data-dir", default="./sg_data")
    args = parser.parse_args()

    scraper = SingaporeDataScraper(data_dir=args.data_dir)

    if args.source in ["wages", "all"]:
        await scraper.scrape_wage_tables()

    if args.source in ["skills", "all"]:
        await scraper.scrape_skills_frameworks()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Test basic scraper structure**

```bash
uv run python sg_scrape.py --help
```

Expected: Help message displays

- [ ] **Step 5: Commit scraper skeleton**

```bash
git add sg_scrape.py .env.sg.example
git commit -m "feat: add Singapore data scraper skeleton"
```

---

### Task 1.2: Implement MOM Wage Table scraper

**Files:**
- Modify: `sg_scrape.py` (add wage scraping logic)

- [ ] **Step 1: Install dependencies**

```bash
uv add playwright openpyxl pandas
```

- [ ] **Step 2: Add wage table extraction to scraper**

```python
# Add to SingaporeDataScraper class in sg_scrape.py

async def extract_wage_data_from_excel(self, excel_path: Path) -> list:
    """Extract wage data from downloaded Excel file"""
    import pandas as pd

    try:
        # Read Excel file
        df = pd.read_excel(excel_path)

        # Expected columns: Occupation, SSOC_Code, Median_25, Median_50, Median_75
        wage_data = []

        for _, row in df.iterrows():
            wage_data.append({
                "occupation": row.get("Occupation", ""),
                "ssoc_code": str(row.get("SSOC_Code", "")),
                "median_25": float(row.get("Median_25", 0)) if pd.notna(row.get("Median_25")) else None,
                "median_50": float(row.get("Median_50", 0)) if pd.notna(row.get("Median_50")) else None,
                "median_75": float(row.get("Median_75", 0)) if pd.notna(row.get("Median_75")) else None,
            })

        return wage_data

    except Exception as e:
        print(f"Error reading {excel_path}: {e}")
        return []
```

- [ ] **Step 3: Save extracted wage data**

```python
# Add to SingaporeDataScraper class

def save_wage_data(self, wage_data: list):
    """Save wage data to JSON"""
    output_path = self.data_dir / "wages_extracted.json"

    with open(output_path, "w") as f:
        json.dump(wage_data, f, indent=2)

    print(f"Saved {len(wage_data)} wage records to {output_path}")
```

- [ ] **Step 4: Test wage extraction**

```bash
# First download a sample wage table manually, then test
uv run python -c "
import asyncio
from sg_scrape import SingaporeDataScraper

scraper = SingaporeDataScraper()
data = asyncio.run(scraper.extract_wage_data_from_excel(Path('sg_data/sample_wage.xlsx')))
print(f'Extracted {len(data)} records')
"
```

- [ ] **Step 5: Commit wage extraction**

```bash
git add sg_scrape.py
git commit -m "feat: add MOM wage table extraction"
```

---

### Task 1.3: Implement Skills Framework scraper

**Files:**
- Modify: `sg_scrape.py` (add skills framework scraping)

- [ ] **Step 1: Add skills framework job role extraction**

```python
# Add to SingaporeDataScraper class in sg_scrape.py

SKILLS_FRAMEWORKS = [
    "accountancy",
    "infocomm-technology",
    "financial-services",
    "logistics",
    "precision-engineering",
    "retail",
    # Add all 30+ frameworks...
]

async def scrape_all_skills_frameworks(self):
    """Scrape all SkillsFuture frameworks"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        all_job_roles = []

        for framework in self.SKILLS_FRAMEWORKS:
            url = f"{self.BASE_URL['skillsfuture']}/skills-frameworks/{framework}"
            job_roles = await self._scrape_framework_job_roles(context, url, framework)
            all_job_roles.extend(job_roles)

        # Save combined data
        output_path = self.data_dir / "skills_job_roles.json"
        with open(output_path, "w") as f:
            json.dump(all_job_roles, f, indent=2)

        print(f"Saved {len(all_job_roles)} job roles from {len(self.SKILLS_FRAMEWORKS)} frameworks")

        await browser.close()

async def _scrape_framework_job_roles(self, context, url: str, framework: str) -> list:
    """Scrape job roles from a single framework"""
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")

        # Extract job role data
        job_roles = await page.eval_on_selector_all(
            "[data-job-role], .job-role-card",
            """els => els.map(el => ({
                title: el.querySelector('.job-title')?.textContent || el.textContent,
                description: el.querySelector('.description')?.textContent || '',
                skills: Array.from(el.querySelectorAll('.skill-tag')).map(s => s.textContent)
            }))"""
        )

        await page.close()

        return [{"framework": framework, **role} for role in job_roles]

    except Exception as e:
        print(f"Error scraping {framework}: {e}")
        return []
```

- [ ] **Step 2: Test skills framework scraping**

```bash
uv run python sg_scrape.py --source skills
```

Expected: Skills data downloaded to `sg_data/skills_job_roles.json`

- [ ] **Step 3: Commit skills framework scraper**

```bash
git add sg_scrape.py
git commit -m "feat: add SkillsFuture framework scraper"
```

---

### Task 1.4: Create SSOC occupation master list

**Files:**
- Create: `sg_occupations.json`
- Create: `sg_make_master_list.py`

- [ ] **Step 1: Create SSOC master list generator**

```python
# sg_make_master_list.py
"""
Generate master Singapore occupation list based on SSOC 2020.

SSOC 2020 has 510 detailed occupations (4-digit codes).
This script creates a master list from:
1. SSOC 2020 classification
2. MOM Occupational Wage Tables
3. SkillsFuture job roles

Output: sg_occupations.json
"""

import json
from pathlib import Path


# SSOC 2020 Major Groups (10 categories)
SSOC_MAJOR_GROUPS = {
    "1": "Managers",
    "2": "Professionals",
    "3": "Associate Professionals and Technicians",
    "4": "Clerical Support Workers",
    "5": "Service and Sales Workers",
    "6": "Skilled Agricultural and Fishery Workers",
    "7": "Craftsmen and Related Trades Workers",
    "8": "Plant and Machine Operators and Assemblers",
    "9": "Cleaners, Labourers and Related Workers",
    "0": "Armed Forces"
}


# Sample SSOC occupations (expand to 510)
SSOC_OCCUPATIONS = [
    {"code": "1111", "title": "Chief Executives and Managing Directors", "category": "Managers"},
    {"code": "1112", "title": "Legislators and Senior Officials", "category": "Managers"},
    {"code": "1120", "title": "General Managers", "category": "Managers"},
    # ... add all 510 occupations
]


def load_ssoc_from_pdf():
    """
    Load SSOC 2020 classification from PDF.

    Download SSOC 2020 PDF from:
    https://www.singstat.gov.sg/-/media/files/standards_and_classifications/ssoc2020.pdf

    For now, return hardcoded sample.
    """
    return SSOC_OCCUPATIONS


def load_wage_occupations():
    """Load occupations from wage data"""
    wage_file = Path("sg_data/wages_extracted.json")

    if wage_file.exists():
        with open(wage_file) as f:
            wage_data = json.load(f)

        # Extract unique occupations
        occupations = {}
        for record in wage_data:
            ssoc_code = record.get("ssoc_code", "")
            title = record.get("occupation", "")

            if ssoc_code and title:
                occupations[ssoc_code] = {
                    "code": ssoc_code,
                    "title": title,
                    "category": SSOC_MAJOR_GROUPS.get(ssoc_code[0], "Other")
                }

        return list(occupations.values())

    return []


def load_skills_occupations():
    """Load job roles from SkillsFuture frameworks"""
    skills_file = Path("sg_data/skills_job_roles.json")

    if skills_file.exists():
        with open(skills_file) as f:
            skills_data = json.load(f)

        # Map job roles to SSOC codes (manual mapping required)
        # For now, return as-is
        return skills_data

    return []


def merge_sources():
    """Merge all occupation sources"""
    ssoc_jobs = load_ssoc_from_pdf()
    wage_jobs = load_wage_occupations()
    skills_jobs = load_skills_occupations()

    # Create master list
    master_list = []

    for job in ssoc_jobs:
        master_list.append({
            "code": job["code"],
            "title": job["title"],
            "category": job["category"],
            "slug": slugify(job["title"]),
            "sources": ["ssoc"]
        })

    # Add wage data
    wage_dict = {j["code"]: j for j in wage_jobs}
    for job in master_list:
        if job["code"] in wage_dict:
            job["sources"].append("wage")

    # Add skills data
    for skill_role in skills_jobs:
        # Try to match by title
        for job in master_list:
            if skill_role["title"].lower() in job["title"].lower():
                job["sources"].append("skills")
                job["skills_framework"] = skill_role.get("framework")
                break

    return master_list


def slugify(title: str) -> str:
    """Convert title to URL-friendly slug"""
    return title.lower().replace(" ", "-").replace("/", "-").replace("(", "").replace(")", "")


def main():
    """Generate master occupation list"""
    master_list = merge_sources()

    # Sort by category, then title
    master_list.sort(key=lambda x: (x["category"], x["title"]))

    # Save to JSON
    output_path = Path("sg_occupations.json")

    with open(output_path, "w") as f:
        json.dump(master_list, f, indent=2)

    print(f"Generated {len(master_list)} occupations to {output_path}")

    # Print summary by category
    from collections import Counter
    category_counts = Counter(j["category"] for j in master_list)

    print("\nOccupations by category:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run master list generator**

```bash
uv run python sg_make_master_list.py
```

- [ ] **Step 3: Verify output**

```bash
cat sg_occupations.json | jq '. | length'
```

Expected: JSON file with 510 occupations

- [ ] **Step 4: Commit master list**

```bash
git add sg_make_master_list.py sg_occupations.json
git commit -m "feat: add SSOC occupation master list"
```

---

## PHASE 2: Data Processing (1 week)

### Task 2.1: Create Singapore occupation descriptions from Skills Frameworks

**Files:**
- Create: `sg_parse.py`
- Create: `sg_descriptions/` directory

- [ ] **Step 1: Create description parser**

```python
# sg_parse.py
"""
Parse SkillsFuture job role data into occupation descriptions.

Creates Markdown files similar to BLS OOH pages for each occupation.
"""

import json
from pathlib import Path
from typing import Dict, List


class SingaporeDescriptionParser:
    """Parse job role data into occupation descriptions"""

    def __init__(self, skills_data_path: str = "sg_data/skills_job_roles.json"):
        self.skills_data_path = Path(skills_data_path)
        self.output_dir = Path("sg_descriptions")
        self.output_dir.mkdir(exist_ok=True)

    def load_skills_data(self) -> List[Dict]:
        """Load SkillsFuture job role data"""
        if self.skills_data_path.exists():
            with open(self.skills_data_path) as f:
                return json.load(f)
        return []

    def generate_description(self, job_role: Dict) -> str:
        """Generate Markdown description for a job role"""
        title = job_role.get("title", "")
        description = job_role.get("description", "")
        skills = job_role.get("skills", [])
        framework = job_role.get("framework", "")

        md = f"""# {title}

**Industry Framework:** {framework.replace("-", " ").title()}

## What They Do

{description or "Job role information not available."}

## Skills Required

{chr(10).join(f"- {skill}" for skill in skills) if skills else "No specific skills listed."}

## Related Job Roles

*Job roles from the same framework would be listed here.*

---

*Data source: SkillsFuture Singapore*
"""
        return md

    def parse_all(self):
        """Generate descriptions for all job roles"""
        skills_data = self.load_skills_data()

        print(f"Processing {len(skills_data)} job roles...")

        for job_role in skills_data:
            title = job_role.get("title", "Unknown")
            slug = title.lower().replace(" ", "-").replace("/", "-")

            # Generate description
            description = self.generate_description(job_role)

            # Save to file
            output_path = self.output_dir / f"{slug}.md"

            with open(output_path, "w") as f:
                f.write(description)

        print(f"Generated {len(skills_data)} description files to {self.output_dir}")


def main():
    """Main entry point"""
    parser = SingaporeDescriptionParser()
    parser.parse_all()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test description parser**

```bash
uv run python sg_parse.py
ls sg_descriptions | head -10
```

- [ ] **Step 3: Verify description format**

```bash
cat sg_descriptions/software-engineer.md
```

Expected: Markdown file with job description

- [ ] **Step 4: Commit description parser**

```bash
git add sg_parse.py sg_descriptions/
git commit -m "feat: add Singapore occupation description parser"
```

---

### Task 2.2: Generate Singapore occupations CSV

**Files:**
- Create: `sg_make_csv.py`

- [ ] **Step 1: Create CSV generator**

```python
# sg_make_csv.py
"""
Generate Singapore occupations.csv from multiple data sources.

Combines:
- SSOC occupation master list
- MOM wage data
- SkillsFuture job descriptions
- Census 2021 employment counts (manual)

Output: sg_occupations.csv
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional


def load_master_list() -> List[Dict]:
    """Load SSOC master occupation list"""
    with open("sg_occupations.json") as f:
        return json.load(f)


def load_wage_data() -> Dict[str, Dict]:
    """Load wage data by SSOC code"""
    wage_file = Path("sg_data/wages_extracted.json")

    if wage_file.exists():
        with open(wage_file) as f:
            wage_data = json.load(f)

        # Index by SSOC code
        return {record["ssoc_code"]: record for record in wage_data}

    return {}


def load_census_employment() -> Dict[str, int]:
    """
    Load Census 2021 employment counts.

    For MVP, use sample data.
    Full Census data requires manual extraction from:
    https://www.singstat.gov.sg/-/media/files/publications/cop/cop2021/cop2021sg.pdf
    """
    # Sample employment counts (replace with real Census data)
    return {
        "1111": 45000,  # Chief Executives
        "1120": 120000,  # General Managers
        "2131": 98000,  # Computer Engineers
        # ... add all 510 codes
    }


def create_outlook_proxy(vacancy_rate: Optional[float], redundancy_rate: Optional[float]) -> Dict:
    """
    Create proxy outlook metric from vacancy and redundancy rates.

    Since Singapore doesn't have occupation-level projections,
    we use industry vacancy/redundancy rates as a proxy.

    Outlook Score = (Vacancy Rate - Redundancy Rate) * 10

    Returns:
        Dict with outlook_pct and outlook_desc
    """
    if vacancy_rate is None and redundancy_rate is None:
        return {"outlook_pct": None, "outlook_desc": "Data not available"}

    # Use defaults if missing
    v_rate = vacancy_rate or 2.0  # Singapore average
    r_rate = redundancy_rate or 1.0

    # Calculate outlook score
    outlook_score = (v_rate - r_rate) * 10

    # Generate description
    if outlook_score > 15:
        desc = "Much faster than average"
    elif outlook_score > 8:
        desc = "Faster than average"
    elif outlook_score > 0:
        desc = "Average"
    elif outlook_score > -5:
        desc = "Slower than average"
    else:
        desc = "Declining"

    return {
        "outlook_pct": round(outlook_score, 1),
        "outlook_desc": desc
    }


def generate_csv():
    """Generate occupations CSV"""
    master_list = load_master_list()
    wage_data = load_wage_data()
    census_data = load_census_employment()

    output_path = Path("sg_occupations.csv")

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "title", "slug", "category", "ssoc_code",
            "median_pay_monthly", "pay_25th", "pay_75th",
            "num_jobs_2021", "outlook_pct", "outlook_desc",
            "entry_education", "url"
        ])

        writer.writeheader()

        for occupation in master_list:
            code = occupation["code"]
            slug = occupation["slug"]
            title = occupation["title"]
            category = occupation["category"]

            # Get wage data
            wage_info = wage_data.get(code, {})
            median_pay = wage_info.get("median_50")
            pay_25th = wage_info.get("median_25")
            pay_75th = wage_info.get("median_75")

            # Get employment count
            num_jobs = census_data.get(code)

            # Generate proxy outlook
            outlook = create_outlook_proxy(None, None)

            # Education (not available in Singapore data)
            entry_education = ""  # Would need manual mapping

            # URL (link to SkillsFuture or MOM if available)
            url = occupation.get("url", "")

            writer.writerow({
                "title": title,
                "slug": slug,
                "category": category,
                "ssoc_code": code,
                "median_pay_monthly": median_pay,
                "pay_25th": pay_25th,
                "pay_75th": pay_75th,
                "num_jobs_2021": num_jobs,
                "outlook_pct": outlook["outlook_pct"],
                "outlook_desc": outlook["outlook_desc"],
                "entry_education": entry_education,
                "url": url
            })

    print(f"Generated {len(master_list)} occupations to {output_path}")


def main():
    """Main entry point"""
    generate_csv()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run CSV generator**

```bash
uv run python sg_make_csv.py
```

- [ ] **Step 3: Verify CSV format**

```bash
head sg_occupations.csv
wc -l sg_occupations.csv
```

Expected: 511 lines (510 occupations + header)

- [ ] **Step 4: Commit CSV generator**

```bash
git add sg_make_csv.py sg_occupations.csv
git commit -m "feat: add Singapore occupations CSV generator"
```

---

## PHASE 3: Frontend Updates (1 week)

### Task 3.1: Update site/index.html for Singapore context

**Files:**
- Modify: `site/index.html`

- [ ] **Step 1: Update page title and header**

```html
<!-- Line 6: Update title -->
<title>Singapore Job Market Visualizer</title>

<!-- Line 212: Update header -->
<h1>Singapore Job Market Visualizer <a href="https://github.com/gibtang/jobs-report-sg">GitHub</a></h1>

<!-- Line 213: Update description -->
<p>This is a research tool that visualizes <b>510 occupations</b> from the <a href="https://www.mom.gov.sg">Ministry of Manpower</a> and <a href="https://www.skillsfuture.gov.sg">SkillsFuture Singapore</a>, using the Singapore Standard Occupational Classification (SSOC 2020). Each rectangle's <b>area</b> is proportional to total employment. <b>Color</b> shows the selected metric &mdash; toggle between labour market indicators, median pay, and skills frameworks. This is not a government publication &mdash; it is a development tool for exploring Singapore job market data visually.</p>
```

- [ ] **Step 2: Update BLS references to Singapore sources**

```html
<!-- Replace BLS references with Singapore equivalents -->

<p><b>Data Sources:</b> Occupational data from MOM Occupational Wage Tables (biennial), SkillsFuture Skills Frameworks, and Census 2021. The "Digital AI Exposure" layer uses LLM scoring to estimate how AI will reshape each occupation.</p>

<p><b>Important Notes:</b> Singapore does not publish occupation-level employment projections. The "Labour Market Indicator" layer uses job vacancy and redundancy rates as a proxy for outlook. Education requirements are not systematically linked to occupations in Singapore data.</p>
```

- [ ] **Step 3: Update color mode labels**

```html
<!-- Line 248-252: Update layer names -->
<div class="color-toggle" id="colorToggle">
  <button data-mode="outlook" class="active">Labour Market Indicator</button>
  <button data-mode="pay">Median Pay</button>
  <button data-mode="skills">Skills Framework</button>
  <button data-mode="exposure">Digital AI Exposure</button>
</div>
```

- [ ] **Step 4: Update legend labels**

```javascript
// Line 863-868: Update LEGEND_CONFIG
const LEGEND_CONFIG = {
  exposure:  { low: "Low", high: "High" },
  outlook:   { low: "Declining", high: "Growing" },
  pay:       { low: "$2K", high: "$20K" },  // SGD monthly
  skills:    { low: "Entry", high: "Advanced" },
};
```

- [ ] **Step 5: Test site locally**

```bash
cd site
python -m http.server 8000
# Open http://localhost:8000
```

- [ ] **Step 6: Commit frontend updates**

```bash
git add site/index.html
git commit -m "feat: update site for Singapore context"
```

---

### Task 3.2: Create Singapore site data builder

**Files:**
- Create: `build_sg_data.py`

- [ ] **Step 1: Create site data builder**

```python
# build_sg_data.py
"""
Build site/data.json for Singapore from occupations.csv and scores.json.

Combines:
- sg_occupations.csv (for stats)
- scores.json (for AI exposure)

Output: site/data.json
"""

import csv
import json


def main():
    # Load AI exposure scores (if available)
    scores_path = "scores.json"
    scores = {}

    if Path(scores_path).exists():
        with open(scores_path) as f:
            scores_list = json.load(f)
        scores = {s["slug"]: s for s in scores_list}

    # Load CSV stats
    with open("sg_occupations.csv") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Merge data
    data = []
    for row in rows:
        slug = row["slug"]
        score = scores.get(slug, {})

        data.append({
            "title": row["title"],
            "slug": slug,
            "category": row["category"],
            "ssoc_code": row["ssoc_code"],
            "pay": int(row["median_pay_monthly"]) if row["median_pay_monthly"] else None,
            "pay_25th": int(row["pay_25th"]) if row["pay_25th"] else None,
            "pay_75th": int(row["pay_75th"]) if row["pay_75th"] else None,
            "jobs": int(row["num_jobs_2021"]) if row["num_jobs_2021"] else None,
            "outlook": float(row["outlook_pct"]) if row["outlook_pct"] else None,
            "outlook_desc": row["outlook_desc"],
            "education": row["entry_education"],
            "exposure": score.get("exposure"),
            "exposure_rationale": score.get("rationale"),
            "url": row.get("url", ""),
        })

    # Write output
    import os
    os.makedirs("site", exist_ok=True)

    with open("site/data.json", "w") as f:
        json.dump(data, f)

    print(f"Wrote {len(data)} occupations to site/data.json")

    # Print summary
    total_jobs = sum(d["jobs"] for d in data if d["jobs"])
    print(f"Total jobs represented: {total_jobs:,}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Build site data**

```bash
uv run python build_sg_data.py
```

- [ ] **Step 3: Verify data.json**

```bash
cat site/data.json | jq '. | length'
cat site/data.json | jq '.[0]'
```

Expected: JSON with occupation data

- [ ] **Step 4: Commit site data builder**

```bash
git add build_sg_data.py site/data.json
git commit -m "feat: add Singapore site data builder"
```

---

## PHASE 4: LLM Scoring (keep as-is, with Singapore context)

### Task 4.1: Score Singapore occupations for AI exposure

**Files:**
- Create: `sg_score.py`
- Modify: `score.py` (optional, for Singapore-specific prompt)

- [ ] **Step 1: Create Singapore scoring script**

```python
# sg_score.py
"""
Score Singapore occupations for Digital AI Exposure using LLM.

Reads sg_descriptions/*.md and sends each to OpenRouter API
for AI exposure scoring (0-10 scale).

Output: scores.json
"""

import asyncio
import json
import os
from pathlib import Path

import aiohttp
from openai import AsyncOpenAI


# Singapore-specific AI exposure scoring prompt
SG_PROMPT = """You are an expert analyst evaluating how exposed different occupations in Singapore are to AI automation and transformation.

You will be given a job role description from Singapore's SkillsFuture frameworks.

Rate the occupation's overall AI Exposure on a scale from 0 to 10.

AI Exposure measures: how much will AI reshape this occupation in Singapore's context?
Consider both direct effects (AI automating tasks) and indirect effects (AI increasing productivity).

Singapore-specific factors:
- Singapore is a regional hub for finance, tech, and logistics
- Government actively promotes AI adoption through National AI Strategy
- Smaller labour market means faster adoption of automation
- Focus on digital economy and smart nation initiatives

Use these anchors:

0–1: Minimal exposure. Physical/hands-on work in unpredictable environments.
Examples: Construction labourer, plumber, security guard.

2–3: Low exposure. Mostly physical or interpersonal work with minor digital tasks.
Examples: Retail assistant, food service worker, healthcare assistant.

4–5: Moderate exposure. Mix of physical/interpersonal and knowledge work.
Examples: Nurse, teacher, police officer, property agent.

6–7: High exposure. Predominantly knowledge work with some human interaction.
Examples: Accountant, HR manager, journalist, marketing specialist.

8–9: Very high exposure. Almost entirely computer-based work.
Examples: Software engineer, data analyst, graphic designer, financial analyst.

10: Maximum exposure. Routine information processing.
Examples: Data entry clerk, telemarketer.

Respond with ONLY a JSON object in this exact format, no other text:
{"exposure": <0-10>, "rationale": "<2-3 sentences explaining key factors for Singapore context>"}
"""


async def score_occupation(client: AsyncOpenAI, description: str, title: str) -> dict:
    """Score a single occupation using LLM"""

    prompt = f"{SG_PROMPT}\n\nOccupation: {title}\n\n{description}"

    try:
        response = await client.chat.completions.create(
            model="google/gemini-flash-1.5",  # Fast, cost-effective
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )

        result = response.choices[0].message.content.strip()

        # Parse JSON response
        if result.startswith("```json"):
            result = result[7:-3]

        score_data = json.loads(result)

        return {
            "title": title,
            "exposure": score_data.get("exposure"),
            "rationale": score_data.get("rationale", "")
        }

    except Exception as e:
        print(f"Error scoring {title}: {e}")
        return {
            "title": title,
            "exposure": None,
            "rationale": f"Scoring failed: {e}"
        }


async def score_all_occupations():
    """Score all occupations from sg_descriptions"""

    # Initialize OpenAI client with OpenRouter
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )

    # Read all description files
    descriptions_dir = Path("sg_descriptions")
    description_files = list(descriptions_dir.glob("*.md"))

    print(f"Found {len(description_files)} occupation descriptions")

    # Score occupations
    scores = []

    for i, desc_file in enumerate(description_files, 1):
        title = desc_file.stem.replace("-", " ").title()

        with open(desc_file) as f:
            description = f.read()

        print(f"[{i}/{len(description_files)}] Scoring {title}...")

        result = await score_occupation(client, description, title)

        # Generate slug
        result["slug"] = desc_file.stem

        scores.append(result)

        # Rate limiting
        await asyncio.sleep(0.5)

    # Save scores
    with open("scores.json", "w") as f:
        json.dump(scores, f, indent=2)

    print(f"\nSaved {len(scores)} scores to scores.json")

    # Print summary
    scored = [s for s in scores if s.get("exposure") is not None]
    print(f"Successfully scored: {len(scored)}/{len(scores)}")

    avg_exposure = sum(s["exposure"] for s in scored) / len(scored) if scored else 0
    print(f"Average exposure: {avg_exposure:.1f}/10")


async def main():
    """Main entry point"""
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not set")
        return

    await score_all_occupations()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run AI scoring**

```bash
export OPENROUTER_API_KEY=your_key_here
uv run python sg_score.py
```

Note: This will take ~30 minutes for 300 occupations with rate limiting

- [ ] **Step 3: Verify scores**

```bash
cat scores.json | jq '. | length'
cat scores.json | jq '.[0]'
```

Expected: JSON with exposure scores (0-10)

- [ ] **Step 4: Commit scoring script**

```bash
git add sg_score.py scores.json
git commit -m "feat: add Singapore AI exposure scoring"
```

---

## Final Steps

### Task 5.1: Update README for Singapore context

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README header**

```markdown
# Singapore Job Market Visualizer

A research tool for visually exploring Singapore labour market data from the Ministry of Manpower (MOM) and SkillsFuture Singapore. This visualizes **510 occupations** using the Singapore Standard Occupational Classification (SSOC 2020), covering employment across the Singapore economy.

**Live demo:** (Add URL when deployed)

## What's here

Each rectangle's **area** is proportional to employment (from Census 2021), and **color** shows the selected metric — toggle between labour market indicators, median pay, skills frameworks, and AI exposure.

## Data Sources

Unlike the US BLS OOH which has comprehensive occupation-level data, Singapore's data is more limited:

- **MOM Occupational Wage Tables**: Biennial wage data by occupation (25th/50th/75th percentile)
- **SkillsFuture Skills Frameworks**: Job role descriptions for 30+ industries
- **Census 2021**: Baseline employment counts by occupation
- **Job Vacancy/Redundancy Rates**: Used as proxy for outlook (Singapore doesn't publish occupation-level projections)

## Limitations

- No occupation-level employment projections (Singapore doesn't publish these)
- Education requirements not linked to occupations systematically
- Data updates infrequent (wages: biennial, census: every 10 years)
```

- [ ] **Step 2: Update usage instructions**

```markdown
## Usage

```bash
# Scrape SkillsFuture data
uv run python sg_scrape.py --source skills

# Generate master occupation list
uv run python sg_make_master_list.py

# Parse job descriptions
uv run python sg_parse.py

# Generate CSV
uv run python sg_make_csv.py

# Score AI exposure (requires OPENROUTER_API_KEY)
export OPENROUTER_API_KEY=your_key
uv run python sg_score.py

# Build site data
uv run python build_sg_data.py

# Serve site locally
cd site && python -m http.server 8000
```
```

- [ ] **Step 3: Commit README**

```bash
git add README.md
git commit -m "docs: update README for Singapore context"
```

---

### Task 5.2: Final verification and testing

**Files:**
- All files

- [ ] **Step 1: Run full pipeline**

```bash
# From clean slate
rm -rf sg_data sg_descriptions scores.json site/data.json

# Run all steps
uv run python sg_scrape.py --source skills
uv run python sg_make_master_list.py
uv run python sg_parse.py
uv run python sg_make_csv.py
# uv run python sg_score.py  # Skip if no API key
uv run python build_sg_data.py
```

- [ ] **Step 2: Test website locally**

```bash
cd site && python -m http.server 8000
# Open http://localhost:8000
```

Verify:
- Treemap renders correctly
- Color modes toggle properly
- Tooltips show occupation data
- Stats update per layer

- [ ] **Step 3: Check for issues**

```bash
# Verify data completeness
cat site/data.json | jq '. | length'  # Should be ~510
cat site/data.json | jq '[.[] | select(.pay == null)] | length'  # Count missing wages
cat site/data.json | jq '[.[] | select(.jobs == null)] | length'  # Count missing employment
```

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete Singapore job market visualizer MVP"
```

---

## Data Quality Checklist

Before considering the MVP complete, verify:

- [ ] At least 300 occupations have wage data
- [ ] At least 200 occupations have employment counts
- [ ] All 10 SSOC major groups are represented
- [ ] Treemap renders without errors
- [ ] All 4 color modes work (Pay, Outlook, Skills, Exposure)
- [ ] Tooltip data displays correctly
- [ ] Site is responsive on mobile

---

## Known Limitations

Document these in the final README:

1. **No occupation-level projections**: Singapore doesn't publish 10-year employment outlooks like US BLS
2. **Education data**: Not systematically linked to occupations
3. **Employment counts**: Only from Census 2021 (10-year old data)
4. **Wage data**: Biennial updates only
5. **Job descriptions**: From SkillsFuture (industry-specific, not comprehensive)

---

## Future Enhancements

Possible improvements for v2:

1. Add SkillsFramework coloring layer (beyond AI exposure)
2. Scrape job posting trends from MyCareersFuture
3. Incorporate graduate employment survey data (MOE)
4. Add historical wage trends
5. Create industry-level view (SSIC codes)
6. Add education requirement inference from WSQ competencies

---

## Advisory Improvements (Optional)

These recommendations from the plan review are not required for MVP but can improve implementation:

1. **Add `.gitignore` entry** for `sg_data/` directory to prevent committing large scraped files
2. **Increase rate limiting** in SkillsFuture scraper - government sites may block rapid scraping
3. **Add Census extraction guidance** - Task 2.2 requires manual extraction from Census 2021 PDF
4. **Add checkpoint/resume** for AI scoring script if scoring fails partway through
5. **Add data validation** after CSV generation (check for negative wages, duplicate SSOC codes)

---

**Plan Complete & Approved**
