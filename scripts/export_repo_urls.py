import os
from git import Repo

REPO_BASE = "external_repos"
OUTPUT_FILE = "data/repo_urls.txt"

def find_git_repos(base_path):
    """
    Recursively find all directories under `base_path` containing a `.git` folder.
    """
    for root, dirs, files in os.walk(base_path):
        if ".git" in dirs:
            yield root
            # prevent descending into nested repos
            dirs.clear()

def export_repo_urls():
    """
    Reads the 'origin' remote URL from each Git repo under REPO_BASE
    and writes them to OUTPUT_FILE.
    """
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    urls = []
    
    for repo_path in find_git_repos(REPO_BASE):
        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            # take the first URL if multiple are present
            url = next(iter(origin.urls))
            urls.append(url)
        except Exception as e:
            print(f"⚠️ Skipping {repo_path}: {e}")

    # Write to file
    with open(OUTPUT_FILE, "w") as f:
        for url in urls:
            f.write(f"{url}\n")
    print(f"✅ Exported {len(urls)} repo URLs to {OUTPUT_FILE}")

if __name__ == "__main__":
    export_repo_urls()