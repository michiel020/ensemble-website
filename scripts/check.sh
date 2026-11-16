#!/usr/bin/env bash
# The one local check for this site; CI runs the same command (.github/workflows/site.yml).
# The folders that make up the live site are listed in scripts/site-dirs.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/site-dirs.sh
python3 scripts/check-links.py $SITE_DIRS
