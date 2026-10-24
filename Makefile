# Set up the crew and run the browser demo (demo_ui.py). Run `make` to see the targets.
#
# Needs make, lsof, pgrep, and curl. The page starts in the background and its
# output goes to $(LOG). Setup and the swarm step need ANTHROPIC_API_KEY. A key
# already in your environment (for example from direnv) is used as is. Without
# one, the key comes from $(ENV_FILE) if that file exists.

PYTHON ?= python
DEMO_UI_PORT ?= 8765
LOG ?= outputs/demo-ui.log
ENV_FILE ?= ./.env
ID_BACKUP ?= outputs/old-workspace-ids
URL = http://127.0.0.1:$(DEMO_UI_PORT)
LISTENER = lsof -tiTCP:$(DEMO_UI_PORT) -sTCP:LISTEN 2>/dev/null | head -1
LOAD_KEY = [ -f "$(ENV_FILE)" ] && { saved="$$ANTHROPIC_API_KEY"; set -a; . "$(ENV_FILE)"; set +a; [ -z "$$saved" ] || ANTHROPIC_API_KEY="$$saved"; }
ID_FILES = .specialist_ids.json .coordinator_id .environment_id .skill_ids.json .last_session_id

.DEFAULT_GOAL := help
.PHONY: help crew-setup ui ui-stop ui-restart ui-status ui-logs

help: ## Show this list
	@awk -F':.*## ' '/^[a-z-]+:.*## /{printf "  make %-11s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

crew-setup: ## Create the crew, skills, and environment in your key's workspace (FORCE=1 to redo)
	@if [ -e .coordinator_id ] && [ -z "$(FORCE)" ]; then \
	  echo "A crew is already set up here (.coordinator_id exists)."; \
	  echo "To create a new one in the workspace your key belongs to, run: make crew-setup FORCE=1"; \
	  echo "The old ids are kept under $(ID_BACKUP)/"; exit 1; \
	fi; \
	$(LOAD_KEY); \
	if [ -z "$$ANTHROPIC_API_KEY" ]; then \
	  echo "No ANTHROPIC_API_KEY in your environment or in $(ENV_FILE)"; exit 1; \
	fi; \
	backup="$(ID_BACKUP)/$$(date +%Y%m%d-%H%M%S)"; \
	for f in $(ID_FILES); do \
	  if [ -e $$f ]; then mkdir -p $$backup; mv $$f $$backup/; fi; \
	done; \
	for script in create_specialists create_cleaner create_coordinator upload_skills setup_environment; do \
	  echo "== $$script"; $(PYTHON) $$script.py || exit 1; \
	done; \
	echo "Crew ready. Run: make ui"; \
	if [ -d "$$backup" ]; then echo "Old ids are in $$backup"; fi

ui: ## Start the demo page in the background
	@mkdir -p $(dir $(LOG)); \
	if [ -n "$$($(LISTENER))" ]; then echo "Already running at $(URL)"; exit 0; fi; \
	$(LOAD_KEY); \
	DEMO_UI_PORT=$(DEMO_UI_PORT) nohup $(PYTHON) demo_ui.py > $(LOG) 2>&1 & \
	for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
	  if curl -s -o /dev/null $(URL)/; then echo "Demo page running at $(URL) (log: $(LOG))"; exit 0; fi; \
	  sleep 0.5; \
	done; \
	echo "The page did not come up. See $(LOG)"; exit 1

ui-stop: ## Stop the demo page (refuses while a step is running; add FORCE=1 to stop anyway)
	@pid=$$($(LISTENER)); \
	if [ -z "$$pid" ]; then echo "Not running"; exit 0; fi; \
	case "$$(ps -o command= -p $$pid)" in \
	  *demo_ui.py*) ;; \
	  *) echo "Port $(DEMO_UI_PORT) is used by something else (pid $$pid), not touching it"; exit 1;; \
	esac; \
	kids=$$(pgrep -P $$pid); \
	if [ -n "$$kids" ] && [ -z "$(FORCE)" ]; then \
	  echo "A step is still running (pid $$kids). Wait for it, or run: make ui-stop FORCE=1"; exit 1; \
	fi; \
	[ -z "$$kids" ] || kill $$kids; \
	kill $$pid; \
	for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do \
	  if [ -z "$$($(LISTENER))" ]; then echo "Stopped"; exit 0; fi; \
	  sleep 0.3; \
	done; \
	echo "Still listening after stopping it. Try: kill -9 $$pid"; exit 1

ui-restart: ui-stop ui ## Stop the demo page, then start it again

ui-status: ## Show whether the demo page is running
	@pid=$$($(LISTENER)); \
	if [ -z "$$pid" ]; then echo "Not running"; exit 0; fi; \
	echo "Running at $(URL) (pid $$pid)"; \
	kids=$$(pgrep -P $$pid); \
	if [ -n "$$kids" ]; then echo "A step is running (pid $$kids)"; fi; \
	true

ui-logs: ## Follow the demo page's log
	@tail -n 40 -f $(LOG)
