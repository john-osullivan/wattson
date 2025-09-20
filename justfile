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
