import json
import sys
from agents.dev_quality_agent import analyze_dev_and_innovation

def assess_repository(repo_path: str) -> dict:
    
    return analyze_dev_and_innovation(repo_path)["signals"]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/quality_assessment.py /path/to/repo")
        sys.exit(1)

    repo_path = sys.argv[1]
    signals = assess_repository(repo_path)
    print(json.dumps(signals, indent=2))
