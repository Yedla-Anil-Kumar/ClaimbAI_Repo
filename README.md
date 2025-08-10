# ClaimbAI: Automated AI/ML Repository Quality Assessment

ClaimbAI is a robust, extensible pipeline for **automated static and LLM-based analysis of AI/ML code repositories**.  
It supports both classic static code analysis and advanced LLM-powered micro-agents to assess code quality, ML maturity, and best practices across many repositories in parallel.

---

## Features

- **Static Analysis:** Cyclomatic complexity, maintainability, docstring coverage, test/CI/CD detection, secrets scanning, and more.
- **LLM Micro-Agents:** Modular agents for code quality, ML pipeline, infrastructure, and project structure, powered by OpenAI or Huggingface models.
- **Parallel Processing:** Scans multiple repos concurrently for speed.
- **Smart Budgeting:** Caps on files/snippets per repo and per-agent to avoid API overuse and context overflow.
- **Extensible:** Add your own micro-agents or static checks easily.
- **Output:** Per-repo and aggregate JSON reports with detailed signals and scores.

---

## Requirements

- Python 3.9+
- [pip](https://pip.pypa.io/en/stable/)
- (Optional) [OpenAI API key](https://platform.openai.com/account/api-keys) or [Huggingface API token](https://huggingface.co/settings/tokens)
- (Optional) [tiktoken](https://github.com/openai/tiktoken) for token counting

---

## Installation

1. **Clone the repository:**
   ```sh
   git clone <your-claimbai-repo-url>
   cd ClaimbAI
   ```

2. **Create and activate a virtual environment:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Set up your `.env` file:**
   - Copy `.env.example` to `.env` and fill in your API keys and settings, or edit `.env` directly:
     ```
     OPENAI_API_KEY=sk-...
     # or for Huggingface:
     HUGGINGFACE_HUB_TOKEN=hf_...
     REPO_BASE=useful_repos
     MA_CONCURRENCY=2
     MA_MAX_FILES_PER_REPO=5
     MA_SNIPPETS_PER_AGENT=2
     MA_MAX_SNIPPET_BYTES=1800
     MA_MAX_CALLS_PER_REPO=10
     MICRO_AGENT_MODEL=gpt-4o-mini
     ```

---

## Usage

### **1. Prepare Repositories**

- Place or clone all target repositories under the folder specified by `REPO_BASE` (default: `useful_repos/`).

### **2. Run Static + LLM Analysis (Recommended)**

```sh
python run_agents.py
```
- This will scan all repos in parallel and write results to `data/dev_platform_outputs.json`.

### **3. Run Only LLM Micro-Agents (Advanced)**

```sh
python scripts/run_micro_agents_all.py --base useful_repos --out data/micro_agents/aggregate.json --per-repo-dir data/micro_agents/per_repo
```
- Adjust `--max-workers` to control parallelism.

### **4. View Results**

- **Aggregate results:**  
  `data/dev_platform_outputs.json` (static+LLM)  
  `data/micro_agents/aggregate.json` (LLM micro-agents only)
- **Per-repo results:**  
  `data/micro_agents/per_repo/<repo_name>.json`

---

## Configuration

- **Budgeting:**  
  Control the number of files/snippets/LLM calls per repo via `.env`:
  ```
  MA_MAX_FILES_PER_REPO=5
  MA_SNIPPETS_PER_AGENT=2
  MA_MAX_SNIPPET_BYTES=1800
  MA_CONCURRENCY=2
  ```
- **Model:**  
  Set `MICRO_AGENT_MODEL` in `.env` (e.g., `gpt-4o-mini`, `gpt-3.5-turbo`, or a Huggingface model).

- **API Keys:**  
  - For OpenAI: `OPENAI_API_KEY`
  - For Huggingface: `HUGGINGFACE_HUB_TOKEN`

---

## Troubleshooting

- **LLM context length exceeded:**  
  The orchestrator automatically trims files/snippets to avoid this. If you still see errors, lower `MA_MAX_FILES_PER_REPO` or `MA_SNIPPETS_PER_AGENT` in `.env`.

- **API rate limits:**  
  Lower `MA_CONCURRENCY` and/or `MA_MAX_CALLS_PER_REPO`.

- **No output or errors:**  
  Check your `.env` for correct API keys and settings.  
  Check logs for error messages.

---

## Extending

- **Add new micro-agents:**  
  Implement a new agent class in `micro_agents/` and register it in `orchestrator.py`.
- **Add new static checks:**  
  Add functions to `utils/code_analysis.py` or `utils/ml_insights.py`.

---

## Example: Quickstart

```sh
# 1. Clone some repos into useful_repos/
# 2. Set up your .env as above
# 3. Run:
python run_agents.py
# 4. See results in data/dev_platform_outputs.json
```

---

## Project Structure

```
ClaimbAI/
├── agents/
│   └── dev_platform_agent.py
├── micro_agents/
│   ├── orchestrator.py
│   ├── code_quality_agents.py
│   └── ... (other agent modules)
├── utils/
│   ├── code_analysis.py
│   ├── ml_insights.py
│   └── file_utils.py
├── scripts/
│   ├── run_micro_agents_all.py
│   └── ... (other scripts)
├── data/
│   ├── dev_platform_outputs.json
│   └── micro_agents/
│       ├── aggregate.json
│       └── per_repo/
├── useful_repos/
│   └── ... (your target repos)
├── .env
├── requirements.txt
└── run_agents.py
```

---

## License

MIT License (or your chosen license)

---

## Contact

For questions or contributions, open an issue or pull request on GitHub.
