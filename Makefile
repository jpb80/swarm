export SHELL := /bin/bash

HELP_REGEX:=^(.+): .*\#\# (.*)

CACHE_DIR := .cache

.PHONY: help
help: ## Show this help message.
	@echo 'Usage:'
	@echo '  make [target] ...'
	@echo
	@echo 'Targets:'
	@egrep "$(HELP_REGEX)" Makefile | sed -E "s/$(HELP_REGEX)/  \1 # \2/" | column -t -c 2 -s '#'

.PHONY: install
install: virtual_env # Install requirements to build/run swarm
	pip install -r requirements.txt

virtual_env: # Activate venv
	python3 -m venv venv
	. venv/bin/activate
