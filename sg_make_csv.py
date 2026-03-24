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
        return {record["ssoc_code"]: record for record in wage_data}
    return {}


def load_census_employment() -> Dict[str, int]:
    """Load Census 2021 employment counts"""
    # Sample employment counts (replace with real Census data)
    return {
        "1111": 45000,  # Chief Executives
        "1120": 120000,  # General Managers
        "2131": 98000,  # Computer Engineers
    }


def create_outlook_proxy(vacancy_rate: Optional[float], redundancy_rate: Optional[float]) -> Dict:
    """Create proxy outlook metric from vacancy/redundancy rates"""
    if vacancy_rate is None and redundancy_rate is None:
        return {"outlook_pct": None, "outlook_desc": "Data not available"}
    v_rate = vacancy_rate or 2.0
    r_rate = redundancy_rate or 1.0
    outlook_score = (v_rate - r_rate) * 10
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
    return {"outlook_pct": round(outlook_score, 1), "outlook_desc": desc}


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

            wage_info = wage_data.get(code, {})
            median_pay = wage_info.get("median_50")
            pay_25th = wage_info.get("median_25")
            pay_75th = wage_info.get("median_75")

            num_jobs = census_data.get(code)
            outlook = create_outlook_proxy(None, None)

            writer.writerow({
                "title": title, "slug": slug, "category": category, "ssoc_code": code,
                "median_pay_monthly": median_pay, "pay_25th": pay_25th, "pay_75th": pay_75th,
                "num_jobs_2021": num_jobs, "outlook_pct": outlook["outlook_pct"],
                "outlook_desc": outlook["outlook_desc"], "entry_education": "", "url": ""
            })

    print(f"Generated {len(master_list)} occupations to {output_path}")


def main():
    """Main entry point"""
    generate_csv()


if __name__ == "__main__":
    main()
