set shell := ["bash", "-cu"]

up:
	docker compose -f infra/compose.yaml up -d

down:
	docker compose -f infra/compose.yaml down

logs:
	docker compose -f infra/compose.yaml logs -f

validate:
	bash scripts/vault_validate.sh

pr:
	bash scripts/pr_open.sh

# ------- Python (agent-core) -------
ac-install:
	cd agent-core && poetry install

ac-shell:
	cd agent-core && poetry shell

ac-test:
	cd agent-core && poetry run pytest -q

ac-run-relate note:
	# Example: just ac-run-relate /abs/path/to/vault/00_Inbox/some-note.md
	cd agent-core && poetry run wattson-agent relate {{note}}

ac-export-reqs:
	cd agent-core && poetry export -f requirements.txt --with-credentials -o requirements.txt

# Optional: lock refresh (updates poetry.lock)
ac-update:
	cd agent-core && poetry update

# ------- Lint/format helpers -------
ac-lint:
	cd agent-core && poetry run ruff check .

ac-fmt:
	cd agent-core && poetry run black .