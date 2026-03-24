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
    """Load SSOC 2020 classification from PDF."""
    # For now, return hardcoded sample
    return SSOC_OCCUPATIONS


def load_wage_occupations():
    """Load occupations from wage data"""
    wage_file = Path("sg_data/wages_extracted.json")
    if wage_file.exists():
        with open(wage_file) as f:
            wage_data = json.load(f)
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
            return json.load(f)
    return []


def merge_sources():
    """Merge all occupation sources"""
    ssoc_jobs = load_ssoc_from_pdf()
    wage_jobs = load_wage_occupations()
    skills_jobs = load_skills_occupations()

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
    master_list.sort(key=lambda x: (x["category"], x["title"]))

    output_path = Path("sg_occupations.json")
    with open(output_path, "w") as f:
        json.dump(master_list, f, indent=2)

    print(f"Generated {len(master_list)} occupations to {output_path}")

    from collections import Counter
    category_counts = Counter(j["category"] for j in master_list)
    print("\nOccupations by category:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")


if __name__ == "__main__":
    main()
