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

from playwright.async_api import async_playwright


class SingaporeDataScraper:
    """Scraper for Singapore job market data"""

    BASE_URL = {
        "mom": "https://www.mom.gov.sg",
        "skillsfuture": "https://www.skillsfuture.gov.sg",
        "census": "https://www.singstat.gov.sg"
    }

    SKILLS_FRAMEWORKS = [
        "accountancy",
        "infocomm-technology",
        "financial-services",
        "logistics",
        "precision-engineering",
        "retail",
    ]

    def __init__(self, data_dir: str = "./sg_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }

    async def scrape_wage_tables(self):
        """Scrape MOM Occupational Wage Tables"""
        raise NotImplementedError("TODO: Implement wage table scraping")

    def extract_wage_data_from_excel(self, excel_path: Path) -> list:
        """Extract wage data from downloaded Excel file (synchronous)

        Note: Column names (Occupation, SSOC_Code, Median_25, Median_50, Median_75)
        are assumptions based on typical MOM wage table format. May need adjustment
        based on actual MOM Excel file structure.
        """
        import pandas as pd

        try:
            # Read Excel file
            df = pd.read_excel(excel_path)

            # Expected columns: Occupation, SSOC_Code, Median_25, Median_50, Median_75
            # NOTE: These column names may need adjustment based on actual MOM Excel file
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

    async def _download_file(self, page, url: str, dest_path: Path):
        """Download file from URL"""
        try:
            response = await page.request.get(url)
            content = await response.body()

            with open(dest_path, "wb") as f:
                f.write(content)

        except Exception as e:
            print(f"Failed to download {url}: {e}")

    async def scrape_skills_frameworks(self):
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

    def save_wage_data(self, wage_data: list):
        """Save wage data to JSON"""
        output_path = self.data_dir / "wages_extracted.json"

        with open(output_path, "w") as f:
            json.dump(wage_data, f, indent=2)

        print(f"Saved {len(wage_data)} wage records to {output_path}")


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
