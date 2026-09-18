#!/bin/sh
set -eu
for module in ambient_sensor terrain_sensor plantation_sensor seeder irrigator harvester camp_manager dashboard; do
  echo "== $module =="
  (cd "$module" && pytest -q)
done
