# Variables
VENV_DIR=venv
PYTHON=$(VENV_DIR)/bin/python
PIP=$(VENV_DIR)/bin/pip
UVICORN=$(VENV_DIR)/bin/uvicorn
RUFF=$(VENV_DIR)/bin/ruff
PROJECT_DIR=$(shell pwd)

default: install

# change test

venv:
	python3 -m venv $(VENV_DIR)

install:
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

run:
	$(UVICORN) app.main:app --reload

clean:
	rm -rf $(VENV_DIR)

lint:
	@echo "Running lint checks..."
	@$(RUFF) check $(PROJECT_DIR) --fix
	@echo "Linting completed."

.PHONY: venv install run clean lint
