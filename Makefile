# Vibe — common tasks. Every target wraps a script in ./scripts or ./deploy, so you can also run those directly.

.PHONY: help setup check dev dev-fake test up down deploy destroy mcp-smoke

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[32m%-12s\033[0m %s\n",$$1,$$2}'

setup: ## Install backend + frontend dependencies, create .env files
	./scripts/setup.sh

check: ## Verify AWS credentials, Bedrock model access and TMDB key
	./scripts/check-aws.sh

dev: ## Run locally with real Bedrock + TMDB (SQLite database)
	./scripts/dev.sh

dev-fake: ## Run locally with offline demo data (no keys)
	./scripts/dev.sh --fake

test: ## All automated tests + production build
	./scripts/test.sh

up: ## Docker compose stack (Postgres + API + web)
	docker compose up --build

down: ## Stop docker compose stack
	docker compose down

deploy: ## Deploy to AWS (App Runner + RDS + CloudFront)
	./deploy/aws/deploy.sh

destroy: ## Delete the AWS deployment
	./deploy/aws/destroy.sh

mcp-smoke: ## MCP smoke test against localhost (or URL=https://.../mcp)
	./scripts/mcp-smoke.sh $(URL)
