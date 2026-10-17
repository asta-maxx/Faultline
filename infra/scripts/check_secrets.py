#!/usr/bin/env python3
"""Secret scan script to prevent credentials from entering git.
Checks:
1. .env files are not tracked in git
2. No API keys, passwords, private keys, or tokens in staged/tracked files
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# High-entropy / known token patterns
PATTERNS = [
    (r"AIza[0-9A-Za-z\\-_]{35}", "Google API Key"),
    (r"gsk_[a-zA-Z0-9]{48}", "Groq API Key"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private Key"),
    (r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "Generic Secret"),
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def check_env_files() -> list[str]:
    errors = []
    # Verify .env is not tracked
    res = subprocess.run(["git", "ls-files", ".env"], cwd=REPO_ROOT, capture_output=True, text=True)
    if res.stdout.strip():
        errors.append("ERROR: .env is tracked in git! Untrack it immediately: git rm --cached .env")
    return errors

def scan_files() -> list[str]:
    errors = []
    # Scan git staged and working tree files in data/ and infra/
    for folder in ("data", "infra"):
        folder_path = REPO_ROOT / folder
        if not folder_path.exists():
            continue
        for file_path in folder_path.rglob("*"):
            if not file_path.is_file():
                continue
            if ".git" in file_path.parts or "__pycache__" in file_path.parts:
                continue
            # Skip binary / large outputs
            if file_path.suffix in (".pyc", ".rdb", ".png", ".jpg", ".ico"):
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
                
            for regex, desc in PATTERNS:
                matches = re.findall(regex, content, re.IGNORECASE)
                # Filter out obvious false positives like example placeholders or tests
                real_matches = [
                    m for m in matches 
                    if not any(placeholder in m.lower() for placeholder in ("example", "your_", "placeholder", "xxx", "foo"))
                ]
                if real_matches:
                    errors.append(f"Potential {desc} detected in {file_path.relative_to(REPO_ROOT)}: {real_matches[0][:8]}...")

    return errors

def main():
    print("Running Faultline pre-commit secret scan...")
    errors = check_env_files() + scan_files()
    if errors:
        print("\n[FAIL] Secret scan FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("[PASS] Secret scan PASSED: No secrets found.")

if __name__ == "__main__":
    main()
