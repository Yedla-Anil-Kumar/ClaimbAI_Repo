import os

def list_all_files(repo_path: str):
    for root, _, files in os.walk(repo_path):
        for fname in files:
            yield os.path.join(root, fname)

def read_file(filepath: str):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None
