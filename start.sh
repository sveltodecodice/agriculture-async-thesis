#!/usr/bin/env bash
set -Eeuo pipefail

echo "==> Stopping and removing previous Docker Compose resources"
docker compose down \
  --volumes \
  --remove-orphans \
  --rmi local

echo "==> Cleaning Docker build cache."
docker builder prune --all --force

echo "==> Cleaning unused Docker resources, including volumes"
docker system prune --all --force --volumes

echo "==> Rebuilding images"
docker compose build

echo "==> Starting Docker Compose"
docker compose up 
