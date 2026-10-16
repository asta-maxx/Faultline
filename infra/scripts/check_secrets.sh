#!/usr/bin/env bash
set -euo pipefail

# Secret scan script for Faultline
# If gitleaks is installed, run it. Otherwise fall back to python script.
if command -v gitleaks &> /dev/null; then
    echo "Running gitleaks secret scan..."
    gitleaks detect --no-git --source . -v
else
    echo "gitleaks not found, running python secret scanner..."
    python3 infra/scripts/check_secrets.py || python infra/scripts/check_secrets.py
fi
