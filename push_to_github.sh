#!/usr/bin/env bash
# Usage: ./push_to_github.sh <github-username> [repo-name]
set -euo pipefail
USER_NAME="${1:?GitHub username required}"
REPO="${2:-ecommerce-docker-vagrant}"

[ -d .git ] || git init -b main
git add .
git commit -m "Initial commit: e-commerce app (Nginx, Flask, PostgreSQL, Redis) with Vagrant + Docker Compose" || true

if command -v gh >/dev/null 2>&1; then
  gh repo create "$USER_NAME/$REPO" --public --source=. --remote=origin --push
else
  echo "gh CLI not found. Create an empty repo named '$REPO' on github.com, then run:"
  echo "  git remote add origin https://github.com/$USER_NAME/$REPO.git"
  echo "  git push -u origin main"
fi
