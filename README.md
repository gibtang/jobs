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

## LLM-powered coloring

The repo includes scrapers, parsers, and a pipeline for writing custom LLM prompts to score and color occupations by any criteria. You write a prompt, the LLM scores each occupation, and the treemap colors accordingly. The "Digital AI Exposure" layer is one example — it estimates how much current AI (which is primarily digital) will reshape each occupation. But you could write a different prompt for any question — e.g. exposure to humanoid robotics, offshoring risk, climate impact — and re-run the pipeline to get a different coloring. See `score.py` for the prompt and scoring pipeline.

**What "AI Exposure" is NOT:**
- It does **not** predict that a job will disappear. Software developers score 9/10 because AI is transforming their work — but demand for software could easily *grow* as each developer becomes more productive.
- It does **not** account for demand elasticity, latent demand, regulatory barriers, or social preferences for human workers.
- The scores are rough LLM estimates (Gemini Flash via OpenRouter), not rigorous predictions. Many high-exposure jobs will be reshaped, not replaced.

## Data pipeline

1. **Scrape** (`scrape.py`) — Playwright (non-headless, BLS blocks bots) downloads raw HTML for all 342 occupation pages into `html/`.
2. **Parse** (`parse_detail.py`, `process.py`) — BeautifulSoup converts raw HTML into clean Markdown files in `pages/`.
3. **Tabulate** (`make_csv.py`) — Extracts structured fields (pay, education, job count, growth outlook, SOC code) into `occupations.csv`.
4. **Score** (`score.py`) — Sends each occupation's Markdown description to an LLM with a scoring rubric. Each occupation gets an AI Exposure score from 0-10 with a rationale. Results saved to `scores.json`. Fork this to write your own prompts.
5. **Build site data** (`build_site_data.py`) — Merges CSV stats and AI exposure scores into a compact `site/data.json` for the frontend.
6. **Website** (`site/index.html`) — Interactive treemap visualization with four color layers: BLS Outlook, Median Pay, Education, and Digital AI Exposure.

## Key files

| File | Description |
|------|-------------|
| `occupations.json` | Master list of 342 occupations with title, URL, category, slug |
| `occupations.csv` | Summary stats: pay, education, job count, growth projections |
| `scores.json` | AI exposure scores (0-10) with rationales for all 342 occupations |
| `prompt.md` | All data in a single file, designed to be pasted into an LLM for analysis |
| `html/` | Raw HTML pages from BLS (source of truth, ~40MB) |
| `pages/` | Clean Markdown versions of each occupation page |
| `site/` | Static website (treemap visualization) |

## LLM prompt

[`prompt.md`](prompt.md) packages all the data — aggregate statistics, tier breakdowns, exposure by pay/education, BLS growth projections, and all 342 occupations with their scores and rationales — into a single file (~45K tokens) designed to be pasted into an LLM. This lets you have a data-grounded conversation about AI's impact on the job market without needing to run any code. Regenerate it with `uv run python make_prompt.py`.

## Setup

```
uv sync
uv run playwright install chromium
```

Requires an OpenRouter API key in `.env`:
```
OPENROUTER_API_KEY=your_key_here
```

## Usage

```bash
# Scrape BLS pages (only needed once, results are cached in html/)
uv run python scrape.py

# Generate Markdown from HTML
uv run python process.py

# Generate CSV summary
uv run python make_csv.py

# Score AI exposure (uses OpenRouter API)
uv run python score.py

# Build website data
uv run python build_site_data.py

# Serve the site locally
cd site && python -m http.server 8000
```

## Functionality
Jobs report data scraper and site builder for Singapore occupational data.
