import os
import time
from typing import List, Optional
from serpapi import GoogleSearch
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

OUTPUT_FILE = os.getenv("STUDENT_REPOS_OUTPUT", "student_repos.txt")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable")
if not SERPAPI_API_KEY:
    raise ValueError("Missing SERPAPI_API_KEY environment variable")

def run_serpapi_search(query: str) -> List[dict]:
    """Run a SerpAPI Google search and return organic results."""
    try:
        search = GoogleSearch({
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "num": 10,
            "engine": "google"
        })
        results = search.get_dict()
        return results.get("organic_results", [])
    except Exception as e:
        print(f"[ERROR] SerpAPI search failed: {e}")
        return []

llm = ChatOpenAI(
    model="gpt-4o",
    openai_api_key=OPENAI_API_KEY
)

def is_probably_student_repo(snippet: str, link: str) -> bool:
    """
    Use LLM to determine if a repo is likely a student/academic AI/ML project.
    """
    prompt = f"""
You are an AI assistant helping identify student or academic GitHub repositories.
Given the following search snippet and link, answer YES if it is likely a university/final year/student project repository in AI/ML. Otherwise, answer NO.

Snippet: "{snippet}"
Link: {link}

Only respond with YES or NO.
"""
    try:
        resp = llm.invoke(prompt)
        return resp.content.strip().upper().startswith("Y")
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        return False

def extract_repo_link(link: str) -> Optional[str]:
    """Return the link if it's a GitHub repo, else None."""
    return link if "github.com" in link else None

def fetch_repos(limit: int = 10, sleep_sec: float = 2.0) -> List[str]:
    """
    Search for student/academic AI/ML GitHub repos using SerpAPI and LLM filtering.
    """
    queries = [
        "university student machine learning project GitHub",
        "final year AI project GitHub",
        "college AI ML project repositories",
        "student AI ML GitHub repo"
    ]
    found = set()
    for q in queries:
        print(f"🔍 Searching: {q}")
        for item in run_serpapi_search(q):
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            repo_link = extract_repo_link(link)
            if repo_link and is_probably_student_repo(snippet, repo_link):
                if repo_link not in found:
                    print(f"✅ Found: {repo_link}")
                    found.add(repo_link)
            if len(found) >= limit:
                break
            time.sleep(sleep_sec)  # Rate limiting
        if len(found) >= limit:
            break
    return list(found)

def save_repos(repos: List[str], output_path: str) -> None:
    """Save repo links to a file, filtering duplicates."""
    unique_repos = list(set(repos))
    with open(output_path, "w") as f:
        f.write("\n".join(unique_repos))
    print(f"📄 Saved {len(unique_repos)} repos to {output_path}")

if __name__ == "__main__":
    print("🚀 Fetching student/academic GitHub repos...")
    repos = fetch_repos(limit=10, sleep_sec=2.0)
    if repos:
        save_repos(repos, OUTPUT_FILE)
    else:
        print("⚠️ No repos found.")