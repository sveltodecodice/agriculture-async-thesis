#!/usr/bin/env bash
set -Eeuo pipefail

# Trap errors so the terminal window stays open for inspection
trap 'echo ""; read -p "An error occurred. Press [Enter] to exit..."' ERR

echo "==> Stopping and removing container state (preserving base images)"
docker compose down --volumes --remove-orphans

echo "==> Clearing build cache"
docker builder prune --force

echo "==> Purging dangling resources & volumes (preserving pulled images)"
docker system prune --force --volumes

echo "==> Rebuilding images"
docker compose build

echo "==> Starting Docker Compose"
docker compose up