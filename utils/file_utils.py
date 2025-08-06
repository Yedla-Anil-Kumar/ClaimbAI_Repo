import os
from pathlib import Path
from typing import Iterator

def list_all_files(repo_path: str) -> Iterator[str]:
    """Yield every file under repo_path."""
    for root, _, files in os.walk(repo_path):
        for fname in files:
            yield os.path.join(root, fname)

def list_source_files(root: str,
                      include_dirs=None,
                      exclude_dirs=None
                     ) -> Iterator[Path]:
    """
    Yield only .py files under include_dirs (defaults to src/ and the repo root folder),
    skipping any path containing an exclude_dir.
    """
    root_path = Path(root)
    repo_name = root_path.name
    include_dirs = include_dirs or {"src", repo_name}
    exclude_dirs = set(exclude_dirs or [
        "docs", "examples", "templates", ".github", "tests", "__pycache__"
    ])

    for path in root_path.rglob("*.py"):
        parts = set(path.parts)
        if not parts & include_dirs:
            continue
        if parts & exclude_dirs:
            continue
        yield path
