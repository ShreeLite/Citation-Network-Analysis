# One command: `make all`. Every step is idempotent and resumes from data/cache.
PY := .venv/bin/python
export PYTHONPATH := $(CURDIR)

.PHONY: checks core scimago setup roster identity reingest pubs enrich networks qa analysis deliverables site all test clean-processed

setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements.txt
	$(PY) -m playwright install chromium
	cd site && npm install

roster:        ; $(PY) -m pipeline.01_roster && $(PY) -m pipeline.01b_nirf
identity:      ; $(PY) -m pipeline.02_identity
reingest:      ; $(PY) -m pipeline.02_identity --reingest
pubs:          ; $(PY) -m pipeline.03_publications
enrich:        ; $(PY) -m pipeline.04_enrich
networks:      ; $(PY) -m pipeline.05_networks
qa:            ; $(PY) -m pipeline.06_qa
analysis:      ; $(PY) -m analysis.run_all && $(PY) -m analysis.figures
deliverables:  ; $(PY) -m analysis.deliverables
site:          ; cp deliverables/group9_deliverables.zip site/public/ && cd site && npm run build && cp public/group9_deliverables.zip dist/

all: roster identity pubs enrich networks qa analysis deliverables site checks

test:
	$(PY) -m pytest -q tests

clean-processed:   # keeps the download cache
	rm -rf data/processed/*

core:          # run this yourself: CORE's robots.txt disallows AI agents
	$(PY) scripts/download_core.py
scimago:       ; $(PY) -m pipeline.00_scimago

checks:        # every sanity check in qa/sanity_checklist.md
	$(PY) qa/checkpoint1.py
	$(PY) qa/checkpoint2.py
	$(PY) -m pipeline.06_qa
	$(PY) -m analysis.robustness
	$(PY) qa/findings_handcheck.py
	$(PY) qa/site_check.py
	$(PY) -m analysis.report_results
