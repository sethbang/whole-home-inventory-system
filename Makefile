# Convenience wrapper around bin/whis. Either entrypoint works equivalently;
# `make up` / `make down` / `make certs` exist purely for users who reach for
# `make` first. All real logic lives in bin/whis.

WHIS := ./bin/whis

.PHONY: help up down certs logs nas-up nas-down nas-logs

help:
	@$(WHIS) help

up:
	@$(WHIS) up

down:
	@$(WHIS) down

certs:
	@$(WHIS) certs

logs:
	@$(WHIS) logs

nas-up:
	@$(WHIS) nas up

nas-down:
	@$(WHIS) nas down

nas-logs:
	@$(WHIS) nas logs
