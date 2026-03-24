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
            model="google/gemini-flash-1.5",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )

        result = response.choices[0].message.content.strip()

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

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )

    descriptions_dir = Path("sg_descriptions")
    description_files = list(descriptions_dir.glob("*.md"))

    print(f"Found {len(description_files)} occupation descriptions")

    scores = []

    for i, desc_file in enumerate(description_files, 1):
        title = desc_file.stem.replace("-", " ").title()

        with open(desc_file) as f:
            description = f.read()

        print(f"[{i}/{len(description_files)}] Scoring {title}...")

        result = await score_occupation(client, description, title)
        result["slug"] = desc_file.stem
        scores.append(result)

        await asyncio.sleep(0.5)

    with open("scores.json", "w") as f:
        json.dump(scores, f, indent=2)

    print(f"\nSaved {len(scores)} scores to scores.json")

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
