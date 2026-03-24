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
