import os
from utils.file_utils import list_all_files, read_file

def analyze_docs(repo_path: str) -> dict:
    signals = {
        "has_docs_folder": os.path.isdir(os.path.join(repo_path, "docs")),
        "notebooks_found": False,
        "docstring_density": 0.0
    }

    py_files = [f for f in list_all_files(repo_path) if f.endswith(".py")]
    doc_count = 0
    total_funcs = 0

    for fpath in py_files:
        content = read_file(fpath) or ""
        func_count = content.count("def ")
        total_funcs += func_count
        doc_count += content.count('"""') // 2

    if total_funcs:
        signals["docstring_density"] = round(doc_count / total_funcs, 2)

    signals["notebooks_found"] = any(f.endswith(".ipynb") for f in list_all_files(repo_path))

    return {
        "agent": "documentation_agent",
        "repo": os.path.basename(repo_path),
        "signals": signals
    }
