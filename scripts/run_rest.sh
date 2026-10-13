#!/usr/bin/env bash
# Runs everything after step 4; stops at the first failure and reports which step.
set -o pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=. PYTHONWARNINGS=ignore
PY=.venv/bin/python
L=data/raw/logs
step() { echo "== $1 $(date +%H:%M)" >> $L/run_rest.status; shift; "$@" > $L/run_rest_$(date +%s).out 2>&1 || { echo "FAILED: $* (see newest $L/run_rest_*.out)" >> $L/run_rest.status; exit 1; }; }
step networks     $PY -m pipeline.05_networks
step qa           $PY -m pipeline.06_qa
step analysis     $PY -m analysis.run_all
step figures      $PY -m analysis.figures
step deliverables $PY -m analysis.deliverables
step qa_again     $PY -m pipeline.06_qa
step site         bash -c "cp deliverables/group9_deliverables.zip site/public/ && cd site && npm run build && cp public/group9_deliverables.zip dist/"
echo "ALL DONE $(date +%H:%M)" >> $L/run_rest.status
